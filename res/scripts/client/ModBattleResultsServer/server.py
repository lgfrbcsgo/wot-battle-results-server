from ModBattleResultsServer.fetcher import BattleResultsFetcher
from ModBattleResultsServer.protocol import Protocol, handler, WebSocketServer
from ModBattleResultsServer.run_loop import RunLoop
from ModBattleResultsServer.session import Session
from ModBattleResultsServer.util import safe_callback
from debug_utils import LOG_NOTE

HOST = 'localhost'
PORT = 61942


class MessageType(object):
    BATTLE_RESULT = 'BATTLE_RESULT'
    SUBSCRIBE_TO_BATTLE_RESULTS = 'SUBSCRIBE_TO_BATTLE_RESULTS'
    REPLAY_BATTLE_RESULTS = 'REPLAY_BATTLE_RESULTS'
    REPLAY_AND_SUBSCRIBE_TO_BATTLE_RESULTS = 'REPLAY_AND_SUBSCRIBE_TO_BATTLE_RESULTS'
    UNSUBSCRIBE_FROM_BATTLE_RESULTS = 'UNSUBSCRIBE_FROM_BATTLE_RESULTS'
    UNKNOWN_COMMAND = 'UNKNOWN_COMMAND'
    INVALID_COMMAND = 'INVALID_COMMAND'


class BattleResultsServerProtocol(Protocol):
    def __init__(self, connection):
        super(BattleResultsServerProtocol, self).__init__(connection)
        self.subscribed_to_battle_results = False

    def handle_message_not_dispatched(self, msg_type, **__):
        self.send_message(
            MessageType.UNKNOWN_COMMAND,
            commandType=msg_type
        )

    def handle_invalid_message(self, data):
        self.send_message(
            MessageType.INVALID_COMMAND,
            command=data
        )

    @handler(Protocol.CONNECTED)
    def on_connected(self, _, **__):
        LOG_NOTE('{host} connected on port {port} (Origin: {origin})'.format(**self.connection_info))

    @handler(Protocol.DISCONNECTED)
    def on_disconnected(self, _, **__):
        LOG_NOTE('{host} disconnected from port {port} (Origin: {origin})'.format(**self.connection_info))

    @handler(MessageType.SUBSCRIBE_TO_BATTLE_RESULTS, MessageType.REPLAY_AND_SUBSCRIBE_TO_BATTLE_RESULTS)
    def on_subscribe_to_battle_results(self, _, **__):
        self.subscribed_to_battle_results = True

    @handler(MessageType.UNSUBSCRIBE_FROM_BATTLE_RESULTS, Protocol.DISCONNECTED)
    def on_unsubscribe_from_battle_results(self, _, **__):
        self.subscribed_to_battle_results = False

    @handler(MessageType.REPLAY_BATTLE_RESULTS, MessageType.REPLAY_AND_SUBSCRIBE_TO_BATTLE_RESULTS)
    def on_replay_battle_results(self, _, offset=None, sessionId=None, **__):
        if offset is not None and not isinstance(offset, (long, int)):
            return

        if sessionId is not None and not Session.current().id == sessionId:
            return

        for result in Session.current().query_results(offset):
            self._send_battle_result_message(result)

    def notify_battle_result(self, result):
        if self.subscribed_to_battle_results:
            self._send_battle_result_message(result)

    def _send_battle_result_message(self, result):
        self.send_message(
            MessageType.BATTLE_RESULT,
            index=result.index,
            battleResult=result.battle_result,
            sessionId=Session.current().id,
        )


server = WebSocketServer(HOST, PORT, BattleResultsServerProtocol)
server_run_loop = RunLoop(server.serveonce)


@safe_callback
def broadcast_battle_result(battle_result):
    result = Session.current().receive_battle_result(battle_result)
    for protocol in server.protocols:
        protocol.notify_battle_result(result)


battle_results_fetcher = BattleResultsFetcher()
battle_results_fetcher.battleResultFetched += broadcast_battle_result


def init():
    server_run_loop.start()
    battle_results_fetcher.start()
    LOG_NOTE('Server listening on port {}'.format(PORT))


def fini():
    server_run_loop.stop()
    server.close()
    battle_results_fetcher.stop()
    LOG_NOTE('Stopped server')
