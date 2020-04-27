import json
from collections import namedtuple
from functools import update_wrapper
from typing import Any, Set, Callable, Union, Generator, List

from ModBattleResultsServer.transport import Transport
from ModBattleResultsServer.util import safe_callback, get
from ModBattleResultsServer.validation import any_, record, field, string, validate, JsonValidationError, array, object_

MetaMessageType = namedtuple('MetaMessageType', ('name',))


class Handler(object):
    def __init__(self, func, message_types, validator):
        # type: (Callable[[...], None], List[Union[str, MetaMessageType]], Callable[[Any], None]) -> None
        self.message_types = message_types
        self.validator = validator
        self._func = safe_callback(func)
        update_wrapper(self, self._func)

    def __call__(self, *args, **kwargs):
        return self._func(*args, **kwargs)

    def handles(self, message_type):
        # type: (Union[str, MetaMessageType]) -> bool
        return message_type in self.message_types


def handler(message_types, validator=any_):
    # type: (List[Union[str, MetaMessageType]], Callable[[Any], None]) -> Callable[[Callable[[...], None]], Handler]
    def decorator(func):
        return Handler(func, message_types, validator)

    return decorator


_MESSAGE_TYPE = 'messageType'
_PAYLOAD = 'payload'
_MESSAGE_VALIDATOR = record(
    field(_MESSAGE_TYPE, string),
    field(_PAYLOAD, object_)
)
_MESSAGES_VALIDATOR = array(_MESSAGE_VALIDATOR)


class Protocol(object):
    CONNECTED = MetaMessageType('CONNECTED')
    DISCONNECTED = MetaMessageType('DISCONNECTED')

    def __init__(self, transport):
        # type: (Transport) -> None
        self.transport = transport

    def handle_data(self, data):
        # type: (str) -> None
        try:
            messages = json.loads(data)
        except ValueError:
            self.handle_malformed_json(data)
        except TypeError:
            self.handle_malformed_json(None)
        else:
            if isinstance(messages, list):
                self.handle_messages(messages)
            else:
                self.handle_message(messages)

    def handle_message(self, message):
        # type: (Any) -> None
        try:
            validate(_MESSAGE_VALIDATOR, message, 'message')
        except JsonValidationError as e:
            self.handle_malformed_message(message, str(e))
        else:
            message_type = get(message, _MESSAGE_TYPE)
            payload = get(message, _PAYLOAD)
            self.dispatch(message_type, payload)

    def handle_messages(self, messages):
        # type: (List[Any]) -> None
        try:
            validate(_MESSAGES_VALIDATOR, messages, 'messages')
        except JsonValidationError as e:
            self.handle_malformed_message(messages, str(e))
        else:
            for message in messages:
                message_type = get(message, _MESSAGE_TYPE)
                payload = get(message, _PAYLOAD)
                self.dispatch(message_type, payload)

    def handle_message_not_dispatched(self, message_type):
        # type: (str) -> None
        pass

    def handle_malformed_json(self, data):
        # type: (Union[str, None]) -> None
        pass

    def handle_malformed_message(self, messages, validation_message):
        # type: (Any, str) -> None
        pass

    def handle_malformed_payload(self, message_type, payload, validation_message):
        # type: (str, Any, str) -> None
        pass

    def handle_connected(self):
        # type: () -> None
        self.dispatch(self.CONNECTED)

    def handle_disconnected(self):
        # type: () -> None
        self.dispatch(self.DISCONNECTED)

    def dispatch(self, message_type, payload=None):
        # type: (Union[str, MetaMessageType], Any) -> None
        handlers = [_handler for _handler in self._handlers() if _handler.handles(message_type)]

        if len(handlers) == 0 and not isinstance(message_type, MetaMessageType):
            self.handle_message_not_dispatched(message_type)
            return

        for _handler in handlers:
            try:
                validate(_handler.validator, payload, _PAYLOAD)
            except JsonValidationError as e:
                return self.handle_malformed_payload(message_type, payload, str(e))

        for _handler in handlers:
            _handler(self, payload)

    def send(self, message_type, payload):
        # type: (Union[str, MetaMessageType], Any) -> None
        message = {
            _MESSAGE_TYPE: message_type,
            _PAYLOAD: payload
        }
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

    @classmethod
    def _handlers(cls):
        # type: () -> Generator[Handler]
        for attribute_name in dir(cls):
            attribute = getattr(cls, attribute_name)
            if isinstance(attribute, Handler):
                yield attribute
