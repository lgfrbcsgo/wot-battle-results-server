import json
from functools import update_wrapper

from ModBattleResultsServer.transport import Transport
from ModBattleResultsServer.util import safe_callback


class Handler(object):
    def __init__(self, func, *msg_types):
        self.msg_types = msg_types
        self._func = safe_callback(func)
        update_wrapper(self, self._func)

    def __call__(self, *args, **kwargs):
        return self._func(*args, **kwargs)

    def handles(self, msg_type):
        return msg_type in self.msg_types


def handler(*msg_types):
    def decorator(func):
        return Handler(func, *msg_types)
    return decorator


class MetaMessageToken(object):
    pass


class Protocol(object):
    CONNECTED = MetaMessageToken()
    DISCONNECTED = MetaMessageToken()

    def __init__(self, transport):
        if not isinstance(transport, Transport):
            raise TypeError('transport must be an instance of Transport')
        self.transport = transport

    def handle_data(self, data):
        try:
            msg = json.loads(data)
            msg_type, payload = self._deconstruct_message(**msg)
        except (TypeError, ValueError):
            self.handle_invalid_message(data)
        else:
            self.dispatch_message(msg_type, **payload)

    def handle_message_not_dispatched(self, msg_type):
        pass

    def handle_invalid_message(self, data):
        pass

    def dispatch_connected(self):
        self.dispatch_message(Protocol.CONNECTED)

    def dispatch_disconnected(self):
        self.dispatch_message(Protocol.DISCONNECTED)

    def dispatch_message(self, msg_type, **payload):
        handled = False

        for _handler in self._handlers():
            if _handler.handles(msg_type):
                _handler(self, **payload)
                handled = True

        if not handled and not isinstance(msg_type, MetaMessageToken):
            self.handle_message_not_dispatched(msg_type)

    def send_message(self, msg_type, **payload):
        msg = self._construct_message(msg_type, payload)
        data = json.dumps(msg)
        self.transport.send_message(data)

    @property
    def handled_msg_types(self):
        handled_msg_types = set()

        for _handler in self._handlers():
            for msg_type in _handler.msg_types:
                if not isinstance(msg_type, MetaMessageToken):
                    handled_msg_types.add(msg_type)

        return handled_msg_types

    @staticmethod
    def _deconstruct_message(msgType=None, **payload):
        return msgType, payload

    @staticmethod
    def _construct_message(msg_type, payload):
        return dict(msgType=msg_type, **payload)

    @classmethod
    def _handlers(cls):
        for attribute_name in dir(cls):
            attribute = getattr(cls, attribute_name)
            if isinstance(attribute, Handler):
                yield attribute
