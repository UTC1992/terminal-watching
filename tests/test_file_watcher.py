"""Tests for the file watcher."""

import shutil
import pytest
from terminal_watching.infrastructure.file_watcher import FsWatchFileWatcher


class TestFsWatchFileWatcher:
    def test_is_available(self):
        watcher = FsWatchFileWatcher()
        # Should match whether fswatch is installed or not
        expected = shutil.which("fswatch") is not None
        assert watcher.is_available() == expected

    def test_stop_idempotent(self):
        watcher = FsWatchFileWatcher()
        watcher.stop()  # should not raise
        watcher.stop()

    def test_start_without_fswatch(self):
        watcher = FsWatchFileWatcher()
        if not watcher.is_available():
            # Should silently do nothing
            watcher.start(["/tmp"], ["py"], lambda f: None)
            assert watcher._process is None
