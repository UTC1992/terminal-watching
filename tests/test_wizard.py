"""Tests for the interactive wizard (with mocked input)."""

import pytest
from unittest.mock import patch
from terminal_watching.infrastructure.wizard import run_wizard


class TestWizard:
    @patch("builtins.input", side_effect=[
        "MyApp",        # name
        "npm start",    # command
        "3000",         # port
        "3",            # ready pattern choice (listening on)
        "",             # error patterns (use default)
        "",             # watch dirs (use default)
        "",             # watch extensions (use default)
    ])
    def test_basic_flow(self, mock_input, tmp_path):
        config = run_wizard(str(tmp_path))
        assert config["name"] == "MyApp"
        assert config["command"] == "npm start"
        assert config["port"] == 3000
        assert "listening" in config["ready_pattern"]

    @patch("builtins.input", side_effect=[
        "",                # name (use default)
        "go run .",        # command
        "",                # port (none)
        "custom pattern",  # ready pattern (custom)
        "panic,fatal",     # error patterns
        "src,cmd",         # watch dirs
        "go,html",         # watch extensions
    ])
    def test_custom_values(self, mock_input, tmp_path):
        config = run_wizard(str(tmp_path))
        assert config["name"] == "My Project"
        assert config["command"] == "go run ."
        assert config["port"] is None
        assert config["ready_pattern"] == "custom pattern"
        assert config["error_patterns"] == ["panic", "fatal"]
        assert config["watch"]["dirs"] == ["src", "cmd"]
        assert config["watch"]["extensions"] == ["go", "html"]

    @patch("builtins.input", side_effect=[
        "",             # name (use prefill)
        "",             # command (use prefill)
        "",             # port (use prefill)
        "1",            # ready pattern (Spring Boot)
        "",             # error patterns (use prefill)
        "",             # watch dirs (use prefill)
        "",             # watch extensions (use prefill)
    ])
    def test_prefill(self, mock_input, tmp_path):
        prefill = {
            "name": "Spring App",
            "command": "./gradlew bootRun",
            "port": 8080,
            "error_patterns": ["BUILD FAILED"],
            "watch": {
                "dirs": ["src"],
                "extensions": ["java"],
                "exclude": ["build/"],
            },
        }
        config = run_wizard(str(tmp_path), prefill=prefill)
        assert config["name"] == "Spring App"
        assert config["command"] == "./gradlew bootRun"
        assert config["port"] == 8080
        assert config["error_patterns"] == ["BUILD FAILED"]
        assert config["watch"]["exclude"] == ["build/"]

    @patch("builtins.input", side_effect=[
        "",             # name
        "",             # command (empty first time)
        "make run",     # command (retry)
        "bad",          # port (invalid)
        "2",            # ready pattern
        "",             # errors
        "",             # dirs
        ".go,.rs",      # extensions with dots
    ])
    def test_edge_cases(self, mock_input, tmp_path):
        config = run_wizard(str(tmp_path))
        assert config["command"] == "make run"
        assert config["port"] is None  # "bad" is invalid
        assert config["watch"]["extensions"] == ["go", "rs"]  # dots stripped

    @patch("builtins.input", side_effect=[
        "Test",
        "npm dev",
        "4000",
        "4",            # Flask pattern
        "",
        "",
        "",
    ])
    def test_pattern_choices(self, mock_input, tmp_path):
        config = run_wizard(str(tmp_path))
        assert "Running on" in config["ready_pattern"] or "Serving" in config["ready_pattern"]
