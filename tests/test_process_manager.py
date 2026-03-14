"""Tests for the process manager."""

import os
import time
import tempfile
import pytest
from terminal_watching.infrastructure.process_manager import AppProcessRunner


class TestAppProcessRunner:
    def test_start_and_is_running(self, tmp_path):
        log_file = str(tmp_path / "test.log")
        runner = AppProcessRunner()
        runner.start(["sleep", "10"], log_file)
        assert runner.is_running() is True
        runner.stop()
        assert runner.is_running() is False

    def test_stop_idempotent(self):
        runner = AppProcessRunner()
        runner.stop()  # should not raise
        runner.stop()

    def test_not_running_initially(self):
        runner = AppProcessRunner()
        assert runner.is_running() is False

    def test_writes_stdout_to_log(self, tmp_path):
        log_file = str(tmp_path / "test.log")
        runner = AppProcessRunner()
        runner.start(["echo", "hello from process"], log_file)
        time.sleep(0.5)
        runner.stop()
        with open(log_file) as f:
            content = f.read()
        assert "hello from process" in content

    def test_start_stops_previous(self, tmp_path):
        log1 = str(tmp_path / "log1.log")
        log2 = str(tmp_path / "log2.log")
        runner = AppProcessRunner()
        runner.start(["sleep", "10"], log1)
        pid1 = runner._process.pid
        runner.start(["sleep", "10"], log2)
        pid2 = runner._process.pid
        assert pid1 != pid2
        runner.stop()

    def test_captures_stderr(self, tmp_path):
        log_file = str(tmp_path / "test.log")
        runner = AppProcessRunner()
        # Python command that writes to stderr
        runner.start(
            ["python3", "-c", "import sys; sys.stderr.write('err msg\\n')"],
            log_file,
        )
        time.sleep(0.5)
        runner.stop()
        with open(log_file) as f:
            content = f.read()
        assert "err msg" in content
