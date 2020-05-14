import time
from collections import namedtuple
from typing import List

from debug_utils import LOG_NOTE
from ModBattleResultsServer.fetcher import BattleResultsFetcher
from ModBattleResultsServer.protocol import Protocol, Transport, send
from ModBattleResultsServer.run_loop import RunLoop
from ModBattleResultsServer.util import get
from ModBattleResultsServer.validation import (ValidationError, field, number,
                                               record)
from ModBattleResultsServer.websocket import WebSocketServer

HOST = "localhost"
PORT = 61942

BattleResultRecord = namedtuple("BattleResultRecord", ("recorded_at", "result"))

subscribers = []  # type: List[Transport]
battle_result_records = []  # type: List[BattleResultRecord]


def log_and_notify_subscribers(battle_result):
    battle_result_record = BattleResultRecord(
        recorded_at=time.time(), result=battle_result
    )
    battle_result_records.append(battle_result_record)
    for transport in subscribers:
        send_battle_result(transport, battle_result_record)


battle_results_fetcher = BattleResultsFetcher()
battle_results_fetcher.battle_result_fetched += log_and_notify_subscribers

protocol = Protocol()


@protocol.on("SUBSCRIBE")
def subscribe(transport, _=None):
    if transport not in subscribers:
        subscribers.append(transport)


@protocol.on_disconnected
@protocol.on("UNSUBSCRIBE")
def unsubscribe(transport, _=None):
    if transport in subscribers:
        subscribers.remove(transport)


@protocol.on("REPLAY")
def replay(transport, payload):
    record(field("after", number, optional=True))(payload)

    after = get(payload, "after")
    if after is None:
        after = 0

    for battle_result_record in battle_result_records:
        if battle_result_record.recorded_at > after:
            send_battle_result(transport, battle_result_record)


@protocol.on_unhandled
def unknown_command(transport, message_type, _=None):
    send_error(
        transport,
        "UNRECOGNISED_COMMAND",
        "Command not recognized: {}".format(message_type),
    )


@protocol.on_error(ValidationError)
def validation_error(transport, exception):
    send_error(transport, "VALIDATION", str(exception))


@protocol.on_unhandled_error
def generic_error(transport, exception):
    send_error(transport, "GENERIC", str(exception))


def send_battle_result(transport, result):
    send(
        transport,
        "BATTLE_RESULT",
        {"result": result.result, "recordedAt": result.recorded_at},
    )


def send_error(transport, error_type, error_message):
    send(transport, "ERROR", {"type": error_type, "message": error_message})


server = WebSocketServer(HOST, PORT, protocol)
server_run_loop = RunLoop(server.serveonce)


def init():
    server_run_loop.start()
    battle_results_fetcher.start()
    LOG_NOTE("Server listening on port {}".format(PORT))


def fini():
    server_run_loop.stop()
    server.close()
    battle_results_fetcher.stop()
    LOG_NOTE("Stopped server")
