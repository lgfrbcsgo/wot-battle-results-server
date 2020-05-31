from mod_async import AsyncMutex, AsyncValue, async_task, auto_run
from mod_battle_results_server.util import override
from shared_utils.account_helpers.BattleResultsCache import BattleResultsCache


def apply_patch():
    mutex = AsyncMutex()

    @override(BattleResultsCache, "get")
    @auto_run
    @async_task
    def patched_get(get, self, arena_unique_id, callback):
        yield mutex.acquire()
        try:
            result = AsyncValue()
            get(self, arena_unique_id, lambda *args: result.set(args))
            return_value = yield result
            callback(*return_value)
        finally:
            mutex.release()
