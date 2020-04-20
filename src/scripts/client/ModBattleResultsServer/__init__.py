import json

from ModBattleResultsServer.fetcher import BattleResultsFetcher
from ModBattleResultsServer.lib.SimpleWebSocketServer import WebSocket, SimpleWebSocketServer
from ModBattleResultsServer.run_loop import RunLoop
from ModBattleResultsServer.util import safe_callback, get
from debug_utils import LOG_NOTE

HOST = 'localhost'
PORT = 61942

previous_results = []


class WebSocketHandler(WebSocket):
    @safe_callback
    def handleConnected(self):
        host, port = self.address[:2]
        origin = get(self.request.headers, 'Origin')
        if origin is not None:
            LOG_NOTE('%s connected on port %d (Origin: %s)' % (host, port, origin))
        else:
            LOG_NOTE('%s connected on port %d' % (host, port))
        for data in previous_results:
            self.sendMessage(data)

    @safe_callback
    def handleClose(self):
        host, port = self.address[:2]
        origin = get(self.request.headers, 'Origin')
        if origin is not None:
            LOG_NOTE('%s disconnected from port %d (Origin: %s)' % (host, port, origin))
        else:
            LOG_NOTE('%s disconnected from port %d' % (host, port))

    @safe_callback
    def handleMessage(self):
        pass


server = SimpleWebSocketServer(HOST, PORT, WebSocketHandler, selectInterval=0)
run_loop = RunLoop(server.serveonce)


@safe_callback
def message_results(battle_result):
    data = json.dumps(battle_result)
    previous_results.append(data)
    for client in server.connections.itervalues():
        client.sendMessage(data)


battle_results_fetcher = BattleResultsFetcher()
battle_results_fetcher.battleResultFetched += message_results


def init():
    run_loop.start()
    battle_results_fetcher.start()
    LOG_NOTE('Server listening on port %d' % PORT)


def fini():
    run_loop.stop()
    server.close()
    battle_results_fetcher.stop()
    LOG_NOTE('Stopped server')
