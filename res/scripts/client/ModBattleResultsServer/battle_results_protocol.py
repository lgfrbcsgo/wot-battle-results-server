from ModBattleResultsServer.gaming_session import GamingSession
from ModBattleResultsServer.protocol import Protocol, handler


class CommandType(object):
    SUBSCRIBE_TO_BATTLE_RESULTS = 'SUBSCRIBE_TO_BATTLE_RESULTS'
    REPLAY_BATTLE_RESULTS = 'REPLAY_BATTLE_RESULTS'
    REPLAY_AND_SUBSCRIBE_TO_BATTLE_RESULTS = 'REPLAY_AND_SUBSCRIBE_TO_BATTLE_RESULTS'
    UNSUBSCRIBE_FROM_BATTLE_RESULTS = 'UNSUBSCRIBE_FROM_BATTLE_RESULTS'
    START_NEW_SESSION = 'START_NEW_SESSION'


class MessageType(object):
    COMMANDS = 'COMMANDS'
    SESSION_ID = 'SESSION_ID'
    BATTLE_RESULT = 'BATTLE_RESULT'
    UNKNOWN_COMMAND = 'UNKNOWN_COMMAND'
    INVALID_COMMAND = 'INVALID_COMMAND'


class BattleResultsProtocol(Protocol):
    def __init__(self, transport):
        super(BattleResultsProtocol, self).__init__(transport)
        self.subscribed_to_battle_results = False

    def handle_message_not_dispatched(self, msg_type):
        self._send_unknown_command_message(msg_type)

    def handle_invalid_message(self, data):
        self._send_invalid_command_message(data)

    @handler(Protocol.CONNECTED)
    def on_connected(self, **_):
        self._send_commands_message(list(self.handled_msg_types))
        self.notify_session_id()

    @handler(CommandType.SUBSCRIBE_TO_BATTLE_RESULTS, CommandType.REPLAY_AND_SUBSCRIBE_TO_BATTLE_RESULTS)
    def on_subscribe_to_battle_results(self, **_):
        self.subscribed_to_battle_results = True

    @handler(CommandType.UNSUBSCRIBE_FROM_BATTLE_RESULTS, Protocol.DISCONNECTED)
    def on_unsubscribe_from_battle_results(self, **_):
        self.subscribed_to_battle_results = False

    @handler(CommandType.REPLAY_BATTLE_RESULTS, CommandType.REPLAY_AND_SUBSCRIBE_TO_BATTLE_RESULTS)
    def on_replay_battle_results(self, offset=None, sessionId=None, **_):
        if offset is not None and not isinstance(offset, (long, int)):
            return

        if sessionId is not None and not GamingSession.current().id == sessionId:
            return

        for result in GamingSession.current().query_results(offset):
            self._send_battle_result_message(result)

    @handler(CommandType.START_NEW_SESSION)
    def on_start_new_session(self, **_):
        GamingSession.start_new()

    def notify_session_id(self):
        self._send_session_id_message(GamingSession.current().id)

    def notify_battle_result(self, result):
        if self.subscribed_to_battle_results:
            self._send_battle_result_message(result)

    def _send_battle_result_message(self, result):
        self.send_message(
            MessageType.BATTLE_RESULT,
            index=result.index,
            battleResult=result.battle_result,
            sessionId=result.session_id,
        )

    def _send_session_id_message(self, session_id):
        self.send_message(
            MessageType.SESSION_ID,
            sessionId=session_id
        )

    def _send_commands_message(self, command_types):
        self.send_message(
            MessageType.COMMANDS,
            commandTypes=command_types
        )

    def _send_unknown_command_message(self, command_type):
        self.send_message(
            MessageType.UNKNOWN_COMMAND,
            commandType=command_type
        )

    def _send_invalid_command_message(self, command):
        self.send_message(
            MessageType.INVALID_COMMAND,
            command=command
        )
