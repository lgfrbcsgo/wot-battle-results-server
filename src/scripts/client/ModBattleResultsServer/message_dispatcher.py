import functools
import json

from ModBattleResultsServer.lib.SimpleWebSocketServer import WebSocket
from ModBattleResultsServer.util import get, safe_callback, unset

MSG_TYPE = 'msgType'


class Handler(object):
    def __init__(self, func, *msg_types):
        self.msg_types = set(msg_types)
        self._func = func
        functools.update_wrapper(self, func)

    def __call__(self, *args, **kwargs):
        return self._func(*args, **kwargs)


def handler(*msg_types):
    def decorator(func):
        return Handler(func, *msg_types)
    return decorator


class WebSocketProtocol(object):
    CONNECTED = '[WebSocketMessageDispatcher] CONNECTED'
    DISCONNECTED = '[WebSocketMessageDispatcher] DISCONNECTED'
    _MESSAGES = (CONNECTED, DISCONNECTED)

    def __init__(self, connection):
        if not isinstance(connection, WebSocket):
            raise TypeError('connection must be an instance of SimpleWebSocketServer.WebSocket')
        self.connection = connection

    def handle_data(self, data):
        msg = json.loads(data)
        msg_type = get(msg, MSG_TYPE)
        unset(msg, MSG_TYPE)
        self.dispatch_message(msg_type, **msg)

    def message_not_dispatched(self, msg_type, payload):
        pass

    def dispatch_connected(self):
        self.dispatch_message(WebSocketProtocol.CONNECTED)

    def dispatch_disconnected(self):
        self.dispatch_message(WebSocketProtocol.DISCONNECTED)

    def dispatch_message(self, msg_type, **payload):
        if msg_type is None:
            return

        handled = False
        for attribute_name in dir(self):
            attribute = getattr(self, attribute_name)
            if isinstance(attribute, Handler) and msg_type in attribute.msg_types:
                attribute(self, msg_type, **payload)
                handled = True

        if not handled and msg_type not in WebSocketProtocol._MESSAGES:
            self.message_not_dispatched(msg_type, **payload)

    def send_message(self, msg_type, **payload):
        payload[MSG_TYPE] = msg_type
        data = json.dumps(payload)
        self.connection.sendMessage(data)

    @property
    def connection_info(self):
        host, port = self.connection.address[:2]
        origin = get(self.connection.request.headers, 'Origin')
        return host, port, origin


def websocket(dispatcher_class):
    if not issubclass(dispatcher_class, WebSocketProtocol):
        raise TypeError('dispatcher_class must be a subclass of WebSocketMessageDispatcher')

    class DispatchingWebSocket(WebSocket):
        def __init__(self, server, sock, address):
            super(DispatchingWebSocket, self).__init__(server, sock, address)
            self.dispatcher = dispatcher_class(self)

        @safe_callback
        def handleConnected(self):
            self.dispatcher.dispatch_connected()

        @safe_callback
        def handleClose(self):
            self.dispatcher.dispatch_disconnected()

        @safe_callback
        def handleMessage(self):
            self.dispatcher.handle_data(self.data)

    return DispatchingWebSocket
