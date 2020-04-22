from ModBattleResultsServer.battle_results_protocol import BattleResultsProtocol
from ModBattleResultsServer.fetcher import BattleResultsFetcher
from ModBattleResultsServer.websocket import WebSocketServer
from ModBattleResultsServer.run_loop import RunLoop
from ModBattleResultsServer.gaming_session import GamingSession
from ModBattleResultsServer.util import safe_callback
from debug_utils import LOG_NOTE

HOST = 'localhost'
PORT = 61942

server = WebSocketServer(HOST, PORT, BattleResultsProtocol)
server_run_loop = RunLoop(server.serveonce)


@safe_callback
def on_battle_result_fetched(battle_result):
    result = GamingSession.current().receive_battle_result(battle_result)
    for protocol in server.protocols:
        protocol.notify_battle_result(result)


battle_results_fetcher = BattleResultsFetcher()
battle_results_fetcher.battle_result_fetched += on_battle_result_fetched


@safe_callback
def on_started_new_session():
    for protocol in server.protocols:
        protocol.notify_session_id()


GamingSession.started_new += on_started_new_session


def init():
    server_run_loop.start()
    battle_results_fetcher.start()
    LOG_NOTE('Server listening on port {}'.format(PORT))


def fini():
    server_run_loop.stop()
    server.close()
    battle_results_fetcher.stop()
    LOG_NOTE('Stopped server')
