import re
import time
from collections import namedtuple
from typing import Any, List

from async import _Future, async, await
from debug_utils import LOG_NOTE
from mod_async_server import Server, delay
from mod_battle_results_server.fetcher import BattleResultsFetcher
from mod_battle_results_server.util import (
    JsonParseError,
    get,
    parse_json,
    serialize_to_json,
)
from mod_battle_results_server.validation import (
    ValidationError,
    field,
    number,
    record,
    string,
)
from mod_websocket_server import MessageStream, websocket_protocol

PORT = 15455

ORIGIN_WHITELIST = [
    re.compile("^https?://localhost(:[0-9]{1,5})?$"),
    "https://lgfrbcsgo.github.io",
]

BattleResultRecord = namedtuple("BattleResultRecord", ("recorded_at", "result"))

subscribers = []  # type: List[MessageStream]
battle_result_records = []  # type: List[BattleResultRecord]


def subscribe(stream):
    if stream not in subscribers:
        subscribers.append(stream)


def unsubscribe(stream):
    if stream in subscribers:
        subscribers.remove(stream)


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

MESSAGE_TYPE = "messageType"
PAYLOAD = "payload"
validate_message = record(field(MESSAGE_TYPE, string), field(PAYLOAD, record()))


@websocket_protocol(allowed_origins=ORIGIN_WHITELIST)
@async
def protocol(server, stream):
    # type: (Server, MessageStream) -> _Future
    host, port = stream.peer_addr
    LOG_NOTE("[{host}]:{port} connected.".format(host=host, port=port))
    try:
        while True:
            data = yield await(stream.receive_message())
            try:
                yield await(handle_data(stream, data))
            except ValidationError as e:
                yield await(send_error(stream, "VALIDATION", str(e)))
            except JsonParseError as e:
                yield await(send_error(stream, "JSON_DECODE", str(e)))
            except Exception:
                yield await(send_error(stream, "INTERNAL", "Internal error."))
                raise
    finally:
        unsubscribe(stream)
        LOG_NOTE("[{host}]:{port} disconnected.".format(host=host, port=port))


@async
def handle_data(stream, data):
    message = parse_json(data)
    validate_message(message)
    message_type = get(message, MESSAGE_TYPE)
    payload = get(message, PAYLOAD)
    yield await(handle_message(stream, message_type, payload))


@async
def handle_message(stream, message_type, payload):
    if message_type == "SUBSCRIBE":
        subscribe(stream)
    elif message_type == "UNSUBSCRIBE":
        unsubscribe(stream)
    elif message_type == "REPLAY":
        yield await(replay(stream, payload))
    else:
        error_msg = "Command not recognized: {}".format(message_type)
        yield await(send_error(stream, "UNRECOGNISED_COMMAND", error_msg))


@async
def replay(stream, payload):
    record(field("after", number, optional=True))(payload)

    after = get(payload, "after")
    if after is None:
        after = 0

    for battle_result_record in battle_result_records:
        if battle_result_record.recorded_at > after:
            yield await(send_battle_result(stream, battle_result_record))


@async
def send_battle_result(stream, result):
    payload = {"result": result.result, "recordedAt": result.recorded_at}
    yield await(send(stream, "BATTLE_RESULT", payload))


@async
def send_error(stream, error_type, error_message):
    payload = {"type": error_type, "message": error_message}
    yield await(send(stream, "ERROR", payload))


@async
def send(message_stream, message_type, payload):
    # type: (MessageStream, str, Any) -> _Future
    message = {MESSAGE_TYPE: message_type, PAYLOAD: payload}
    validate_message(message)
    data = serialize_to_json(message)
    yield await(message_stream.send_message(data))


keep_running = True


@async
def init():
    battle_results_fetcher.start()

    LOG_NOTE("Starting server on port {}".format(PORT))

    with Server(protocol, PORT) as server:
        while keep_running and not server.closed:
            server.poll()
            yield delay(0)

    LOG_NOTE("Stopped server")


def fini():
    global keep_running
    keep_running = False
    battle_results_fetcher.stop()
