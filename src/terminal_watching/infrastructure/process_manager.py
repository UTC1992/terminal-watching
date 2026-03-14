import subprocess
import os
import signal
from terminal_watching.domain.ports import ProcessRunner


class AppProcessRunner(ProcessRunner):
    """Manages any application process."""

    def __init__(self):
        self._process: subprocess.Popen | None = None

    def start(self, command: list[str], log_file: str) -> None:
        self.stop()
        with open(log_file, 'w') as f:
            self._process = subprocess.Popen(
                command,
                stdout=f,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid,
            )

    def stop(self) -> None:
        if self._process and self._process.poll() is None:
            try:
                os.killpg(os.getpgid(self._process.pid), signal.SIGTERM)
                self._process.wait(timeout=10)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(os.getpgid(self._process.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
            self._process = None

    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None
