import time
from collections import namedtuple
from typing import List

from async import async, await
from debug_utils import LOG_NOTE
from mod_async_server import Server, delay
from mod_battle_results_server.fetcher import BattleResultsFetcher
from mod_battle_results_server.protocol import Protocol, send
from mod_battle_results_server.util import JsonParseError, get
from mod_battle_results_server.validation import ValidationError, field, number, record
from mod_websocket_server import MessageStream, websocket_protocol

PORT = 61942

BattleResultRecord = namedtuple("BattleResultRecord", ("recorded_at", "result"))

subscribers = []  # type: List[MessageStream]
battle_result_records = []  # type: List[BattleResultRecord]


def log_and_notify_subscribers(battle_result):
    battle_result_record = BattleResultRecord(
        recorded_at=time.time(), result=battle_result
    )
    battle_result_records.append(battle_result_record)
    for stream in subscribers:
        # don't await, send in parallel, we're not in an async context anyways
        send_battle_result(stream, battle_result_record)


battle_results_fetcher = BattleResultsFetcher()
battle_results_fetcher.battle_result_fetched += log_and_notify_subscribers

protocol = Protocol()


@protocol.on("SUBSCRIBE")
def subscribe(stream, _=None):
    if stream not in subscribers:
        subscribers.append(stream)


@protocol.on_disconnected
@protocol.on("UNSUBSCRIBE")
def unsubscribe(stream, _=None):
    if stream in subscribers:
        subscribers.remove(stream)


@protocol.on("REPLAY")
@async
def replay(stream, payload):
    record(field("after", number, optional=True))(payload)

    after = get(payload, "after")
    if after is None:
        after = 0

    for battle_result_record in battle_result_records:
        if battle_result_record.recorded_at > after:
            yield await(send_battle_result(stream, battle_result_record))


@protocol.on_unhandled
@async
def unknown_command(stream, message_type, _=None):
    yield await(
        send_error(
            stream,
            "UNRECOGNISED_COMMAND",
            "Command not recognized: {}".format(message_type),
        )
    )


@protocol.on_error(ValidationError)
@async
def validation_error(stream, exception):
    yield await(send_error(stream, "VALIDATION", str(exception)))


@protocol.on_error(JsonParseError)
@async
def json_parse_error(stream, exception):
    yield await(send_error(stream, "JSON_DECODE", str(exception)))


@protocol.on_unhandled_error
@async
def generic_error(stream, _=None):
    yield await(send_error(stream, "INTERNAL", "Internal error."))


@protocol.on_connected
def connected(stream):
    LOG_NOTE("[{}]:{} connected.".format(*stream.peer_addr))


@protocol.on_disconnected
def disconnected(stream):
    LOG_NOTE("[{}]:{} disconnected.".format(*stream.peer_addr))


@async
def send_battle_result(stream, result):
    yield await(
        send(
            stream,
            "BATTLE_RESULT",
            {"result": result.result, "recordedAt": result.recorded_at},
        )
    )


@async
def send_error(stream, error_type, error_message):
    yield await(send(stream, "ERROR", {"type": error_type, "message": error_message}))


keep_running = True


@async
def init():
    battle_results_fetcher.start()

    LOG_NOTE("Starting server on port {}".format(PORT))

    with Server(websocket_protocol(protocol), PORT) as server:
        while keep_running and not server.closed:
            server.poll()
            yield delay(0)

    LOG_NOTE("Stopped server")


def fini():
    global keep_running
    keep_running = False
    battle_results_fetcher.stop()
