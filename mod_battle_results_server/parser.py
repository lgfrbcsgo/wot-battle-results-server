from contextlib import contextmanager


class Parser(object):
    def parse(self, value):
        raise NotImplementedError()


class ParserError(Exception):
    def __init__(self, message_format, context=()):
        self.message_format = message_format
        self.context = context
        super(ParserError, self).__init__(
            message_format.format(context="".join(context))
        )


@contextmanager
def parser_context(context):
    try:
        yield
    except ParserError as e:
        raise ParserError(e.message_format, (context,) + e.context)


def parse(parser, value, context="$"):
    with parser_context(context):
        return parser.parse(value)


class Any(Parser):
    def parse(self, value):
        return value


class StringLiteral(Parser):
    def __init__(self, value):
        if not isinstance(value, (str, unicode)):
            raise TypeError("Expected a string.")
        self._value = value

    def parse(self, value):
        if self._value != value:
            raise ParserError(
                "Expected {{context}} to be '{expected_value}'.".format(
                    expected_value=self._value
                )
            )

        return value


class Fail(Parser):
    def __init__(self, message_format):
        self._message_format = message_format

    def parse(self, value):
        raise ParserError(self._message_format)


class Null(Parser):
    def parse(self, value):
        if value is not None:
            raise ParserError("Expected {context} to be null.")
        return None


class Boolean(Parser):
    def parse(self, value):
        if not isinstance(value, bool):
            raise ParserError("Expected {context} to be a boolean.")
        return value


class String(Parser):
    def parse(self, value):
        if not isinstance(value, (str, unicode)):
            raise ParserError("Expected {context} to be a string.")
        return value


class Number(Parser):
    def parse(self, value):
        if not isinstance(value, (int, long, float)) or isinstance(value, bool):
            raise ParserError("Expected {context} to be a number.")
        return value


class Integer(Parser):
    def parse(self, value):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ParserError("Expected {context} to be an integer.")
        return value


class Object(Parser):
    def __init__(self, value_parser, key_parser=None):
        if key_parser is None:
            key_parser = String()
        self._key_parser = key_parser
        self._value_parser = value_parser

    def parse(self, value):
        if not isinstance(value, dict):
            raise ParserError("Expected {context} to be an object.")

        parsed_dict = dict()
        for key, contained_value in value.iteritems():
            with parser_context("@key={}".format(key)):
                parsed_key = self._key_parser.parse(key)
            with parser_context(".{}".format(key)):
                parsed_value = self._value_parser.parse(contained_value)
            parsed_dict[parsed_key] = parsed_value

        return parsed_dict


class Array(Parser):
    def __init__(self, value_parser):
        self._value_parser = value_parser

    def parse(self, value):
        if not isinstance(value, list):
            raise ParserError("Expected {context} to be an array.")

        parsed_list = []
        for index, contained_value in enumerate(value):
            with parser_context("[{}]".format(index)):
                parsed_value = self._value_parser.parse(contained_value)
            parsed_list.append(parsed_value)

        return parsed_list


class Tuple(Parser):
    def __init__(self, *value_parsers):
        self._value_parsers = value_parsers

    def parse(self, value):
        if not isinstance(value, list):
            raise ParserError("Expected {context} to be an array.")

        if len(value) != len(self._value_parsers):
            raise ParserError(
                "Expected {{context}} to be an array of length {length}.".format(
                    length=len(self._value_parsers)
                )
            )

        parsed_list = []
        for index, (value_parser, contained_value) in enumerate(
            zip(self._value_parsers, value)
        ):
            with parser_context("[{}]".format(index)):
                parsed_value = value_parser.parse(contained_value)
            parsed_list.append(parsed_value)

        return tuple(parsed_list)


def field(name, value_parser, optional=False):
    return name, value_parser, optional


class Record(Parser):
    def __init__(self, *fields):
        self._fields = fields

    def parse(self, value):
        if not isinstance(value, dict):
            raise ParserError("Expected {context} to be an object.")

        parsed_record = dict()
        for name, value_parser, optional in self._fields:
            if name not in value:
                if optional:
                    continue
                else:
                    raise ParserError(
                        'Expected {{context}} to be an object with property "{name}."'.format(
                            name=name
                        )
                    )
            contained_value = value[name]
            with parser_context(".{}".format(name)):
                parsed_value = value_parser.parse(contained_value)
            parsed_record[name] = parsed_value

        return parsed_record


class OneOf(Parser):
    def __init__(self, *parsers):
        if len(parsers) == 0:
            raise ValueError("At least one parser is required.")

        self._parsers = parsers

    def parse(self, value):
        errors = set()
        for parser in self._parsers:
            try:
                with parser_context("{context}"):
                    return parser.parse(value)
            except ParserError as e:
                errors.add(str(e))

        raise ParserError(
            "Expected at least one of these to succeed:\n"
            + "\n".join(" - " + error for error in errors)
        )


class Nullable(OneOf):
    def __init__(self, value_parser):
        super(Nullable, self).__init__(Null(), value_parser)
