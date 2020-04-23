from typing import List, Union, Generator

from Event import Event
from ModBattleResultsServer.batte_result import BattleResult


class BattleResultRepository(object):
    def __init__(self):
        self.received_battle_result = Event()
        self._battle_results = []  # type: List[BattleResult]

    def receive_battle_result(self, battle_result):
        # type: (BattleResult) -> None
        self._battle_results.append(battle_result)
        self.received_battle_result(battle_result)

    def get_battle_results_after(self, timestamp):
        # type: (Union[int, long, float]) -> Generator[BattleResult]
        for result in self._battle_results:
            if timestamp < result.received_at:
                yield result
