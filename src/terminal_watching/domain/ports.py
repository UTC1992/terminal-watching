from abc import ABC, abstractmethod
from typing import Callable, Optional


class ProcessRunner(ABC):
    """Port for running external processes."""

    @abstractmethod
    def start(self, command: list[str], log_file: str) -> None:
        pass

    @abstractmethod
    def stop(self) -> None:
        pass

    @abstractmethod
    def is_running(self) -> bool:
        pass


class LogWatcher(ABC):
    """Port for watching log file changes."""

    @abstractmethod
    def start(self, log_file: str, on_line: Callable[[str], None]) -> None:
        pass

    @abstractmethod
    def stop(self) -> None:
        pass


class FileWatcher(ABC):
    """Port for watching source file changes."""

    @abstractmethod
    def start(self, directories: list[str], extensions: list[str],
              on_change: Callable[[str], None]) -> None:
        pass

    @abstractmethod
    def stop(self) -> None:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass


class UIRenderer(ABC):
    """Port for rendering the terminal UI."""

    @abstractmethod
    def setup(self) -> None:
        pass

    @abstractmethod
    def teardown(self) -> None:
        pass

    @abstractmethod
    def render(self, state: 'AppState') -> None:
        pass

    @abstractmethod
    def get_key(self) -> Optional[str]:
        """Non-blocking key read. Returns None if no key pressed."""
        pass
