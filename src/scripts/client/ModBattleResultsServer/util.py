from functools import wraps

from debug_utils import LOG_CURRENT_EXCEPTION


def unset(dct, property_name):
    if dct is not None and property_name in dct:
        del dct[property_name]


def get(dct, *path):
    for segment in path:
        if dct is None or segment not in dct:
            return None
        dct = dct[segment]

    if dct is not None:
        return dct


def safe_callback(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            LOG_CURRENT_EXCEPTION()

    return wrapper
