from collections import namedtuple

from debug_utils import LOG_CURRENT_EXCEPTION
from mod_battle_results_server.parser import (
    Any,
    Fail,
    Null,
    Number,
    OneOf,
    ParserError,
    Record,
    String,
    StringLiteral,
    field,
    parse,
)
from mod_battle_results_server.util import (
    JsonParseError,
    get,
    parse_json,
    serialize_to_json,
)

Notification = namedtuple("Notification", ("method", "params"))
Request = namedtuple("Request", ("method", "params", "id"))
SuccessResponse = namedtuple("SuccessResponse", ("result", "id"))
ErrorResponse = namedtuple("Error", ("code", "message", "data", "id"))


class NotificationParser(Record):
    def __init__(self):
        super(NotificationParser, self).__init__(
            field("jsonrpc", StringLiteral("2.0")),
            field("method", String()),
            field("params", Any(), optional=True),
            field("id", Fail("Expected {context} to not be present."), optional=True),
        )

    def parse(self, value):
        parsed = super(NotificationParser, self).parse(value)
        return Notification(method=get(parsed, "method"), params=get(parsed, "params"))


class RequestParser(Record):
    def __init__(self):
        super(RequestParser, self).__init__(
            field("jsonrpc", StringLiteral("2.0")),
            field("method", String()),
            field("params", Any(), optional=True),
            field("id", OneOf(String(), Number(), Null())),
        )

    def parse(self, value):
        parsed = super(RequestParser, self).parse(value)
        return Request(
            method=get(parsed, "method"),
            params=get(parsed, "params"),
            id=get(parsed, "id"),
        )


request_parser = OneOf(RequestParser(), NotificationParser())


def make_notification(notification):
    return {
        "jsonrpc": "2.0",
        "method": notification.method,
        "params": notification.params,
    }


def make_success_response(response):
    return {"jsonrpc": "2.0", "result": response.result, "id": response.id}


def make_error_response(response):
    return {
        "jsonrpc": "2.0",
        "error": {
            "code": response.code,
            "message": response.message,
            "data": response.data,
        },
        "id": response.id,
    }


class Dispatcher(object):
    def __init__(self):
        self._handlers = dict()

    def __call__(self, data):
        try:
            json = parse_json(data)
        except JsonParseError as e:
            response = ErrorResponse(-32700, "Parse error", str(e), None)
            return serialize_to_json(make_error_response(response))
        else:
            response = self._handle(json)
            if response:
                return serialize_to_json(response)
            return None

    def add_method(self, param_parser=Any()):
        def decorator(handler):
            self._handlers[handler.__name__] = (handler, param_parser)
            return handler

        return decorator

    def _handle(self, json):
        if isinstance(json, list):
            return self._handle_batch(json)
        else:
            return self._handle_single(json)

    def _handle_batch(self, batch):
        responses = [self._handle_single(single) for single in batch]
        filtered = [response for response in responses if response is not None]
        if len(filtered) > 0:
            return filtered
        return None

    def _handle_single(self, single):
        try:
            request = parse(request_parser, single)
        except ParserError as e:
            return make_error_response(
                ErrorResponse(-32600, "Invalid Request", str(e), None)
            )
        else:
            if isinstance(request, Request):
                return self._handle_request(request.method, request.params, request.id)
            else:
                self._handle_request(request.method, request.params, None)
                return None

    def _handle_request(self, method, params, request_id):
        try:
            handler, param_parser = self._handlers[method]
        except KeyError:
            return make_error_response(
                ErrorResponse(-32601, "Method not found", None, request_id)
            )

        try:
            params = parse(param_parser, params)
        except ParserError as e:
            return make_error_response(
                ErrorResponse(-32602, "Invalid params", str(e), request_id)
            )

        try:
            return make_success_response(SuccessResponse(handler(params), request_id))
        except Exception:
            LOG_CURRENT_EXCEPTION()
            return make_error_response(
                ErrorResponse(-32603, "Internal error", None, request_id)
            )
