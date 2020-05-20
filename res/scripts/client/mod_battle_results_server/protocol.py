from typing import Any, Callable, Dict, List, Type

from async import _Future, _Promise, async
from async import await as await_
from BWUtil import AsyncReturn
from mod_async_server import Server
from mod_battle_results_server.util import get, parse_json, serialize_to_json
from mod_battle_results_server.validation import any_, field, object_, record, string
from mod_websocket_server import MessageStream

MESSAGE_TYPE = "messageType"
PAYLOAD = "payload"
validate_message = record(field(MESSAGE_TYPE, string), field(PAYLOAD, object_(any_)))


def await(future, *args, **kwargs):
    if isinstance(future, _Future):
        return await_(future, *args, **kwargs)
    else:
        promise = _Promise()
        promise.set_value(future)
        return await_(promise.get_future(), *args, **kwargs)


@async
def send(message_stream, message_type, payload):
    # type: (MessageStream, str, Any) -> _Future
    message = {MESSAGE_TYPE: message_type, PAYLOAD: payload}
    validate_message(message)
    data = serialize_to_json(message)
    yield await(message_stream.send_message(data))


class Protocol(object):
    def __init__(self):
        self._connected_handlers = []  # type: List[Callable[[MessageStream], _Future]]
        self._disconnected_handlers = (
            []
        )  # type: List[Callable[[MessageStream], _Future]]
        self._handlers = (
            dict()
        )  # type: Dict[str, List[Callable[[MessageStream, Any], _Future]]]
        self._default_handlers = (
            []
        )  # type: List[Callable[[MessageStream, str, Any], _Future]]
        self._error_handlers = (
            dict()
        )  # type: Dict[Type, List[Callable[[MessageStream, Any], _Future]]]
        self._default_error_handlers = (
            []
        )  # type: List[Callable[[MessageStream, Any], _Future]]

    @async
    def __call__(self, _, message_stream):
        # type: (Server, MessageStream) -> _Future
        self._handle_connect(message_stream)
        try:
            while True:
                data = yield await(message_stream.receive_message())
                yield await(self._handle_data(message_stream, data))
        finally:
            self._handle_disconnect(message_stream)

    def on_connected(self, func):
        # type: (Callable[[MessageStream], _Future]) -> Callable[[MessageStream], _Future]
        self._connected_handlers.append(func)
        return func

    def on_disconnected(self, func):
        # type: (Callable[[MessageStream], _Future]) -> Callable[[MessageStream], _Future]
        self._disconnected_handlers.append(func)
        return func

    def on(self, message_type):
        # type: (str) -> ...
        def decorator(func):
            # type: (Callable[[MessageStream, Any], _Future]) -> Callable[[MessageStream, Any], _Future]
            if message_type not in self._handlers:
                self._handlers[message_type] = []

            self._handlers[message_type].append(func)
            return func

        return decorator

    def on_unhandled(self, func):
        # type: (Callable[[MessageStream, str, Any], _Future]) -> Callable[[MessageStream, str, Any], _Future]
        self._default_handlers.append(func)
        return func

    def on_error(self, error_type):
        # type: (Type) -> ...
        def decorator(func):
            # type: (Callable[[MessageStream, Any], _Future]) -> Callable[[MessageStream, Any], _Future]
            if error_type not in self._error_handlers:
                self._error_handlers[error_type] = []

            self._error_handlers[error_type].append(func)
            return func

        return decorator

    def on_unhandled_error(self, func):
        # type: (Callable[[MessageStream, Any], _Future]) -> Callable[[MessageStream, Any], _Future]
        self._default_error_handlers.append(func)
        return func

    @async
    def _handle_connect(self, stream):
        # type: (MessageStream) -> _Future
        for handler in self._connected_handlers:
            yield await(handler(stream))

    @async
    def _handle_disconnect(self, stream):
        # type: (MessageStream) -> _Future
        for handler in self._disconnected_handlers:
            yield await(handler(stream))

    @async
    def _handle_data(self, stream, data):
        # type: (MessageStream, str) -> _Future
        try:
            message = parse_json(data)
            yield await(self._handle_message(stream, message))
        except Exception as e:
            handled = yield await(self._dispatch_error(stream, e))
            if not handled:
                raise e

    @async
    def _handle_message(self, stream, message):
        # type: (MessageStream, Any) -> _Future
        validate_message(message)
        message_type = get(message, MESSAGE_TYPE)
        payload = get(message, PAYLOAD)
        yield await(self._dispatch(stream, message_type, payload))

    @async
    def _dispatch(self, stream, message_type, payload):
        # type: (MessageStream, str, Any) -> _Future
        handlers = self._handlers.get(message_type, [])
        if len(handlers) > 0:
            for handler in handlers:
                yield await(handler(stream, payload))
            raise AsyncReturn(True)
        else:
            for handler in self._default_handlers:
                yield await(handler(stream, message_type, payload))
            raise AsyncReturn(False)

    @async
    def _dispatch_error(self, stream, error):
        # type: (MessageStream, Any) -> _Future
        handlers = self._error_handlers.get(type(error), [])
        if len(handlers) > 0:
            for handler in handlers:
                yield await(handler(stream, error))
            raise AsyncReturn(True)
        else:
            for handler in self._default_error_handlers:
                yield await(handler(stream, error))
            raise AsyncReturn(False)
