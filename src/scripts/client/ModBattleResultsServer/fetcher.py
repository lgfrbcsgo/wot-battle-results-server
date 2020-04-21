from ChatManager import chatManager
from Event import Event
from ModBattleResultsServer.serialization import serialize_battle_results
from ModBattleResultsServer.util import safe_callback, get
from PlayerEvents import g_playerEvents
from adisp import process
from chat_shared import CHAT_ACTIONS, SYS_MESSAGE_TYPE
from debug_utils import LOG_NOTE
from gui.shared.gui_items.processors.common import BattleResultsGetter
from messenger.proto.bw.wrappers import ServiceChannelMessage


class BattleResultsFetcher(object):
    def __init__(self):
        self.battleResultFetched = Event()
        self._stopped = True
        self._account_is_player = False
        self._fetching = False
        self._queue = []

    def start(self):
        self._stopped = False
        g_playerEvents.onAccountBecomePlayer += self._on_account_become_player
        g_playerEvents.onAccountBecomeNonPlayer += self._on_account_become_non_player
        chatManager.subscribeChatAction(self._on_personal_sys_message, CHAT_ACTIONS.personalSysMessage)

    def stop(self):
        self._stopped = True
        g_playerEvents.onAccountBecomePlayer -= self._on_account_become_player
        g_playerEvents.onAccountBecomeNonPlayer -= self._on_account_become_non_player
        chatManager.unsubscribeChatAction(self._on_personal_sys_message, CHAT_ACTIONS.personalSysMessage)

    @safe_callback
    def _on_account_become_player(self):
        self._account_is_player = True
        self._fetch_battle_results()

    @safe_callback
    def _on_account_become_non_player(self):
        self._account_is_player = False

    @safe_callback
    def _on_personal_sys_message(self, chat_action, *args, **kwargs):
        message = ServiceChannelMessage.fromChatAction(chat_action, personal=True)
        if message.type == SYS_MESSAGE_TYPE.battleResults.index():
            arena_unique_id = get(message.data, 'arenaUniqueID')
            if arena_unique_id is not None:
                self._queue.append(arena_unique_id)
                LOG_NOTE('Queued battle result %d' % arena_unique_id)
                if self._account_is_player:
                    self._fetch_battle_results()

    @process
    def _fetch_battle_results(self):
        if self._fetching:
            return

        self._fetching = True
        try:
            while self._account_is_player and not self._stopped and len(self._queue) > 0:
                arena_unique_id = self._queue.pop()
                if arena_unique_id > 0:
                    LOG_NOTE('Fetching battle result %d' % arena_unique_id)
                    results = yield BattleResultsGetter(arena_unique_id).request()
                    if results.success:
                        result = serialize_battle_results(results.auxData)
                        LOG_NOTE('Fetched battle result %d' % arena_unique_id)
                        self.battleResultFetched(result)
                    else:
                        LOG_NOTE('Failed fetching battle result %d' % arena_unique_id)

        finally:
            self._fetching = False
