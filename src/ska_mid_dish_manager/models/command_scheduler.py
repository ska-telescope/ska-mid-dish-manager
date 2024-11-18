"""Module containing the CommandScheduler class"""
import threading
import time
from heapq import heapify, heappop, heappush


class CommandScheduler:
    """CommandScheduler class.

    This class provides functionality to schedule commands to be executed at regular intervals.
    """

    def __init__(self, logger):
        self.logger = logger
        self.commands = []  # Min-heap to store commands to run: (next_run_time, period, command)
        self._lock = threading.Lock()  # Lock for thread-safe access to commands
        self._commands_list_updated_event = threading.Event()
        self._stop_event = threading.Event()
        self._thread = None

    def _run(self):
        """Thread that runs commands based on their scheduled times."""
        self.logger.debug("Scheduler runner thread started")

        command_to_run = None
        wait_time = 0

        while len(self.commands) > 0 and not self._stop_event.is_set():
            with self._lock:
                next_run_time, command, command_name, period = heappop(self.commands)
                current_time = time.time()

                if next_run_time > current_time:
                    wait_time = next_run_time - current_time
                    heappush(self.commands, (next_run_time, command, command_name, period))
                else:
                    # Assign the command to run outside of the lock so we don't hold on to it
                    command_to_run = command
                    # Reschedule the command
                    next_run_time = current_time + period
                    heappush(self.commands, (next_run_time, command, command_name, period))

            if command_to_run:
                self.logger.debug("Executing command %s", command_to_run)
                command_to_run()
                command_to_run = None
            elif wait_time > 0:
                self.logger.debug("Waiting %ss", wait_time)
                self._commands_list_updated_event.clear()
                self._commands_list_updated_event.wait(wait_time)
                wait_time = 0
        self.logger.debug("Scheduler runner thread exited")

    def _is_runner_thread_running(self):
        """Check if the classes runner thread is running."""
        return self._thread is not None and self._thread.is_alive()

    def _start_runner_thread(self):
        """The the classes runner thread."""
        if not self._is_runner_thread_running():
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run)
            self._thread.start()

    def is_command_scheduled(self, command_name):
        """Check if the given command name is in the list of scheduled commands."""
        for _, _, cmd_name, _ in self.commands:
            if cmd_name == command_name:
                return True
        return False

    def submit_command(self, command, command_name, period):
        """Adds a new command to run every `period` seconds."""
        next_run_time = time.time() + period
        with self._lock:
            heappush(self.commands, (next_run_time, command, command_name, period))
            self._commands_list_updated_event.set()

        if not self._is_runner_thread_running():
            self._start_runner_thread()

    def remove_command(self, command_name_to_remove):
        """Removes a scheduled command."""
        with self._lock:
            self.commands = [cmd for cmd in self.commands if cmd[2] != command_name_to_remove]
            heapify(self.commands)
            self._commands_list_updated_event.set()

    def update_command_period(self, command_name_to_update, new_period):
        """Updates the scheduled commands period."""
        with self._lock:
            for i, (_, command, command_name, _) in enumerate(self.commands):
                if command_name == command_name_to_update:
                    next_run_time = time.time() + new_period
                    self.commands[i] = (next_run_time, command, command_name, new_period)
                    heapify(self.commands)
                    self._commands_list_updated_event.set()
                    break

    def stop(self):
        """Stops the scheduler and thread."""
        self._stop_event.set()
        self._thread.join()


if __name__ == "__main__":
    command_scheduler = CommandScheduler()

    def test_cmd():
        """Test command"""
        print(f"Test ({time.time()})")

    command_scheduler.submit_command(test_cmd, "tester", 1)
    time.sleep(5)
    command_scheduler.stop()
