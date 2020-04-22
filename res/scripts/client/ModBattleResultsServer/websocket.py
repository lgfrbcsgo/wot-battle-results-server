from functools import partial
from typing import TypeVar, Generic, Type, Generator, Any

from ModBattleResultsServer.lib.SimpleWebSocketServer import WebSocket, SimpleWebSocketServer
from ModBattleResultsServer.protocol import Protocol
from ModBattleResultsServer.transport import Transport
from ModBattleResultsServer.util import safe_callback, get
from debug_utils import LOG_NOTE


class WebSocketProtocolAdapter(WebSocket, Transport):
    def __init__(self, protocol_class, server, sock, address):
        if not issubclass(protocol_class, Protocol):
            raise TypeError('protocol_class must be a subclass of Protocol')

        super(WebSocketProtocolAdapter, self).__init__(server, sock, address)
        self.protocol = protocol_class(self)

    @safe_callback
    def handleConnected(self):
        LOG_NOTE('{host} connected on port {port} (Origin: {origin})'.format(**self.connection_info))
        self.protocol.dispatch_connected()

    @safe_callback
    def handleClose(self):
        LOG_NOTE('{host} disconnected from port {port} (Origin: {origin})'.format(**self.connection_info))
        self.protocol.dispatch_disconnected()

    @safe_callback
    def handleMessage(self):
        self.protocol.handle_data(self.data)

    def send_message(self, data):
        self.sendMessage(data)

    @property
    @property
    def connection_info(self):
        host, port = self.address[:2]
        origin = get(self.request.headers, 'Origin')
        return dict(host=host, port=port, origin=origin)


P = TypeVar('P', bound=Protocol)


class WebSocketServer(SimpleWebSocketServer, Generic[P]):
    def __init__(self, host, port, protocol_class):
        # type: (str, int, Type[P]) -> None
        websocket_class = partial(WebSocketProtocolAdapter, protocol_class)
        super(WebSocketServer, self).__init__(host, port, websocket_class, selectInterval=0)

    @property
    def protocols(self):
        # type: () -> Generator[P, Any, Any]
        for client in self.connections.itervalues():
            yield client.protocol
