import inspect
import sys
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

    return dct


def safe_callback(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            LOG_CURRENT_EXCEPTION()

    return wrapper


def hook(hook_handler):
    def build_decorator(module, func_name):
        def decorator(func):
            orig_func = getattr(module, func_name)

            @wraps(orig_func)
            def func_wrapper(*args, **kwargs):
                return hook_handler(orig_func, func, *args, **kwargs)

            if inspect.ismodule(module):
                setattr(sys.modules[module.__name__], func_name, func_wrapper)
            elif inspect.isclass(module):
                setattr(module, func_name, func_wrapper)

            return func

        return decorator

    return build_decorator


@hook
def override(orig_func, func, *args, **kwargs):
    try:
        return func(orig_func, *args, **kwargs)
    except:
        LOG_CURRENT_EXCEPTION()
        return orig_func(*args, **kwargs)
