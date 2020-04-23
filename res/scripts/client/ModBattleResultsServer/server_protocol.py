from ModBattleResultsServer.protocol import Protocol, handler
from ModBattleResultsServer.repository import BattleResultRepository
from ModBattleResultsServer.transport import Transport


class CommandType(object):
    SUBSCRIBE = 'SUBSCRIBE'
    UNSUBSCRIBE = 'UNSUBSCRIBE'
    REPLAY = 'REPLAY'
    PIPELINE = 'PIPELINE'


class MessageType(object):
    COMMANDS = 'COMMANDS'
    BATTLE_RESULT = 'BATTLE_RESULT'
    ERROR = 'ERROR'


class ErrorType(object):
    UNKNOWN_COMMAND = 'UNKNOWN_COMMAND'
    INVALID_COMMAND = 'INVALID_COMMAND'
    INVALID_ARGUMENT = 'INVALID_ARGUMENT'


class BattleResultsProtocol(Protocol):
    def __init__(self, repository, transport):
        # type: (BattleResultRepository, Transport) -> None
        super(BattleResultsProtocol, self).__init__(transport)
        self.repository = repository
        self.subscribed = False

    def handle_message_not_dispatched(self, message_type):
        self._send_error(
            ErrorType.UNKNOWN_COMMAND,
            'Command {} is unknown.'.format(message_type)
        )

    def handle_invalid_message(self, data):
        self._send_error(
            ErrorType.INVALID_COMMAND,
            'Message is invalid: {}'.format(data)
        )

    @handler(Protocol.CONNECTED)
    def on_connected(self, **_):
        self.repository.received_battle_result += self.notify_battle_result
        self._send_commands(list(self.handled_message_types))

    @handler(Protocol.DISCONNECTED)
    def on_disconnected(self, **_):
        self.repository.received_battle_result -= self.notify_battle_result

    @handler(CommandType.SUBSCRIBE)
    def on_subscribe(self, **_):
        self.subscribed = True

    @handler(CommandType.UNSUBSCRIBE, Protocol.DISCONNECTED)
    def on_unsubscribe(self, **_):
        self.subscribed = False

    @handler(CommandType.REPLAY)
    def on_replay(self, after=None, **_):
        if after is None:
            after = 0

        if not isinstance(after, (int, long, float)):
            return self._send_error(
                ErrorType.INVALID_ARGUMENT,
                'Command {} expected command.after to be any of int, long, or float.'.format(CommandType.REPLAY)
            )

        for result in self.repository.get_battle_results_after(after):
            self._send_battle_result(result)

    @handler(CommandType.PIPELINE)
    def on_pipeline(self, commands=None, **_):
        if not isinstance(commands, list):
            return self._send_error(
                ErrorType.INVALID_ARGUMENT,
                'Command {} expected command.commands to be a list.'.format(CommandType.PIPELINE)
            )

        for command in commands:
            self.handle_message(command)

    def notify_battle_result(self, battle_result_entry):
        if self.subscribed:
            self._send_battle_result(battle_result_entry)

    def _send_battle_result(self, battle_result_entry):
        self.send(
            MessageType.BATTLE_RESULT,
            timestamp=battle_result_entry.timestamp,
            battleResult=battle_result_entry.battle_result
        )

    def _send_commands(self, command_types):
        self.send(
            MessageType.COMMANDS,
            commandTypes=command_types
        )

    def _send_error(self, error_type, error_message):
        self.send(
            MessageType.ERROR,
            errorType=error_type,
            errorMessage=error_message
        )
