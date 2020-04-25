from contextlib import contextmanager


class JsonValidationError(Exception):
    def __init__(self, message):
        self.message = message
        self.context = []

    def __str__(self):
        context = ''.join(reversed(self.context))
        return 'Expected {} to {}.'.format(context, self.message)


def expected_it_to(message):
    return JsonValidationError(message)


@contextmanager
def validation_context(context):
    try:
        yield
    except JsonValidationError as e:
        e.context.append(context)
        raise e


def any_(_):
    pass


def string(value):
    if not isinstance(value, (str, unicode)):
        raise expected_it_to('be a string')


def number(value):
    if not isinstance(value, (int, long, float)):
        raise expected_it_to('be a number')


def object_(validator):
    def validate_object(container):
        if not isinstance(container, dict):
            raise expected_it_to('be an object')

        for key, value in container.iteritems():
            with validation_context('.{}'.format(key)):
                validator(value)

    return validate_object


def array(validator):
    def validate_array(container):
        if not isinstance(container, list):
            raise expected_it_to('be an array')

        for index, value in enumerate(container):
            with validation_context('[{}]'.format(index)):
                validator(value)

    return validate_array


def tuple_(*validators):
    def validate_tuple(container):
        if not isinstance(container, list):
            raise expected_it_to('be an array')

        if len(container) != len(validators):
            raise expected_it_to('have length {}'.format(len(validators)))

        for index, (validator, value) in enumerate(zip(validators, container)):
            with validation_context('[{}]'.format(index)):
                validator(value)

    return validate_tuple


def field(name, validator, optional=False):
    return name, validator, optional


def record(*fields):
    def validate_record(container):
        if not isinstance(container, dict):
            raise expected_it_to('be an object')

        for name, validator, optional in fields:
            if name not in container:
                if optional:
                    continue
                else:
                    raise expected_it_to('have a property "{}"'.format(name))

            with validation_context('.{}'.format(name)):
                validator(container[name])

    return validate_record


def nullable(validator):
    def validate_nullable(value):
        if value is not None:
            validator(value)

    return validate_nullable


def validate(validator, obj, context='value'):
    with validation_context(context):
        validator(obj)
