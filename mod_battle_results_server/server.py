import re
import time
from collections import namedtuple
from typing import Any, List

from debug_utils import LOG_NOTE
from mod_async import CallbackCancelled, async_task, auto_run, delay
from mod_async_server import Server
from mod_battle_results_server.fetcher import BattleResultsFetcher
from mod_battle_results_server.json_rpc import (
    Dispatcher,
    Notification,
    make_notification,
)
from mod_battle_results_server.parser import Nullable, Number, Record, field
from mod_battle_results_server.util import get, serialize_to_json
from mod_websocket_server import MessageStream, websocket_protocol

PORT = 15455

ORIGIN_WHITELIST = [
    re.compile("^https?://localhost(:[0-9]{1,5})?$"),
    "https://lgfrbcsgo.github.io",
]

BattleResultRecord = namedtuple("BattleResultRecord", ("timestamp", "battle_result"))


@auto_run
@async_task
def notify(stream, method, params):
    # type: (MessageStream, str, Any) -> ...
    notification = make_notification(Notification(method, params))
    data = serialize_to_json(notification)
    yield stream.send_message(data)


class Handlers(object):
    def __init__(self, fetcher):
        # type: (BattleResultsFetcher) -> None
        self._subscribers = []  # type: List[MessageStream]
        self._records = []  # type: List[BattleResultRecord]
        fetcher.battle_result_fetched += self._on_battle_result

    def subscribe(self, stream):
        # type: (MessageStream) -> None
        if stream not in self._subscribers:
            self._subscribers.append(stream)

    def unsubscribe(self, stream):
        # type: (MessageStream) -> None
        if stream in self._subscribers:
            self._subscribers.remove(stream)

    def get_battle_results(self, after):
        # type: (int) -> ...
        found = [record for record in self._records if record.timestamp > after]
        start = after if not found else min([record.timestamp for record in found])
        end = after if not found else max([record.timestamp for record in found])

        return {
            "start": start,
            "end": end,
            "battleResults": [record.battle_result for record in found],
        }

    def _on_battle_result(self, battle_result):
        # type: (Any) -> None
        record = BattleResultRecord(
            timestamp=int(time.time()), battle_result=battle_result
        )

        self._records.append(record)

        params = {
            "battleResult": record.battle_result,
            "timestamp": record.timestamp,
        }

        for stream in self._subscribers:
            notify(stream, "subscription", params)


def create_dispatcher(stream, handlers):
    # type: (MessageStream, Handlers) -> Dispatcher
    dispatcher = Dispatcher()

    @dispatcher.add_method()
    def subscribe(params):
        handlers.subscribe(stream)

    @dispatcher.add_method()
    def unsubscribe(params):
        handlers.unsubscribe(stream)

    @dispatcher.add_method(
        param_parser=Nullable(Record(field("after", Number(), optional=True)))
    )
    def get_battle_results(params):
        after = get(params, "after")
        if after is None:
            after = 0

        return handlers.get_battle_results(after)

    return dispatcher


def create_protocol(handlers, allowed_origins):
    # type: (Handlers, List) -> ...
    @websocket_protocol(allowed_origins=allowed_origins)
    @async_task
    def protocol(server, stream):
        # type: (Server, MessageStream) -> ...
        host, port = stream.peer_addr
        origin = stream.handshake_headers["origin"]

        LOG_NOTE(
            "{origin} ([{host}]:{port}) connected.".format(
                origin=origin, host=host, port=port
            )
        )

        dispatcher = create_dispatcher(stream, handlers)

        try:
            while True:
                data = yield stream.receive_message()
                response = dispatcher(data)
                if response:
                    yield stream.send_message(response)
        finally:
            handlers.unsubscribe(stream)

            LOG_NOTE(
                "{origin} ([{host}]:{port}) disconnected.".format(
                    origin=origin, host=host, port=port
                )
            )

    return protocol


class BattleResultsServer(object):
    def __init__(self):
        self._keep_running = True
        self._fetcher = BattleResultsFetcher()

    @auto_run
    @async_task
    def serve(self):
        self._fetcher.start()

        LOG_NOTE("Starting server on port {}".format(PORT))

        protocol = create_protocol(Handlers(self._fetcher), ORIGIN_WHITELIST)

        try:
            with Server(protocol, PORT) as server:
                while self._keep_running and not server.closed:
                    server.poll()
                    yield delay(0)
        except CallbackCancelled:
            pass
        finally:
            LOG_NOTE("Stopped server")

    def close(self):
        self._keep_running = False
        self._fetcher.stop()


g_battle_results_server = BattleResultsServer()
