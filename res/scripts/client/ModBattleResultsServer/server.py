from ModBattleResultsServer.fetcher import BattleResultsFetcher
from ModBattleResultsServer.protocol import Protocol, handler, WebSocketServer
from ModBattleResultsServer.run_loop import RunLoop
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


previous_results = []


class BattleResultsServerProtocol(Protocol):
    def __init__(self, connection):
        super(BattleResultsServerProtocol, self).__init__(connection)
        self.subscribed_to_battle_results = False

    def handle_message_not_dispatched(self, msg_type, **__):
        self.send_message(MessageType.UNKNOWN_COMMAND, commandType=msg_type)

    def handle_invalid_message(self, data):
        self.send_message(MessageType.INVALID_COMMAND, command=data)

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
    def on_replay_battle_results(self, _, offset=None, **__):
        if offset is None:
            replayed_results = previous_results
        elif isinstance(offset, (long, int)) and 0 <= offset < len(previous_results):
            replayed_results = previous_results[offset:]
        else:
            return

        for battle_result in replayed_results:
            self.send_message(MessageType.BATTLE_RESULT, battleResult=battle_result)

    def notify_battle_result(self, battle_result):
        if self.subscribed_to_battle_results:
            self.send_message(MessageType.BATTLE_RESULT, battleResult=battle_result)


server = WebSocketServer(HOST, PORT, BattleResultsServerProtocol)
server_run_loop = RunLoop(server.serveonce)


@safe_callback
def broadcast_battle_result(battle_result):
    previous_results.append(battle_result)
    for protocol in server.protocols:
        protocol.notify_battle_result(battle_result)


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
