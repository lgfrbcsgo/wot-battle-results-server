import json
from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Type

from ModBattleResultsServer.util import get
from ModBattleResultsServer.validation import (any_, array, field, object_,
                                               record, string)

MESSAGE_TYPE = "messageType"
PAYLOAD = "payload"
validate_message = record(field(MESSAGE_TYPE, string), field(PAYLOAD, object_(any_)))
validate_messages = array(validate_message)


def send(transport, message_type, payload):
    # type: (Transport, str, Any) -> None
    message = {MESSAGE_TYPE: message_type, PAYLOAD: payload}
    validate_message(message)
    data = json.dumps(message)
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

    def default_on(self, func):
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

    def default_on_error(self, func):
        # type: (Callable[[Transport, Any], None]) -> Callable[[Transport, Any], None]
        self._default_error_handlers.append(func)
        return func

    def handle_connect(self, transport):
        # type: (Transport) -> None
        for handler in self._connected_handlers:
            handler(transport)

    def handle_disconnect(self, transport):
        # type: (Transport) -> None
        for handler in self._disconnected_handlers:
            handler(transport)

    def handle_data(self, transport, data):
        # type: (Transport, str) -> None
        with self._dispatch_catched_error(transport):
            messages = json.loads(data)
            if isinstance(messages, list):
                self.handle_messages(transport, messages)
            else:
                self.handle_message(transport, messages)

    def handle_message(self, transport, message):
        # type: (Transport ,Any) -> None
        with self._dispatch_catched_error(transport):
            validate_message(message)
            message_type = get(message, MESSAGE_TYPE)
            payload = get(message, PAYLOAD)
            self._dispatch(transport, message_type, payload)

    def handle_messages(self, transport, messages):
        # type: (Transport, List[Any]) -> None
        with self._dispatch_catched_error(transport):
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
        else:
            for handler in self._default_handlers:
                handler(transport, message_type, payload)

    def _dispatch_error(self, transport, error):
        handlers = self._error_handlers.get(type(error), [])
        if len(handlers) > 0:
            for handler in handlers:
                handler(transport, error)
        else:
            for handler in self._default_error_handlers:
                handler(transport, error)

    @contextmanager
    def _dispatch_catched_error(self, transport):
        try:
            yield
        except Exception as e:
            self._dispatch_error(transport, e)


class Transport(object):
    def send_message(self, data):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError
