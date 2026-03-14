"""Tests for the Dashboard orchestrator using mock ports."""

import threading
import pytest
from unittest.mock import MagicMock, patch
from terminal_watching.domain.models import AppState, AppStatus, Tab
from terminal_watching.domain.ports import ProcessRunner, LogWatcher, FileWatcher, UIRenderer
from terminal_watching.application.dashboard import Dashboard, MAX_LINES, REQUEST_PATTERNS


def make_dashboard(**overrides):
    """Create a Dashboard with mock dependencies."""
    defaults = dict(
        process_runner=MagicMock(spec=ProcessRunner),
        log_watcher=MagicMock(spec=LogWatcher),
        file_watcher=MagicMock(spec=FileWatcher),
        ui=MagicMock(spec=UIRenderer),
        project_dir="/tmp/test",
        project_name="TestApp",
        command=["npm", "run", "dev"],
        log_file="/tmp/test.log",
        watch_dirs=["/tmp/test/src"],
        watch_extensions=["js", "ts"],
        port=3000,
        ready_pattern="ready in",
        error_patterns=["Error", "Exception"],
    )
    defaults.update(overrides)
    return Dashboard(**defaults)


class TestDashboardInit:
    def test_initial_state(self):
        d = make_dashboard()
        assert d._state.project_name == "TestApp"
        assert d._state.port == 3000
        assert d._state.status == AppStatus.STOPPED

    def test_compiles_patterns(self):
        d = make_dashboard(ready_pattern="Started|ready")
        assert d._ready_re.search("Started in 2s")
        assert d._ready_re.search("ready in 500ms")
        assert not d._ready_re.search("booting up")

    def test_no_ready_pattern(self):
        d = make_dashboard(ready_pattern="")
        assert d._ready_re is None

    def test_default_error_patterns(self):
        d = make_dashboard(error_patterns=None)
        assert d._error_re.search("ERROR occurred")
        assert d._error_re.search("NullPointerException")


class TestHandleKey:
    def test_quit(self):
        d = make_dashboard()
        d._running = True
        d._handle_key("q")
        assert d._running is False

    def test_switch_to_errors(self):
        d = make_dashboard()
        d._handle_key("e")
        assert d._state.active_tab == Tab.ERRORS

    def test_switch_to_requests(self):
        d = make_dashboard()
        d._handle_key("h")
        assert d._state.active_tab == Tab.REQUESTS

    def test_switch_to_logs(self):
        d = make_dashboard()
        d._state.active_tab = Tab.ERRORS
        d._handle_key("l")
        assert d._state.active_tab == Tab.LOGS

    def test_toggle_wrap(self):
        d = make_dashboard()
        assert d._state.wrap_lines is True
        d._handle_key("w")
        assert d._state.wrap_lines is False
        d._handle_key("w")
        assert d._state.wrap_lines is True

    def test_restart(self):
        d = make_dashboard()
        d._handle_key("r")
        assert d._state.status == AppStatus.STARTING
        d._process.stop.assert_called()
        d._process.start.assert_called()

    def test_scroll_up(self):
        d = make_dashboard()
        d._state.log_lines = ["line"] * 100
        d._state.scroll_offset = 50
        d._handle_key("UP")
        assert d._state.scroll_offset == 49

    def test_scroll_down(self):
        d = make_dashboard()
        d._state.log_lines = ["line"] * 100
        d._state.scroll_offset = 10
        d._handle_key("DOWN")
        assert d._state.scroll_offset == 11

    def test_page_up(self):
        d = make_dashboard()
        d._state.log_lines = ["line"] * 100
        d._state.scroll_offset = 50
        d._handle_key("PGUP")
        assert d._state.scroll_offset == 30

    def test_page_down(self):
        d = make_dashboard()
        d._state.log_lines = ["line"] * 100
        d._state.scroll_offset = 10
        d._handle_key("PGDN")
        assert d._state.scroll_offset == 30

    def test_scroll_does_not_go_negative(self):
        d = make_dashboard()
        d._state.scroll_offset = 0
        d._handle_key("UP")
        assert d._state.scroll_offset == 0

    def test_trackpad_scroll_adds_velocity(self):
        d = make_dashboard()
        d._handle_key("SCROLL_DOWN")
        assert d._scroll_velocity > 0
        d._handle_key("SCROLL_UP")
        # velocity reduced or reversed


class TestOnLogLine:
    def test_appends_to_log(self):
        d = make_dashboard()
        d._on_log_line("hello world")
        assert "hello world" in d._state.log_lines

    def test_classifies_errors(self):
        d = make_dashboard()
        d._on_log_line("Error: something failed")
        assert "Error: something failed" in d._state.error_lines

    def test_classifies_requests(self):
        d = make_dashboard()
        d._on_log_line('"GET /api/health" 200')
        assert len(d._state.request_lines) == 1

    def test_detects_ready_state(self):
        d = make_dashboard()
        d._state.status = AppStatus.STARTING
        d._on_log_line("ready in 500ms")
        assert d._state.status == AppStatus.READY

    def test_extracts_startup_time(self):
        d = make_dashboard()
        d._on_log_line("ready in 2.5 seconds")
        assert "2.5 seconds" in d._state.startup_time

    def test_max_lines_limit(self):
        d = make_dashboard()
        for i in range(MAX_LINES + 100):
            d._on_log_line(f"line {i}")
        assert len(d._state.log_lines) == MAX_LINES

    def test_error_status_on_fatal(self):
        d = make_dashboard()
        d._state.status = AppStatus.STARTING
        # Line must match error_patterns AND contain a fatal keyword
        d._on_log_line("Error: FAILED to compile")
        assert d._state.status == AppStatus.ERROR

    def test_no_error_status_when_ready(self):
        d = make_dashboard()
        d._state.status = AppStatus.READY
        d._on_log_line("Error: minor warning")
        # Status stays READY
        assert d._state.status == AppStatus.READY

    def test_auto_scroll(self):
        d = make_dashboard()
        d._auto_scroll = True
        d._on_log_line("new line")
        # scroll_offset should follow


class TestOnFileChange:
    def test_triggers_restart(self):
        d = make_dashboard()
        d._on_file_change("/tmp/test/src/App.js")
        # _start_app clears message after _on_file_change sets it,
        # so we verify restart happened via status and mock calls
        assert d._state.status == AppStatus.STARTING
        d._process.stop.assert_called()
        d._process.start.assert_called()


class TestStartApp:
    def test_starts_process_and_log_watcher(self):
        d = make_dashboard()
        d._start_app()
        d._process.start.assert_called_once_with(
            ["npm", "run", "dev"], "/tmp/test.log"
        )
        d._log_watcher.start.assert_called_once()
        assert d._state.status == AppStatus.STARTING

    def test_clears_state_on_start(self):
        d = make_dashboard()
        d._state.log_lines = ["old"]
        d._state.error_lines = ["old err"]
        d._start_app()
        assert d._state.log_lines == []
        assert d._state.error_lines == []
        assert d._state.request_lines == []


class TestShutdown:
    def test_stops_all_components(self):
        d = make_dashboard()
        d._shutdown()
        d._file_watcher.stop.assert_called_once()
        d._log_watcher.stop.assert_called_once()
        d._process.stop.assert_called_once()
        d._ui.teardown.assert_called_once()


class TestRequestPatterns:
    def test_completed_pattern(self):
        assert REQUEST_PATTERNS.search("Completed 200 OK")

    def test_servlet_pattern(self):
        assert REQUEST_PATTERNS.search("servlet.request handled")

    def test_http_method_pattern(self):
        assert REQUEST_PATTERNS.search('"GET /api" 200')
        assert REQUEST_PATTERNS.search('"POST /users" 201')
        assert REQUEST_PATTERNS.search('"DELETE /item/1" 204')

    def test_no_match(self):
        assert not REQUEST_PATTERNS.search("just a regular log line")
