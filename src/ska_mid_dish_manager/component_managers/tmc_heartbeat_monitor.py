import threading
import time


class HeartbeatChecker:
    """A class to poll TMC's heartbeat."""

    def __init__(self, component_manager):
        self.cm = component_manager
        self._tmc_polling_thread = threading.Thread(target=self._tmc_polling_loop, daemon=True)
        self._tmc_polling_thread.start()

    def _tmc_polling_loop(self):
        while True:
            try:
                interval = self.cm.component_state.get("tmcheartbeatinterval")

                if interval == 0:
                    continue
                self.cm.check_connection()
            except Exception as e:
                self.cm.logger.error(f"Error in TMC heartbeat polling: {e}")
            time.sleep(1)
