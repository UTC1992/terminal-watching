import subprocess
import shutil
import threading
from typing import Callable
from terminal_watching.domain.ports import FileWatcher


class FsWatchFileWatcher(FileWatcher):
    """Watches source files for changes using fswatch."""

    def __init__(self):
        self._process: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self, directories: list[str], extensions: list[str],
              on_change: Callable[[str], None]) -> None:
        self.stop()
        if not self.is_available():
            return

        cmd = ['fswatch', '-r', '-e', '.*']
        for ext in extensions:
            cmd.extend(['-i', f'\\.{ext}$'])
        cmd.extend(['--exclude', 'build/', '--exclude', '.gradle/'])
        cmd.extend(directories)

        self._running = True
        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        self._thread = threading.Thread(
            target=self._read_output,
            args=(on_change,),
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        self._thread = None

    def is_available(self) -> bool:
        return shutil.which('fswatch') is not None

    def _read_output(self, on_change: Callable[[str], None]) -> None:
        if not self._process or not self._process.stdout:
            return
        for line in self._process.stdout:
            if not self._running:
                break
            on_change(line.strip())
