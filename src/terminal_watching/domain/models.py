import time
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional


class AppStatus(Enum):
    STARTING = "STARTING..."
    COMPILING = "COMPILING..."
    BOOTING = "BOOTING..."
    READY = "READY"
    RESTARTING = "RESTARTING..."
    STOPPED = "STOPPED"
    ERROR = "ERROR"


class Tab(Enum):
    LOGS = "logs"
    ERRORS = "errors"
    REQUESTS = "requests"


_LOADING_STATUSES = frozenset({
    AppStatus.STARTING, AppStatus.COMPILING,
    AppStatus.BOOTING, AppStatus.RESTARTING,
})


@dataclass
class AppState:
    SPINNER_FRAMES = ('|', '/', '-', '\\', '|', '/', '-', '\\')

    status: AppStatus = AppStatus.STOPPED
    message: str = ""
    active_tab: Tab = Tab.LOGS
    startup_time: str = ""
    project_name: str = "Project"
    port: int = None
    log_lines: List[str] = field(default_factory=list)
    error_lines: List[str] = field(default_factory=list)
    request_lines: List[str] = field(default_factory=list)
    scroll_offset: int = 0
    wrap_lines: bool = True
    started_at: Optional[float] = None

    @property
    def is_loading(self) -> bool:
        return self.status in _LOADING_STATUSES

    @property
    def spinner_frame(self) -> str:
        if not self.is_loading:
            return ""
        idx = int(time.monotonic() * 8) % len(self.SPINNER_FRAMES)
        return self.SPINNER_FRAMES[idx]

    @property
    def uptime_seconds(self) -> int:
        if self.started_at is None:
            return 0
        return int(time.monotonic() - self.started_at)

    @property
    def uptime_display(self) -> str:
        total = self.uptime_seconds
        hours = total // 3600
        minutes = (total % 3600) // 60
        seconds = total % 60
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    @property
    def active_lines(self) -> List[str]:
        if self.active_tab == Tab.LOGS:
            return self.log_lines
        elif self.active_tab == Tab.ERRORS:
            return self.error_lines
        elif self.active_tab == Tab.REQUESTS:
            return self.request_lines
        return []

    def get_display_lines(self, cols: int) -> List[str]:
        """Get lines ready for display, wrapped if wrap mode is on."""
        raw = self.active_lines
        if not self.wrap_lines or cols <= 4:
            return raw
        width = cols - 1
        wrapped = []
        for line in raw:
            line = line.replace('\t', '  ')
            if len(line) <= width:
                wrapped.append(line)
            else:
                # First chunk
                wrapped.append(line[:width])
                remaining = line[width:]
                # Continuation chunks with indent
                cont_width = width - 2
                while len(remaining) > cont_width:
                    wrapped.append('  ' + remaining[:cont_width])
                    remaining = remaining[cont_width:]
                if remaining:
                    wrapped.append('  ' + remaining)
        return wrapped

    def max_scroll(self, visible_rows: int, cols: int = 0) -> int:
        if cols > 0 and self.wrap_lines:
            total = len(self.get_display_lines(cols))
        else:
            total = len(self.active_lines)
        return max(0, total - visible_rows)
