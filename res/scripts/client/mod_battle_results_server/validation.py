from contextlib import contextmanager


class ValidationError(Exception):
    def __init__(self, message_format, context=()):
        self.message_format = message_format
        self.context = context
        super(ValidationError, self).__init__(
            message_format.format(context="$" + "".join(context))
        )


@contextmanager
def validation_context(context):
    try:
        yield
    except ValidationError as e:
        raise ValidationError(e.message_format, (context,) + e.context)


def any_(_):
    pass


def string(value):
    if not isinstance(value, (str, unicode)):
        raise ValidationError("Expected {context} to be a string.")


def number(value):
    if not isinstance(value, (int, long, float)):
        raise ValidationError("Expected {context} to be a number.")


def object_(value_validator):
    def validate_object(container):
        if not isinstance(container, dict):
            raise ValidationError("Expected {context} to be an object.")

        for key, value in container.iteritems():
            with validation_context(".{}".format(key)):
                value_validator(value)

    return validate_object


def array(value_validator):
    def validate_array(container):
        if not isinstance(container, list):
            raise ValidationError("Expected {context} to be an array.")

        for index, value in enumerate(container):
            with validation_context("[{}]".format(index)):
                value_validator(value)

    return validate_array


def tuple_(*validators):
    def validate_tuple(container):
        if not isinstance(container, list):
            raise ValidationError("Expected {context} to be an array.")

        if len(container) != len(validators):
            raise ValidationError(
                "Expected {{context}} to be an array of length {length}.".format(
                    length=len(validators)
                )
            )

        for index, (validator, value) in enumerate(zip(validators, container)):
            with validation_context("[{}]".format(index)):
                validator(value)

    return validate_tuple


def field(name, validator, optional=False):
    return name, validator, optional


def record(*fields):
    def validate_record(container):
        if not isinstance(container, dict):
            raise ValidationError("Expected {context} to be an object.")

        for name, validator, optional in fields:
            if name not in container:
                if optional:
                    continue
                else:
                    raise ValidationError(
                        'Expected {{context}} to be an object with property "{name}."'.format(
                            name=name
                        )
                    )

            with validation_context(".{}".format(name)):
                validator(container[name])

    return validate_record


def nullable(validator):
    def validate_nullable(value):
        if value is not None:
            validator(value)

    return validate_nullable
