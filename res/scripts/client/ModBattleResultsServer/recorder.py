import time
from collections import namedtuple
from typing import List, Union, Generator, Any

from Event import Event

BattleResultRecord = namedtuple('BattleResult', ('recorded_at', 'result'))


class BattleResultRecorder(object):
    def __init__(self):
        self.received_battle_result = Event()
        self._records = []  # type: List[BattleResultRecord]

    def receive_battle_result(self, battle_result):
        # type: (Any) -> None
        record = BattleResultRecord(recorded_at=time.time(), result=battle_result)
        self._records.append(record)
        self.received_battle_result(record)

    def get_battle_results_after(self, timestamp):
        # type: (Union[int, long, float]) -> Generator[BattleResultRecord]
        for result in self._records:
            if timestamp < result.recorded_at:
                yield result
