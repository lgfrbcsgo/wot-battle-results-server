import BigWorld

from ModBattleResultsServer.util import safe_callback


class RunLoop:
    def __init__(self, callback):
        self._callback = callback
        self._callback_id = None

    def start(self):
        self._run()

    def stop(self):
        if self._callback_id is not None:
            BigWorld.cancelCallback(self._callback_id)

    @safe_callback
    def _run(self):
        self._callback()
        self._callback_id = BigWorld.callback(0, self._run)
