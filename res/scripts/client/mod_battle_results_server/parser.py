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


class Any(Parser):
    def parse(self, value):
        return value


class Literal(Parser):
    def __init__(self, value):
        self._value = value

    def parse(self, value):
        if self._value != value:
            raise ParserError(
                "Expected {{context}} to equal {expected_value}.".format(
                    expected_value=self._value
                )
            )

        return value


class Fail(Parser):
    def __init__(self, message_format):
        self._message_format = message_format

    def parse(self, value):
        raise ParserError(self._message_format)


class String(Parser):
    def parse(self, value):
        if not isinstance(value, (str, unicode)):
            raise ParserError("Expected {context} to be a string.")
        return value


class Number(Parser):
    def parse(self, value):
        if not isinstance(value, (int, long, float)):
            raise ParserError("Expected {context} to be a number.")
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
                parsed_value = value_parser(contained_value)
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
                parsed_value = value_parser(contained_value)
            parsed_record[name] = parsed_value

        return parsed_record


class Nullable(Parser):
    def __init__(self, value_parser):
        self._value_parser = value_parser

    def parse(self, value):
        if value is not None:
            return self._value_parser(value)

        return None


class OneOf(Parser):
    def __init__(self, *parsers):
        if len(parsers) == 0:
            raise ValueError("At least one parser is required.")

        self._parsers = parsers

    def parse(self, value):
        errors = []
        for parser in self._parsers:
            try:
                with parser_context("{context}"):
                    return parser.parse(value)
            except ParserError as e:
                errors.append(str(e))

        raise ParserError(
            "Expected at least one of these to succeed:\n"
            + "\n".join(" - " + error for error in errors)
        )
