from typing import List

from ModBattleResultsServer.protocol import Protocol, handler
from ModBattleResultsServer.recorder import BattleResultRecorder, BattleResultRecord
from ModBattleResultsServer.transport import Transport


class CommandType(object):
    SUBSCRIBE = 'SUBSCRIBE'
    UNSUBSCRIBE = 'UNSUBSCRIBE'
    REPLAY = 'REPLAY'
    PIPELINE = 'PIPELINE'


class MessageType(object):
    PROTOCOL_VERSION = 'PROTOCOL_VERSION'
    BATTLE_RESULT = 'BATTLE_RESULT'
    ERROR = 'ERROR'


class ErrorType(object):
    UNKNOWN_COMMAND = 'UNKNOWN_COMMAND'
    INVALID_COMMAND = 'INVALID_COMMAND'
    INVALID_ARGUMENT = 'INVALID_ARGUMENT'


class BattleResultsProtocol(Protocol):
    def __init__(self, repository, transport):
        # type: (BattleResultRecorder, Transport) -> None
        super(BattleResultsProtocol, self).__init__(transport)
        self.repository = repository

    def handle_message_not_dispatched(self, message_type):
        self.send_error(
            ErrorType.UNKNOWN_COMMAND,
            'Command {} is unknown.'.format(message_type)
        )

    def handle_invalid_message(self, data):
        self.send_error(
            ErrorType.INVALID_COMMAND,
            'Message is invalid: {}'.format(data)
        )

    @handler(Protocol.CONNECTED)
    def on_connected(self, **_):
        self.send_protocol_version(list(self.handled_message_types))

    @handler(CommandType.SUBSCRIBE)
    def on_subscribe(self, **_):
        self.repository.received_battle_result += self.send_battle_result

    @handler(CommandType.UNSUBSCRIBE, Protocol.DISCONNECTED)
    def on_unsubscribe(self, **_):
        self.repository.received_battle_result -= self.send_battle_result

    @handler(CommandType.REPLAY)
    def on_replay(self, after=None, **_):
        if after is None:
            after = 0

        if not isinstance(after, (int, long, float)):
            return self.send_error(
                ErrorType.INVALID_ARGUMENT,
                'Command {} expected command.after to be any of int, long, or float.'.format(CommandType.REPLAY)
            )

        for result in self.repository.get_battle_results_after(after):
            self.send_battle_result(result)

    @handler(CommandType.PIPELINE)
    def on_pipeline(self, commands=None, **_):
        if not isinstance(commands, list):
            return self.send_error(
                ErrorType.INVALID_ARGUMENT,
                'Command {} expected command.commands to be a list.'.format(CommandType.PIPELINE)
            )

        for command in commands:
            self.handle_message(command)

    def send_battle_result(self, record):
        # type: (BattleResultRecord) -> None
        self.send(
            MessageType.BATTLE_RESULT,
            recordedAt=record.recorded_at,
            result=record.result
        )

    def send_protocol_version(self, command_types):
        # type: (List[str]) -> None
        self.send(
            MessageType.PROTOCOL_VERSION,
            commands=command_types
        )

    def send_error(self, error_type, error_message):
        # type: (str, str) -> None
        self.send(
            MessageType.ERROR,
            type=error_type,
            message=error_message
        )
