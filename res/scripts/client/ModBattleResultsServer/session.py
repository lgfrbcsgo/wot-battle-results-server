from collections import namedtuple
from uuid import uuid4

Result = namedtuple('Result', ('index', 'battle_result'))


class Session(object):
    _current = None

    def __init__(self):
        self._id = str(uuid4())
        self._results = []

    @property
    def id(self):
        return self._id

    def receive_battle_result(self, battle_result):
        result = Result(index=len(self._results), battle_result=battle_result)
        self._results.append(result)
        return result

    def query_results(self, offset=0):
        if 0 <= offset < len(self._results):
            return self._results[offset:]
        else:
            return []

    @classmethod
    def current(cls):
        if cls._current is None:
            cls._current = cls()
        return cls._current

    @classmethod
    def reset(cls):
        cls._current = None
