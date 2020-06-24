import re
import time
from collections import namedtuple
from typing import List

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
    notification = make_notification(Notification(method, params))
    data = serialize_to_json(notification)
    yield stream.send_message(data)


class BattleResultsServer(object):
    def __init__(self):
        self._keep_running = True
        self._subscribers = []  # type: List[MessageStream]
        self._records = []  # type: List[BattleResultRecord]
        self._fetcher = BattleResultsFetcher()
        self._fetcher.battle_result_fetched += self._handle_battle_result

    def _handle_battle_result(self, battle_result):
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

    def _subscribe(self, stream):
        if stream not in self._subscribers:
            self._subscribers.append(stream)

    def _unsubscribe(self, stream):
        if stream in self._subscribers:
            self._subscribers.remove(stream)

    def _get_battle_results(self, after):
        found = [record for record in self._records if record.timestamp > after]
        start = after if not found else min([record.timestamp for record in found])
        end = after if not found else max([record.timestamp for record in found])

        return {
            "start": start,
            "end": end,
            "battleResults": [record.battle_result for record in found],
        }

    def _create_dispatcher(self, stream):
        dispatcher = Dispatcher()

        @dispatcher.add_method()
        def subscribe(_):
            self._subscribe(stream)

        @dispatcher.add_method()
        def unsubscribe(_):
            self._unsubscribe(stream)

        @dispatcher.add_method(
            Nullable(Record(field("after", Number(), optional=True)))
        )
        def get_battle_results(params):
            after = get(params, "after")
            if after is None:
                after = 0

            return self._get_battle_results(after)

        return dispatcher

    @async_task
    def _handle_connection(self, stream):
        host, port = stream.peer_addr
        origin = stream.handshake_headers["origin"]

        LOG_NOTE(
            "{origin} ([{host}]:{port}) connected.".format(
                origin=origin, host=host, port=port
            )
        )

        dispatcher = self._create_dispatcher(stream)

        try:
            while True:
                data = yield stream.receive_message()
                response = dispatcher(data)
                if response:
                    yield stream.send_message(response)
        finally:
            self._unsubscribe(stream)

            LOG_NOTE(
                "{origin} ([{host}]:{port}) disconnected.".format(
                    origin=origin, host=host, port=port
                )
            )

    @auto_run
    @async_task
    def serve(self):
        @websocket_protocol(allowed_origins=ORIGIN_WHITELIST)
        @async_task
        def protocol(_, stream):
            yield self._handle_connection(stream)

        LOG_NOTE("Starting server on port {}".format(PORT))

        self._fetcher.start()

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
