import threading
import time
import os
from typing import Callable
from terminal_watching.domain.ports import LogWatcher


class FileLogWatcher(LogWatcher):
    """Watches a log file for new lines (like tail -f)."""

    def __init__(self):
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self, log_file: str, on_line: Callable[[str], None]) -> None:
        self.stop()
        self._running = True
        self._thread = threading.Thread(
            target=self._watch,
            args=(log_file, on_line),
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        self._thread = None

    def _watch(self, log_file: str, on_line: Callable[[str], None]) -> None:
        # Wait for file to exist
        while self._running and not os.path.exists(log_file):
            time.sleep(0.1)

        with open(log_file, 'r') as f:
            # Go to end of file
            f.seek(0, 2)
            while self._running:
                line = f.readline()
                if line:
                    on_line(line.rstrip('\n'))
                else:
                    time.sleep(0.05)
