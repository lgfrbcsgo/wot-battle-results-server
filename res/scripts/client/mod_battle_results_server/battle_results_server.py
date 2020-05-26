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
        timestamp=time.time(), battle_result=battle_result
    )
    battle_result_records.append(battle_result_record)
    for stream in subscribers:
        notify(
            stream,
            "subscription",
            {
                "battleResult": battle_result_record.battle_result,
                "timestamp": battle_result_record.timestamp,
            },
        )


battle_results_fetcher = BattleResultsFetcher()
battle_results_fetcher.battle_result_fetched += log_and_notify_subscribers


dispatcher = Dispatcher()


@dispatcher.method()
def subscribe(params, stream, **context):
    if stream not in subscribers:
        subscribers.append(stream)


@dispatcher.method()
def unsubscribe(params, stream, **context):
    if stream in subscribers:
        subscribers.remove(stream)


@dispatcher.method(
    param_parser=Nullable(Record(field("after", Number(), optional=True)))
)
def get_battle_results(params, **context):
    after = get(params, "after")
    if after is None:
        after = 0

    found = [record for record in battle_result_records if record.timestamp > after]
    start = min([record.timestamp for record in found]) if found else after
    end = max([record.timestamp for record in found]) if found else after
    return {
        "start": start,
        "end": end,
        "battleResults": [record.battle_result for record in found],
    }


@websocket_protocol(allowed_origins=ORIGIN_WHITELIST)
@async_task
def protocol(server, stream):
    host, port = stream.peer_addr
    LOG_NOTE("[{host}]:{port} connected.".format(host=host, port=port))
    try:
        while True:
            data = yield stream.receive_message()
            response = dispatcher(data, stream=stream)
            if response:
                yield stream.send_message(response)
    finally:
        unsubscribe(None, stream)
        LOG_NOTE("[{host}]:{port} disconnected.".format(host=host, port=port))


def make_battle_result(result):
    return {"result": result.result, "recordedAt": result.recorded_at}


@auto_run
@async_task
def notify(stream, method, params):
    notification = make_notification(Notification(method, params))
    data = serialize_to_json(notification)
    yield stream.send_message(data)


keep_running = True


@auto_run
@async_task
def init():
    battle_results_fetcher.start()

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


def fini():
    global keep_running
    keep_running = False
    battle_results_fetcher.stop()
