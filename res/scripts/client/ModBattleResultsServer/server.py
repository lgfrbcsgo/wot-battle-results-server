from ModBattleResultsServer.fetcher import BattleResultsFetcher
from ModBattleResultsServer.repository import BattleResultRepository
from ModBattleResultsServer.run_loop import RunLoop
from ModBattleResultsServer.server_protocol import BattleResultsProtocol
from ModBattleResultsServer.websocket import WebSocketServer
from debug_utils import LOG_NOTE

HOST = 'localhost'
PORT = 61942

repository = BattleResultRepository()

battle_results_fetcher = BattleResultsFetcher()
battle_results_fetcher.battle_result_fetched += repository.receive_battle_result

server = WebSocketServer(HOST, PORT, lambda transport: BattleResultsProtocol(repository, transport))
server_run_loop = RunLoop(server.serveonce)


def init():
    server_run_loop.start()
    battle_results_fetcher.start()
    LOG_NOTE('Server listening on port {}'.format(PORT))


def fini():
    server_run_loop.stop()
    server.close()
    battle_results_fetcher.stop()
    LOG_NOTE('Stopped server')
