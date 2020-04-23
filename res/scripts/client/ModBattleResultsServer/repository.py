from Event import Event


class BattleResultRepository(object):
    def __init__(self):
        self.received_battle_result = Event()
        self._battle_results = []

    def receive_battle_result(self, battle_result):
        self._battle_results.append(battle_result)
        self.received_battle_result(battle_result)

    def get_battle_results_after(self, timestamp):
        for result in self._battle_results:
            if timestamp < result.timestamp:
                yield result
