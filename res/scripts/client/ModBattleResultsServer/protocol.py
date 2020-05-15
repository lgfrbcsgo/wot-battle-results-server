from typing import Any, Callable, Dict, List, Type

from ModBattleResultsServer.util import get, parse_json, serialize_to_json
from ModBattleResultsServer.validation import (
    any_,
    array,
    field,
    object_,
    record,
    string,
)

MESSAGE_TYPE = "messageType"
PAYLOAD = "payload"
validate_message = record(field(MESSAGE_TYPE, string), field(PAYLOAD, object_(any_)))
validate_messages = array(validate_message)


def send(transport, message_type, payload):
    # type: (Transport, str, Any) -> None
    message = {MESSAGE_TYPE: message_type, PAYLOAD: payload}
    validate_message(message)
    data = serialize_to_json(message)
    transport.send_message(data)


def close(transport):
    # type: (Transport) -> None
    transport.close()


class Protocol(object):
    def __init__(self):
        self._connected_handlers = []  # type: List[Callable[[Transport], None]]
        self._disconnected_handlers = []  # type: List[Callable[[Transport], None]]
        self._handlers = (
            dict()
        )  # type: Dict[str, List[Callable[[Transport, Any], None]]]
        self._default_handlers = []  # type: List[Callable[[Transport, str, Any], None]]
        self._error_handlers = (
            dict()
        )  # type: Dict[Type, List[Callable[[Transport, Any], None]]]
        self._default_error_handlers = (
            []
        )  # type: List[Callable[[Transport, Any], None]]

    def on_connected(self, func):
        # type: (Callable[[Transport], None]) -> Callable[[Transport], None]
        self._connected_handlers.append(func)
        return func

    def on_disconnected(self, func):
        # type: (Callable[[Transport], None]) -> Callable[[Transport], None]
        self._disconnected_handlers.append(func)
        return func

    def on(self, message_type):
        # type: (str) -> ...
        def decorator(func):
            # type: (Callable[[Transport, Any], None]) -> Callable[[Transport, Any], None]
            if message_type not in self._handlers:
                self._handlers[message_type] = []

            self._handlers[message_type].append(func)
            return func

        return decorator

    def on_unhandled(self, func):
        # type: (Callable[[Transport, str, Any], None]) -> Callable[[Transport, str, Any], None]
        self._default_handlers.append(func)
        return func

    def on_error(self, error_type):
        # type: (Type) -> ...
        def decorator(func):
            # type: (Callable[[Transport, Any], None]) -> Callable[[Transport, Any], None]
            if error_type not in self._error_handlers:
                self._error_handlers[error_type] = []

            self._error_handlers[error_type].append(func)
            return func

        return decorator

    def on_unhandled_error(self, func):
        # type: (Callable[[Transport, Any], None]) -> Callable[[Transport, Any], None]
        self._default_error_handlers.append(func)
        return func

    def handle_connect(self, transport):
        # type: (Transport) -> None
        try:
            for handler in self._connected_handlers:
                handler(transport)
        except Exception as e:
            transport.close()
            raise e

    def handle_disconnect(self, transport):
        # type: (Transport) -> None
        for handler in self._disconnected_handlers:
            handler(transport)

    def handle_data(self, transport, data):
        # type: (Transport, str) -> None
        try:
            messages = parse_json(data)
            if isinstance(messages, list):
                self._handle_messages(transport, messages)
            else:
                self._handle_message(transport, messages)
        except Exception as e:
            if not self._dispatch_error(transport, e):
                raise e

    def _handle_message(self, transport, message):
        # type: (Transport ,Any) -> None
        validate_message(message)
        message_type = get(message, MESSAGE_TYPE)
        payload = get(message, PAYLOAD)
        self._dispatch(transport, message_type, payload)

    def _handle_messages(self, transport, messages):
        # type: (Transport, List[Any]) -> None
        validate_messages(messages)
        for message in messages:
            message_type = get(message, MESSAGE_TYPE)
            payload = get(message, PAYLOAD)
            self._dispatch(transport, message_type, payload)

    def _dispatch(self, transport, message_type, payload):
        handlers = self._handlers.get(message_type, [])
        if len(handlers) > 0:
            for handler in handlers:
                handler(transport, payload)
            return True
        else:
            for handler in self._default_handlers:
                handler(transport, message_type, payload)
            return False

    def _dispatch_error(self, transport, error):
        handlers = self._error_handlers.get(type(error), [])
        if len(handlers) > 0:
            for handler in handlers:
                handler(transport, error)
            return True
        else:
            for handler in self._default_error_handlers:
                handler(transport, error)
            return False


class Transport(object):
    def send_message(self, data):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError
