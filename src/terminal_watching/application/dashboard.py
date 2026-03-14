import re
import threading
import time
from terminal_watching.domain.models import AppState, AppStatus, Tab
from terminal_watching.domain.ports import ProcessRunner, LogWatcher, FileWatcher, UIRenderer


MAX_LINES = 5000
REQUEST_PATTERNS = re.compile(r'Completed [0-9]|servlet\.request|"(POST|GET|PUT|DELETE)')


class Dashboard:
    """Main orchestrator — coordinates all components."""

    def __init__(
        self,
        process_runner: ProcessRunner,
        log_watcher: LogWatcher,
        file_watcher: FileWatcher,
        ui: UIRenderer,
        project_dir: str,
        project_name: str,
        command: list[str],
        log_file: str,
        watch_dirs: list[str],
        watch_extensions: list[str],
        port: int = None,
        ready_pattern: str = '',
        error_patterns: list[str] = None,
    ):
        self._process = process_runner
        self._log_watcher = log_watcher
        self._file_watcher = file_watcher
        self._ui = ui
        self._project_dir = project_dir
        self._project_name = project_name
        self._command = command
        self._log_file = log_file
        self._watch_dirs = watch_dirs
        self._watch_extensions = watch_extensions
        self._port = port
        self._ready_re = re.compile(ready_pattern) if ready_pattern else None
        self._error_re = re.compile('|'.join(error_patterns)) if error_patterns else re.compile(r'ERROR|Exception')
        self._state = AppState()
        self._state.project_name = project_name
        self._state.port = port
        self._lock = threading.Lock()
        self._running = False
        self._auto_scroll = True
        self._dirty = True
        self._scroll_velocity = 0.0
        self._scroll_frac = 0.0  # fractional scroll accumulator

    def run(self) -> None:
        self._running = True
        self._ui.setup()
        try:
            self._start_app()
            self._start_file_watcher()
            self._main_loop()
        finally:
            self._shutdown()

    def _main_loop(self) -> None:
        last_render = 0
        while self._running:
            # Process all pending keys without delay
            had_key = False
            key = self._ui.get_key()
            while key:
                self._handle_key(key)
                had_key = True
                key = self._ui.get_key()

            # Apply momentum scrolling
            if abs(self._scroll_velocity) > 0.1:
                self._scroll_frac += self._scroll_velocity
                lines = int(self._scroll_frac)
                if lines != 0:
                    with self._lock:
                        self._apply_scroll(lines)
                    self._scroll_frac -= lines
                    self._dirty = True
                # Friction — decelerate (higher = more friction)
                self._scroll_velocity *= 0.75
            else:
                self._scroll_velocity = 0.0
                self._scroll_frac = 0.0

            now = time.monotonic()
            if had_key or (self._dirty and now - last_render > 0.03):
                with self._lock:
                    self._ui.render(self._state)
                    self._dirty = False
                    last_render = now

            time.sleep(0.016)  # ~60fps

    def _handle_key(self, key: str) -> None:
        with self._lock:
            if key == 'q':
                self._running = False
            elif key == 'r':
                self._restart_app()
            elif key == 'e':
                self._switch_tab(Tab.ERRORS)
            elif key == 'h':
                self._switch_tab(Tab.REQUESTS)
            elif key == 'l':
                self._switch_tab(Tab.LOGS)
            elif key == 'UP':
                self._scroll(-1)
            elif key == 'DOWN':
                self._scroll(1)
            elif key == 'SCROLL_UP':
                self._add_scroll_impulse(-0.15)
            elif key == 'SCROLL_DOWN':
                self._add_scroll_impulse(0.15)
            elif key == 'PGUP':
                self._scroll(-20)
            elif key == 'PGDN':
                self._scroll(20)
            elif key == 'w':
                self._state.wrap_lines = not self._state.wrap_lines
                self._state.scroll_offset = self._state.max_scroll(self._content_rows(), self._content_cols())
                self._auto_scroll = True

    def _switch_tab(self, tab: Tab) -> None:
        self._state.active_tab = tab
        self._state.scroll_offset = self._state.max_scroll(self._content_rows(), self._content_cols())
        self._auto_scroll = True

    def _add_scroll_impulse(self, impulse: float) -> None:
        """Add velocity for momentum scrolling (trackpad/mouse wheel)."""
        # Cap max velocity to keep it gentle
        self._scroll_velocity = max(-3.0, min(3.0, self._scroll_velocity + impulse))
        self._auto_scroll = False

    def _apply_scroll(self, delta: int) -> None:
        """Apply scroll delta to state (used by momentum)."""
        new_offset = self._state.scroll_offset + delta
        max_s = self._state.max_scroll(self._content_rows(), self._content_cols())
        self._state.scroll_offset = max(0, min(new_offset, max_s))
        if self._state.scroll_offset >= max_s:
            self._auto_scroll = True
            self._scroll_velocity = 0.0
        if self._state.scroll_offset <= 0:
            self._scroll_velocity = 0.0

    def _scroll(self, delta: int) -> None:
        """Instant scroll (arrow keys, pgup/pgdn)."""
        self._scroll_velocity = 0.0
        self._auto_scroll = False
        new_offset = self._state.scroll_offset + delta
        max_s = self._state.max_scroll(self._content_rows(), self._content_cols())
        self._state.scroll_offset = max(0, min(new_offset, max_s))
        if self._state.scroll_offset >= max_s:
            self._auto_scroll = True

    def _content_rows(self) -> int:
        # header=8, tabs=3, minimum=10
        return max(10, 24 - 11)

    def _content_cols(self) -> int:
        return 80  # default, UI will use actual cols

    def _start_app(self) -> None:
        with self._lock:
            self._state.status = AppStatus.STARTING
            self._state.message = ""
            self._state.log_lines.clear()
            self._state.error_lines.clear()
            self._state.request_lines.clear()
            self._state.scroll_offset = 0

        self._process.start(self._command, self._log_file)
        self._log_watcher.start(self._log_file, self._on_log_line)

    def _restart_app(self) -> None:
        self._state.status = AppStatus.RESTARTING
        self._state.message = "Manual restart"
        self._log_watcher.stop()
        self._process.stop()
        self._start_app()

    def _start_file_watcher(self) -> None:
        if self._file_watcher.is_available():
            self._file_watcher.start(
                self._watch_dirs,
                self._watch_extensions,
                self._on_file_change,
            )

    def _on_log_line(self, line: str) -> None:
        with self._lock:
            # Add to logs
            self._state.log_lines.append(line)
            if len(self._state.log_lines) > MAX_LINES:
                self._state.log_lines = self._state.log_lines[-MAX_LINES:]

            # Classify as error
            if self._error_re and self._error_re.search(line):
                self._state.error_lines.append(line)
                if len(self._state.error_lines) > MAX_LINES:
                    self._state.error_lines = self._state.error_lines[-MAX_LINES:]

            # Classify as request
            if REQUEST_PATTERNS.search(line):
                self._state.request_lines.append(line)
                if len(self._state.request_lines) > MAX_LINES:
                    self._state.request_lines = self._state.request_lines[-MAX_LINES:]

            # Detect ready
            if self._ready_re and self._ready_re.search(line):
                self._state.status = AppStatus.READY
                # Try to extract time
                time_match = re.search(r'(\d+\.?\d*\s*(?:seconds|ms|s))', line)
                if time_match:
                    self._state.startup_time = time_match.group(1)
                    self._state.message = f"Started in {self._state.startup_time}"
                else:
                    self._state.message = "Ready"

            # Detect errors in status (only if not already ready)
            if self._state.status != AppStatus.READY:
                if self._error_re and self._error_re.search(line):
                    # Only set ERROR status for severe errors, not warnings
                    if any(p in line for p in ['FAILED', 'fatal', 'panic', 'EADDRINUSE']):
                        self._state.status = AppStatus.ERROR
                        self._state.message = "Failed - press e to see errors"

            # Auto-scroll
            if self._auto_scroll:
                self._state.scroll_offset = self._state.max_scroll(self._content_rows(), self._content_cols())

            self._dirty = True

    def _on_file_change(self, filepath: str) -> None:
        filename = filepath.rsplit('/', 1)[-1] if '/' in filepath else filepath
        with self._lock:
            self._state.status = AppStatus.RESTARTING
            self._state.message = f"Changed: {filename}"

        self._log_watcher.stop()
        self._process.stop()
        self._start_app()

    def _shutdown(self) -> None:
        self._file_watcher.stop()
        self._log_watcher.stop()
        self._process.stop()
        self._ui.teardown()
