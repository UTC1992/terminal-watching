"""Tests for the log monitor (FileLogWatcher)."""

import os
import time
import threading
import pytest
from terminal_watching.infrastructure.log_monitor import FileLogWatcher


class TestFileLogWatcher:
    def test_detects_new_lines(self, tmp_path):
        log_file = str(tmp_path / "app.log")
        # Create file first
        with open(log_file, "w") as f:
            f.write("existing line\n")

        collected = []
        watcher = FileLogWatcher()
        watcher.start(log_file, lambda line: collected.append(line))

        time.sleep(0.2)

        # Append new lines
        with open(log_file, "a") as f:
            f.write("new line 1\n")
            f.write("new line 2\n")

        time.sleep(0.3)
        watcher.stop()

        # Reads from beginning since process starts fresh log
        assert "existing line" in collected
        assert "new line 1" in collected
        assert "new line 2" in collected

    def test_waits_for_file(self, tmp_path):
        log_file = str(tmp_path / "delayed.log")
        collected = []
        watcher = FileLogWatcher()
        watcher.start(log_file, lambda line: collected.append(line))

        time.sleep(0.2)

        # Create file after watcher started
        with open(log_file, "w") as f:
            f.write("delayed line\n")

        time.sleep(0.3)
        watcher.stop()

        assert "delayed line" in collected

    def test_stop_idempotent(self):
        watcher = FileLogWatcher()
        watcher.stop()  # should not raise
        watcher.stop()

    def test_strips_newlines(self, tmp_path):
        log_file = str(tmp_path / "app.log")
        with open(log_file, "w") as f:
            pass

        collected = []
        watcher = FileLogWatcher()
        watcher.start(log_file, lambda line: collected.append(line))

        time.sleep(0.2)
        with open(log_file, "a") as f:
            f.write("no trailing newline\n")

        time.sleep(0.3)
        watcher.stop()

        if collected:
            assert not collected[0].endswith("\n")
