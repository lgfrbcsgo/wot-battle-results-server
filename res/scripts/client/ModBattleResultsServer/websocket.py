from functools import partial
from typing import TypeVar, Generic, Type, Generator, Any

from ModBattleResultsServer.lib.SimpleWebSocketServer import WebSocket, SimpleWebSocketServer
from ModBattleResultsServer.protocol import Protocol
from ModBattleResultsServer.transport import Transport
from ModBattleResultsServer.util import safe_callback, get


class WebSocketProtocolAdapter(WebSocket, Transport):
    def __init__(self, protocol_class, server, sock, address):
        if not issubclass(protocol_class, Protocol):
            raise TypeError('protocol_class must be a subclass of Protocol')

        super(WebSocketProtocolAdapter, self).__init__(server, sock, address)
        self.protocol = protocol_class(self)

    @safe_callback
    def handleConnected(self):
        self.protocol.dispatch_connected()

    @safe_callback
    def handleClose(self):
        self.protocol.dispatch_disconnected()

    @safe_callback
    def handleMessage(self):
        self.protocol.handle_data(self.data)

    def send_message(self, data):
        self.sendMessage(data)

    @property
    def host(self):
        return self.address[0]

    @property
    def port(self):
        return self.address[1]

    @property
    def origin(self):
        return get(self.request.headers, 'Origin')


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
