from functools import partial

from typing import Any

from ModBattleResultsServer.lib.SimpleWebSocketServer import (
    SimpleWebSocketServer,
    WebSocket,
)
from ModBattleResultsServer.protocol import Protocol, Transport
from ModBattleResultsServer.util import get, safe_callback
from debug_utils import LOG_NOTE


class WebSocketProtocolAdapter(WebSocket, Transport):
    def __init__(self, protocol, server, sock, address):
        # type: (Protocol, Any, Any, Any) -> None
        super(WebSocketProtocolAdapter, self).__init__(server, sock, address)
        self.protocol = protocol

    @safe_callback
    def handleConnected(self):
        LOG_NOTE(
            "{host} connected on port {port} (Origin: {origin})".format(
                **self.connection_info
            )
        )
        self.protocol.handle_connect(self)

    @safe_callback
    def handleClose(self):
        LOG_NOTE(
            "{host} disconnected from port {port} (Origin: {origin})".format(
                **self.connection_info
            )
        )
        self.protocol.handle_disconnect(self)

    @safe_callback
    def handleMessage(self):
        self.protocol.handle_data(self, self.data)

    def send_message(self, data):
        self.sendMessage(data)

    @property
    def connection_info(self):
        host, port = self.address[:2]
        origin = get(self.request.headers, "Origin")
        return dict(host=host, port=port, origin=origin)


class WebSocketServer(SimpleWebSocketServer):
    def __init__(self, host, port, protocol):
        # type: (str, int, Protocol) -> None
        websocket_class = partial(WebSocketProtocolAdapter, protocol)
        super(WebSocketServer, self).__init__(
            host, port, websocket_class, selectInterval=0
        )
