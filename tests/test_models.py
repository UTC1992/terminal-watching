"""Tests for domain models."""

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
