"""Tests for domain models."""

import time
import pytest
from terminal_watching.domain.models import AppState, AppStatus, Tab


class TestAppStatus:
    def test_values(self):
        assert AppStatus.STARTING.value == "STARTING..."
        assert AppStatus.READY.value == "READY"
        assert AppStatus.ERROR.value == "ERROR"
        assert AppStatus.STOPPED.value == "STOPPED"
        assert AppStatus.RESTARTING.value == "RESTARTING..."

    def test_all_statuses_exist(self):
        expected = {"STARTING", "COMPILING", "BOOTING", "READY",
                    "RESTARTING", "STOPPED", "ERROR"}
        assert {s.name for s in AppStatus} == expected


class TestTab:
    def test_values(self):
        assert Tab.LOGS.value == "logs"
        assert Tab.ERRORS.value == "errors"
        assert Tab.REQUESTS.value == "requests"


class TestAppStateDefaults:
    def test_default_state(self):
        state = AppState()
        assert state.status == AppStatus.STOPPED
        assert state.message == ""
        assert state.active_tab == Tab.LOGS
        assert state.project_name == "Project"
        assert state.port is None
        assert state.log_lines == []
        assert state.error_lines == []
        assert state.request_lines == []
        assert state.scroll_offset == 0
        assert state.wrap_lines is True

    def test_independent_list_instances(self):
        """Each AppState must have its own lists."""
        a = AppState()
        b = AppState()
        a.log_lines.append("x")
        assert b.log_lines == []


class TestActiveLines:
    def test_logs_tab(self):
        state = AppState(
            active_tab=Tab.LOGS,
            log_lines=["a", "b"],
            error_lines=["e"],
            request_lines=["r"],
        )
        assert state.active_lines == ["a", "b"]

    def test_errors_tab(self):
        state = AppState(active_tab=Tab.ERRORS, error_lines=["e1", "e2"])
        assert state.active_lines == ["e1", "e2"]

    def test_requests_tab(self):
        state = AppState(active_tab=Tab.REQUESTS, request_lines=["r1"])
        assert state.active_lines == ["r1"]


class TestGetDisplayLines:
    def test_short_lines_unchanged(self):
        state = AppState(log_lines=["hello", "world"])
        lines = state.get_display_lines(80)
        assert lines == ["hello", "world"]

    def test_wrapping_long_line(self):
        state = AppState(log_lines=["A" * 100])
        lines = state.get_display_lines(50)
        # width = 49 (cols - 1)
        assert lines[0] == "A" * 49
        # Continuation lines have 2-char indent, so cont_width = 47
        assert lines[1].startswith("  ")
        # All chars accounted for
        total = len(lines[0]) + sum(len(l) - 2 for l in lines[1:])
        assert total == 100

    def test_no_wrap_mode(self):
        state = AppState(log_lines=["A" * 100], wrap_lines=False)
        lines = state.get_display_lines(50)
        assert lines == ["A" * 100]

    def test_tab_replacement(self):
        state = AppState(log_lines=["\thello"])
        lines = state.get_display_lines(80)
        assert lines == ["  hello"]

    def test_small_cols_returns_raw(self):
        state = AppState(log_lines=["test"])
        lines = state.get_display_lines(3)
        assert lines == ["test"]

    def test_empty_lines(self):
        state = AppState(log_lines=[])
        assert state.get_display_lines(80) == []


class TestMaxScroll:
    def test_no_scroll_needed(self):
        state = AppState(log_lines=["a", "b", "c"])
        assert state.max_scroll(10) == 0

    def test_scroll_needed(self):
        state = AppState(log_lines=["line"] * 50)
        assert state.max_scroll(10) == 40

    def test_with_wrap(self):
        state = AppState(log_lines=["A" * 100], wrap_lines=True)
        # With cols=50, one 100-char line wraps to multiple display lines
        max_s = state.max_scroll(10, cols=50)
        display = len(state.get_display_lines(50))
        assert max_s == max(0, display - 10)

    def test_zero_lines(self):
        state = AppState()
        assert state.max_scroll(10) == 0


class TestUptime:
    def test_default_start_time_is_none(self):
        state = AppState()
        assert state.started_at is None

    def test_uptime_returns_zero_when_not_started(self):
        state = AppState()
        assert state.uptime_seconds == 0

    def test_uptime_counts_seconds(self):
        state = AppState(started_at=time.monotonic() - 65)
        assert state.uptime_seconds >= 65

    def test_uptime_display_format(self):
        state = AppState(started_at=time.monotonic() - 125)
        display = state.uptime_display
        # 125 seconds = 2m 05s
        assert display == "02:05" or display == "02:06"  # allow 1s tolerance

    def test_uptime_display_hours(self):
        state = AppState(started_at=time.monotonic() - 3661)
        display = state.uptime_display
        # 3661 seconds = 1h 01m 01s
        assert display.startswith("1:01:")

    def test_uptime_display_when_stopped(self):
        state = AppState()
        assert state.uptime_display == "00:00"


class TestSpinner:
    def test_spinner_when_starting(self):
        state = AppState(status=AppStatus.STARTING)
        spinner = state.spinner_frame
        assert spinner in AppState.SPINNER_FRAMES

    def test_spinner_when_compiling(self):
        state = AppState(status=AppStatus.COMPILING)
        assert state.spinner_frame in AppState.SPINNER_FRAMES

    def test_spinner_when_ready(self):
        state = AppState(status=AppStatus.READY)
        assert state.spinner_frame == ""

    def test_spinner_when_stopped(self):
        state = AppState(status=AppStatus.STOPPED)
        assert state.spinner_frame == ""

    def test_spinner_when_error(self):
        state = AppState(status=AppStatus.ERROR)
        assert state.spinner_frame == ""

    def test_spinner_changes_over_time(self):
        state = AppState(status=AppStatus.STARTING)
        frames = set()
        for _ in range(20):
            frames.add(state.spinner_frame)
            time.sleep(0.05)
        assert len(frames) > 1

    def test_is_loading_property(self):
        assert AppState(status=AppStatus.STARTING).is_loading is True
        assert AppState(status=AppStatus.COMPILING).is_loading is True
        assert AppState(status=AppStatus.BOOTING).is_loading is True
        assert AppState(status=AppStatus.RESTARTING).is_loading is True
        assert AppState(status=AppStatus.READY).is_loading is False
        assert AppState(status=AppStatus.STOPPED).is_loading is False
        assert AppState(status=AppStatus.ERROR).is_loading is False
