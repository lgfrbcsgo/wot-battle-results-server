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

subscribers = []  # type: List[MessageStream]
battle_result_records = []  # type: List[BattleResultRecord]


def log_and_notify_subscribers(battle_result):
    battle_result_record = BattleResultRecord(
        timestamp=int(time.time()), battle_result=battle_result
    )

    battle_result_records.append(battle_result_record)

    params = {
        "battleResult": battle_result_record.battle_result,
        "timestamp": battle_result_record.timestamp,
    }

    for stream in subscribers:
        notify(stream, "subscription", params)


battle_results_fetcher = BattleResultsFetcher()
battle_results_fetcher.battle_result_fetched += log_and_notify_subscribers


def subscribe(stream):
    if stream not in subscribers:
        subscribers.append(stream)


def unsubscribe(stream):
    if stream in subscribers:
        subscribers.remove(stream)


def get_battle_results(params):
    after = get(params, "after")
    if after is None:
        after = 0

    found = [record for record in battle_result_records if record.timestamp > after]
    start = after if not found else min([record.timestamp for record in found])
    end = after if not found else max([record.timestamp for record in found])

    return {
        "start": start,
        "end": end,
        "battleResults": [record.battle_result for record in found],
    }


@websocket_protocol(allowed_origins=ORIGIN_WHITELIST)
@async_task
def protocol(server, stream):
    host, port = stream.peer_addr
    origin = stream.handshake_headers["origin"]

    LOG_NOTE(
        "{origin} ([{host}]:{port}) connected.".format(
            origin=origin, host=host, port=port
        )
    )

    dispatcher = Dispatcher()
    dispatcher.add_method(subscribe.__name__, lambda _: subscribe(stream))
    dispatcher.add_method(unsubscribe.__name__, lambda _: unsubscribe(stream))
    dispatcher.add_method(
        get_battle_results.__name__,
        get_battle_results,
        param_parser=Nullable(Record(field("after", Number(), optional=True))),
    )

    try:
        while True:
            data = yield stream.receive_message()
            response = dispatcher(data)
            if response:
                yield stream.send_message(response)
    finally:
        unsubscribe(stream)

        LOG_NOTE(
            "{origin} ([{host}]:{port}) disconnected.".format(
                origin=origin, host=host, port=port
            )
        )


@auto_run
@async_task
def notify(stream, method, params):
    notification = make_notification(Notification(method, params))
    data = serialize_to_json(notification)
    yield stream.send_message(data)


keep_running = True


def close_server():
    global keep_running
    keep_running = False


@auto_run
@async_task
def serve():
    LOG_NOTE("Starting server on port {}".format(PORT))

    try:
        with Server(protocol, PORT) as server:
            while keep_running and not server.closed:
                server.poll()
                yield delay(0)
    except CallbackCancelled:
        pass
    finally:
        LOG_NOTE("Stopped server")


def init():
    battle_results_fetcher.start()
    serve()


def fini():
    battle_results_fetcher.stop()
    close_server()
