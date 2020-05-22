from mod_async import AsyncMutex, AsyncResult, async_task
from mod_battle_results_server.util import override
from shared_utils.account_helpers.BattleResultsCache import BattleResultsCache


def apply_patch():
    mutex = AsyncMutex()

    @override(BattleResultsCache, "get")
    @async_task
    def patched_get(get, self, arena_unique_id, callback):
        yield mutex.acquire()
        try:
            with AsyncResult() as async_result:
                get(self, arena_unique_id, lambda *args: async_result.resolve(args))

            return_value = yield async_result
            callback(*return_value)
        finally:
            mutex.release()
