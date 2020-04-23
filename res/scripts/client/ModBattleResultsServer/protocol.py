import json
from collections import namedtuple
from functools import update_wrapper
from typing import Any, Mapping, Set, Callable, Union, Generator

from ModBattleResultsServer.transport import Transport
from ModBattleResultsServer.util import safe_callback

MetaMessageType = namedtuple('MetaMessageType', ('name',))


class Handler(object):
    def __init__(self, func, *message_types):
        # type: (Callable[[...], None], Union[str, MetaMessageType]) -> None
        self.message_types = message_types
        self._func = safe_callback(func)
        update_wrapper(self, self._func)

    def __call__(self, *args, **kwargs):
        return self._func(*args, **kwargs)

    def handles(self, message_type):
        # type: (Union[str, MetaMessageType]) -> bool
        return message_type in self.message_types


def handler(*message_types):
    # type: (Union[str, MetaMessageType]) -> Callable[[Callable[[...], None]], Handler]
    def decorator(func):
        return Handler(func, *message_types)

    return decorator


class Protocol(object):
    CONNECTED = MetaMessageType('CONNECTED')
    DISCONNECTED = MetaMessageType('DISCONNECTED')

    def __init__(self, transport):
        # type: (Transport) -> None
        self.transport = transport

    def handle_data(self, data):
        # type: (str) -> None
        try:
            message = json.loads(data)
        except ValueError:
            self.handle_invalid_message(data)
        else:
            self.handle_message(message)

    def handle_message(self, message):
        # type: (Any) -> None
        try:
            message_type, payload = self._deconstruct_message(**message)
        except TypeError:
            self.handle_invalid_message(json.dumps(message))
        else:
            self.dispatch(message_type, **payload)

    def handle_message_not_dispatched(self, message_type):
        # type: (str) -> None
        pass

    def handle_invalid_message(self, data):
        # type: (str) -> None
        pass

    def handle_connected(self):
        # type: () -> None
        self.dispatch(Protocol.CONNECTED)

    def handle_disconnected(self):
        # type: () -> None
        self.dispatch(Protocol.DISCONNECTED)

    def dispatch(self, message_type, **payload):
        # type: (Union[str, MetaMessageType], Any) -> None
        handled = False

        for _handler in self._handlers():
            if _handler.handles(message_type):
                _handler(self, **payload)
                handled = True

        if not handled and not isinstance(message_type, MetaMessageType):
            self.handle_message_not_dispatched(message_type)

    def send(self, message_type, **payload):
        # type: (Union[str, MetaMessageType], Any) -> None
        message = self._construct_message(message_type, payload)
        data = json.dumps(message)
        self.transport.send_message(data)

    @property
    def handled_message_types(self):
        # type: () -> Set[Union[str]]
        handled_message_types = set()

        for _handler in self._handlers():
            for message_type in _handler.message_types:
                if not isinstance(message_type, MetaMessageType):
                    handled_message_types.add(message_type)

        return handled_message_types

    @staticmethod
    def _deconstruct_message(messageType=None, **payload):
        return messageType, payload

    @staticmethod
    def _construct_message(message_type, payload):
        # type: (str, Mapping) -> Mapping
        return dict(messageType=message_type, **payload)

    @classmethod
    def _handlers(cls):
        # type: () -> Generator[Handler]
        for attribute_name in dir(cls):
            attribute = getattr(cls, attribute_name)
            if isinstance(attribute, Handler):
                yield attribute
