from collections import namedtuple

from mod_battle_results_server.parser import (
    Any,
    Fail,
    Integer,
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


def make_notification(notification):
    return {
        "jsonrpc": "2.0",
        "method": notification.method,
        "params": notification.params,
    }


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


def make_request(request):
    return {
        "jsonrpc": "2.0",
        "method": request.method,
        "params": request.params,
        "id": request.id,
    }


class SuccessResponseParser(Record):
    def __init__(self):
        super(SuccessResponseParser, self).__init__(
            field("jsonrpc", StringLiteral("2.0")),
            field("result", Any()),
            field("id", OneOf(String(), Number(), Null())),
        )

    def parse(self, value):
        parsed = super(SuccessResponseParser, self).parse(value)
        return SuccessResponse(result=get(parsed, "result"), id=get(parsed, "id"))


def make_success_response(response):
    return {"jsonrpc": "2.0", "result": response.result, "id": response.id}


class ErrorResponseParser(Record):
    def __init__(self):
        super(ErrorResponseParser, self).__init__(
            field("jsonrpc", StringLiteral("2.0")),
            field(
                "error",
                Record(
                    field("code", Integer()),
                    field("message", String()),
                    field("data", Any(), optional=True),
                ),
            ),
            field("id", OneOf(String(), Number(), Null())),
        )

    def parse(self, value):
        parsed = super(ErrorResponseParser, self).parse(value)
        return ErrorResponse(
            code=get(parsed, "error", "code"),
            message=get(parsed, "error", "message"),
            data=get(parsed, "error", "data"),
            id=get(parsed, "id"),
        )


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


request_parser = OneOf(RequestParser(), NotificationParser())
response_parser = OneOf(SuccessResponseParser(), ErrorResponseParser())


class Dispatcher(object):
    def __init__(self):
        self._handlers = dict()

    def __call__(self, data, **context):
        try:
            json = parse_json(data)
        except JsonParseError as e:
            response = ErrorResponse(-32700, "Parse error", str(e), None)
            return serialize_to_json(make_error_response(response))
        else:
            response = self._handle(json, context)
            if response:
                return serialize_to_json(response)
            return None

    def method(self, param_parser=Any()):
        def decorator(func):
            self._handlers[func.__name__] = (func, param_parser)
            return func

        return decorator

    def _handle(self, json, context):
        if isinstance(json, list):
            return self._handle_batch(json, context)
        else:
            return self._handle_single(json, context)

    def _handle_batch(self, batch, context):
        responses = [self._handle_single(single, context) for single in batch]
        filtered = [response for response in responses if response is not None]
        if len(filtered) > 0:
            return filtered
        return None

    def _handle_single(self, single, context):
        try:
            request = parse(request_parser, single)
        except ParserError as e:
            return make_error_response(
                ErrorResponse(-32600, "Invalid Request", str(e), None)
            )
        else:
            if isinstance(request, Request):
                return self._handle_request(
                    request.method, request.params, request.id, context
                )
            else:
                self._handle_request(request.method, request.params, None, context)
                return None

    def _handle_request(self, method, params, request_id, context):
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
            return make_success_response(
                SuccessResponse(handler(params, **context), request_id)
            )
        except Exception:
            return make_error_response(
                ErrorResponse(-32603, "Internal error", None, request_id)
            )
