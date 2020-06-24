class Parser(object):
    def parse(self, path, value):
        raise NotImplementedError()


class ParserError(Exception):
    pass


def parse(parser, value, context="$"):
    return parser.parse(context, value)


class Any(Parser):
    def parse(self, _, value):
        return value


class StringLiteral(Parser):
    def __init__(self, value):
        if not isinstance(value, (str, unicode)):
            raise TypeError("Expected a string.")
        self._value = value

    def parse(self, path, value):
        if self._value != value:
            raise ParserError(
                "Expected {path} to be '{expected_value}'.".format(
                    expected_value=self._value, path=path,
                )
            )

        return value


class Fail(Parser):
    def __init__(self, message):
        self._message = message

    def parse(self, path, value):
        raise ParserError(
            "Expectation failed at {path}: {message}".format(
                path=path, message=self._message
            )
        )


class Null(Parser):
    def parse(self, path, value):
        if value is not None:
            raise ParserError("Expected {path} to be null.".format(path=path))
        return None


class Boolean(Parser):
    def parse(self, path, value):
        if not isinstance(value, bool):
            raise ParserError("Expected {path} to be a boolean.".format(path=path))
        return value


class String(Parser):
    def parse(self, path, value):
        if not isinstance(value, (str, unicode)):
            raise ParserError("Expected {path} to be a string.".format(path=path))
        return value


class Number(Parser):
    def parse(self, path, value):
        if not isinstance(value, (int, long, float)) or isinstance(value, bool):
            raise ParserError("Expected {path} to be a number.".format(path=path))
        return value


class Integer(Parser):
    def parse(self, path, value):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ParserError("Expected {path} to be an integer.".format(path=path))
        return value


class Object(Parser):
    def __init__(self, value_parser, key_parser=String()):
        self._key_parser = key_parser
        self._value_parser = value_parser

    def parse(self, path, value):
        if not isinstance(value, dict):
            raise ParserError("Expected {path} to be an object.".format(path=path))

        parsed_dict = dict()
        for key, contained_value in value.iteritems():
            parsed_key = self._key_parser.parse(
                "{path}@key={key}".format(path=path, key=key), key
            )
            parsed_value = self._value_parser.parse(
                "{path}.{key}".format(path=path, key=key), contained_value
            )
            parsed_dict[parsed_key] = parsed_value

        return parsed_dict


class Array(Parser):
    def __init__(self, value_parser):
        self._value_parser = value_parser

    def parse(self, path, value):
        if not isinstance(value, list):
            raise ParserError("Expected {path} to be an array.".format(path=path))

        parsed_list = []
        for index, contained_value in enumerate(value):
            parsed_value = self._value_parser.parse(
                "{path}[{index}]".format(path=path, index=index), contained_value
            )
            parsed_list.append(parsed_value)

        return parsed_list


class Tuple(Parser):
    def __init__(self, *value_parsers):
        self._value_parsers = value_parsers

    def parse(self, path, value):
        if not isinstance(value, list):
            raise ParserError("Expected {path} to be an array.".format(path=path))

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
            parsed_value = value_parser.parse(
                "{path}[{index}]".format(path=path, index=index), contained_value
            )
            parsed_list.append(parsed_value)

        return tuple(parsed_list)


def field(name, value_parser, optional=False):
    return name, value_parser, optional


class Record(Parser):
    def __init__(self, *fields):
        self._fields = fields

    def parse(self, path, value):
        if not isinstance(value, dict):
            raise ParserError("Expected {path} to be an object.".format(path=path))

        parsed_record = dict()
        for name, value_parser, optional in self._fields:
            if name not in value:
                if optional:
                    continue
                else:
                    raise ParserError(
                        'Expected {path} to be an object with property "{name}."'.format(
                            path=path, name=name
                        )
                    )
            contained_value = value[name]
            parsed_value = value_parser.parse(
                "{path}.{name}".format(path=path, name=name), contained_value
            )
            parsed_record[name] = parsed_value

        return parsed_record


class OneOf(Parser):
    def __init__(self, *parsers):
        if len(parsers) == 0:
            raise ValueError("At least one parser is required.")

        self._parsers = parsers

    def parse(self, path, value):
        errors = set()
        for parser in self._parsers:
            try:
                return parser.parse(path, value)
            except ParserError as e:
                errors.add(str(e))

        raise ParserError(
            "Expected at least one of these to succeed:\n"
            + "\n".join(" - " + error for error in errors)
        )


class Nullable(OneOf):
    def __init__(self, value_parser):
        super(Nullable, self).__init__(Null(), value_parser)
