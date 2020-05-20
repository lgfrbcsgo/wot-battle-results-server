from collections import namedtuple

from adisp import async, process
from mod_battle_results_server.util import override
from shared_utils.account_helpers.BattleResultsCache import BattleResultsCache

Task = namedtuple("Task", ("async_task", "callback"))


def wrap_callback(callback):
    def wrapper(*args, **kwargs):
        callback((args, kwargs))

    return wrapper


def create_task(func, *args, **kwargs):
    callback, args = args[-1], args[:-1]
    async_func = async(func, cbwrapper=wrap_callback)
    return Task(async_task=async_func(*args, **kwargs), callback=callback)


def apply_patch():
    queue = []

    @override(BattleResultsCache, "get")
    @process
    def patched_get(get, *args, **kwargs):
        queue.insert(0, create_task(get, *args, **kwargs))

        if len(queue) != 1:
            return  # already processing

        while len(queue) > 0:
            task = queue[-1]
            cb_args, cb_kwargs = yield task.async_task
            task.callback(*cb_args, **cb_kwargs)
            queue.pop()
