from collections import deque

from chat_shared import SYS_MESSAGE_TYPE
from debug_utils import LOG_NOTE
from Event import Event
from gui.shared.gui_items.processors.common import BattleResultsGetter
from messenger.proto.events import g_messengerEvents
from mod_async import async_task, auto_run, from_adisp
from mod_battle_results_server.cache_patch import apply_patch
from mod_battle_results_server.serialization import serialize_battle_results
from mod_battle_results_server.util import get, safe_callback
from PlayerEvents import g_playerEvents

apply_patch()


class BattleResultsFetcher(object):
    def __init__(self):
        self.battle_result_fetched = Event()
        self._stopped = True
        self._account_is_player = False
        self._fetching = False
        self._queue = deque()

    def start(self):
        self._stopped = False
        g_playerEvents.onAccountBecomePlayer += self._on_account_become_player
        g_playerEvents.onAccountBecomeNonPlayer += self._on_account_become_non_player
        g_messengerEvents.serviceChannel.onChatMessageReceived += self._on_sys_message

    def stop(self):
        self._stopped = True
        g_playerEvents.onAccountBecomePlayer -= self._on_account_become_player
        g_playerEvents.onAccountBecomeNonPlayer -= self._on_account_become_non_player
        g_messengerEvents.serviceChannel.onChatMessageReceived -= self._on_sys_message

    @safe_callback
    def _on_account_become_player(self, *_, **__):
        self._account_is_player = True
        self._fetch_battle_results()

    @safe_callback
    def _on_account_become_non_player(self, *_, **__):
        self._account_is_player = False

    @safe_callback
    def _on_sys_message(self, _, message, *__, **___):
        if message.type == SYS_MESSAGE_TYPE.battleResults.index():
            arena_unique_id = get(message.data, "arenaUniqueID")
            if arena_unique_id is not None:
                self._queue.append(arena_unique_id)
                LOG_NOTE("Queued battle result {}".format(arena_unique_id))
                if self._account_is_player:
                    self._fetch_battle_results()

    @auto_run
    @async_task
    def _fetch_battle_results(self):
        if self._fetching:
            return

        self._fetching = True
        try:
            while (
                self._account_is_player and not self._stopped and len(self._queue) > 0
            ):
                arena_unique_id = self._queue.popleft()
                if arena_unique_id > 0:
                    LOG_NOTE("Fetching battle result {}".format(arena_unique_id))
                    response = yield from_adisp(
                        BattleResultsGetter(arena_unique_id).request()
                    )
                    if response.success:
                        LOG_NOTE("Fetched battle result {}".format(arena_unique_id))
                        battle_result = serialize_battle_results(response.auxData)
                        self.battle_result_fetched(battle_result)
                    else:
                        LOG_NOTE(
                            "Failed fetching battle result {}".format(arena_unique_id)
                        )

        finally:
            self._fetching = False
