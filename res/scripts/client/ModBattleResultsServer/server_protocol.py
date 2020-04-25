import json

from ModBattleResultsServer.protocol import Protocol, handler
from ModBattleResultsServer.recorder import BattleResultRecorder, BattleResultRecord
from ModBattleResultsServer.transport import Transport
from ModBattleResultsServer.util import get
from ModBattleResultsServer.validation import record, field, number


class CommandType(object):
    REPLAY = 'REPLAY'
    SUBSCRIBE = 'SUBSCRIBE'
    UNSUBSCRIBE = 'UNSUBSCRIBE'


class MessageType(object):
    BATTLE_RESULT = 'BATTLE_RESULT'
    ERROR = 'ERROR'
    PROTOCOL_VERSION = 'PROTOCOL_VERSION'


class ErrorType(object):
    MALFORMED_JSON = 'MALFORMED_JSON'
    MALFORMED_MESSAGE = 'MALFORMED_MESSAGE'
    MALFORMED_PAYLOAD = 'MALFORMED_PAYLOAD'
    UNRECOGNISED_COMMAND = 'UNRECOGNISED_COMMAND'


class PayloadFields(object):
    AFTER = 'after'
    COMMANDS = 'commands'
    MESSAGE = 'message'
    RECORDED_AT = 'recordedAt'
    RESULT = 'result'
    TYPE = 'type'


class BattleResultsProtocol(Protocol):
    def __init__(self, repository, transport):
        # type: (BattleResultRecorder, Transport) -> None
        super(BattleResultsProtocol, self).__init__(transport)
        self.repository = repository

    def handle_message_not_dispatched(self, message_type):
        self.send_error(
            ErrorType.UNRECOGNISED_COMMAND,
            'Command not recognized: {}'.format(message_type)
        )

    def handle_malformed_json(self, data):
        self.send_error(
            ErrorType.MALFORMED_JSON,
            'Malformed JSON: {}'.format(data)
        )

    def handle_malformed_message(self, messages, validation_message):
        self.send_error(
            ErrorType.MALFORMED_MESSAGE,
            '{} Got: {}'.format(validation_message, json.dumps(messages))
        )

    def handle_malformed_payload(self, message_type, payload, validation_message):
        self.send_error(
            ErrorType.MALFORMED_PAYLOAD,
            '{}: {} Got: {}'.format(message_type, validation_message, json.dumps(payload))
        )

    @handler([CommandType.SUBSCRIBE])
    def on_subscribe(self, _):
        self.repository.received_battle_result += self.send_battle_result

    @handler([CommandType.UNSUBSCRIBE, Protocol.DISCONNECTED])
    def on_unsubscribe(self, _):
        self.repository.received_battle_result -= self.send_battle_result

    @handler(
        [CommandType.REPLAY],
        validator=record(
            field(PayloadFields.AFTER, number, optional=True)
        )
    )
    def on_replay(self, payload):
        after = get(payload, PayloadFields.AFTER)
        if after is None:
            after = 0

        for result in self.repository.get_battle_results_after(after):
            self.send_battle_result(result)

    def send_battle_result(self, result):
        # type: (BattleResultRecord) -> None
        self.send(
            MessageType.BATTLE_RESULT,
            {
                PayloadFields.RECORDED_AT: result.recorded_at,
                PayloadFields.RESULT: result.result
            }
        )

    def send_error(self, error_type, error_message):
        # type: (str, str) -> None
        self.send(
            MessageType.ERROR,
            {
                PayloadFields.TYPE: error_type,
                PayloadFields.MESSAGE: error_message
            }
        )
