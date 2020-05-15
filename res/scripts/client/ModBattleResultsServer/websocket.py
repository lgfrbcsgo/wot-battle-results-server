from functools import partial
from typing import Any

from ModBattleResultsServer.lib.SimpleWebSocketServer import (
    SimpleWebSocketServer, WebSocket)
from ModBattleResultsServer.protocol import Protocol, Transport
from ModBattleResultsServer.util import get, safe_callback


class WebSocketTransport(WebSocket, Transport):
    def __init__(self, protocol, server, sock, address):
        # type: (Protocol, Any, Any, Any) -> None
        super(WebSocketTransport, self).__init__(server, sock, address)
        self.protocol = protocol

    @safe_callback
    def handleConnected(self):
        self.protocol.handle_connect(self)

    @safe_callback
    def handleClose(self):
        self.protocol.handle_disconnect(self)

    @safe_callback
    def handleMessage(self):
        self.protocol.handle_data(self, self.data)

    def send_message(self, data):
        self.sendMessage(data)

    def __str__(self):
        host, port = self.address[:2]
        origin = get(self.request.headers, "Origin")
        return 'WebSocketTransport(host="{host}", port={port}, origin="{origin}")'.format(
            host=host, port=port, origin=origin
        )


class WebSocketServer(SimpleWebSocketServer):
    def __init__(self, host, port, protocol):
        # type: (str, int, Protocol) -> None
        websocket_class = partial(WebSocketTransport, protocol)
        super(WebSocketServer, self).__init__(
            host, port, websocket_class, selectInterval=0
        )
