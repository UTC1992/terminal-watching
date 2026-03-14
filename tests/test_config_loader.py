"""Tests for config loader (save/load round-trip)."""

import os
import pytest
from terminal_watching.infrastructure.config_loader import (
    load_config,
    save_config,
    config_exists,
)


@pytest.fixture
def config_path(tmp_path):
    return str(tmp_path / "tw.yml")


SAMPLE_CONFIG = {
    "name": "My Spring App",
    "command": "./gradlew bootRun",
    "port": 8080,
    "ready_pattern": "Started Application",
    "error_patterns": ["BUILD FAILED", "Exception", "ERROR"],
    "watch": {
        "dirs": ["src", "lib"],
        "extensions": ["java", "kt", "yml"],
        "exclude": ["build/", ".gradle/"],
    },
}


class TestConfigExists:
    def test_exists(self, config_path):
        with open(config_path, "w") as f:
            f.write("name: test\n")
        assert config_exists(config_path) is True

    def test_not_exists(self, config_path):
        assert config_exists(config_path) is False

    def test_directory_is_not_file(self, tmp_path):
        assert config_exists(str(tmp_path)) is False


class TestSaveConfig:
    def test_creates_file(self, config_path):
        save_config(config_path, SAMPLE_CONFIG)
        assert os.path.isfile(config_path)

    def test_contains_all_fields(self, config_path):
        save_config(config_path, SAMPLE_CONFIG)
        with open(config_path) as f:
            content = f.read()
        assert "My Spring App" in content
        assert "./gradlew bootRun" in content
        assert "8080" in content
        assert "Started Application" in content
        assert "BUILD FAILED" in content
        assert "java" in content
        assert "build/" in content

    def test_no_port(self, config_path):
        config = {**SAMPLE_CONFIG, "port": None}
        save_config(config_path, config)
        with open(config_path) as f:
            content = f.read()
        assert "port:" not in content

    def test_empty_extensions(self, config_path):
        config = {**SAMPLE_CONFIG, "watch": {**SAMPLE_CONFIG["watch"], "extensions": []}}
        save_config(config_path, config)
        with open(config_path) as f:
            content = f.read()
        assert "extensions:" not in content


class TestLoadConfig:
    def test_loads_all_fields(self, config_path):
        save_config(config_path, SAMPLE_CONFIG)
        result = load_config(config_path)
        assert result["name"] == "My Spring App"
        assert result["command"] == "./gradlew bootRun"
        assert result["port"] == 8080
        assert result["ready_pattern"] == "Started Application"

    def test_loads_error_patterns(self, config_path):
        save_config(config_path, SAMPLE_CONFIG)
        result = load_config(config_path)
        assert "BUILD FAILED" in result["error_patterns"]
        assert "Exception" in result["error_patterns"]
        assert "ERROR" in result["error_patterns"]

    def test_loads_watch_config(self, config_path):
        save_config(config_path, SAMPLE_CONFIG)
        result = load_config(config_path)
        assert "src" in result["watch"]["dirs"]
        assert "java" in result["watch"]["extensions"]
        assert "build/" in result["watch"]["exclude"]

    def test_handles_comments(self, config_path):
        with open(config_path, "w") as f:
            f.write('# comment\nname: "Test"\ncommand: "npm run dev"\n')
        result = load_config(config_path)
        assert result["name"] == "Test"
        assert result["command"] == "npm run dev"

    def test_handles_empty_lines(self, config_path):
        with open(config_path, "w") as f:
            f.write('name: "Test"\n\n\ncommand: "go run ."\n')
        result = load_config(config_path)
        assert result["name"] == "Test"
        assert result["command"] == "go run ."


class TestRoundTrip:
    def test_full_round_trip(self, config_path):
        save_config(config_path, SAMPLE_CONFIG)
        result = load_config(config_path)
        assert result["name"] == SAMPLE_CONFIG["name"]
        assert result["command"] == SAMPLE_CONFIG["command"]
        assert result["port"] == SAMPLE_CONFIG["port"]
        assert result["ready_pattern"] == SAMPLE_CONFIG["ready_pattern"]
        assert result["error_patterns"] == SAMPLE_CONFIG["error_patterns"]
        assert result["watch"]["dirs"] == SAMPLE_CONFIG["watch"]["dirs"]
        assert result["watch"]["extensions"] == SAMPLE_CONFIG["watch"]["extensions"]
        assert result["watch"]["exclude"] == SAMPLE_CONFIG["watch"]["exclude"]

    def test_minimal_config(self, config_path):
        minimal = {
            "name": "Minimal",
            "command": "make run",
            "port": None,
            "ready_pattern": "ready",
            "error_patterns": [],
            "watch": {"dirs": ["src"], "extensions": [], "exclude": []},
        }
        save_config(config_path, minimal)
        result = load_config(config_path)
        assert result["name"] == "Minimal"
        assert result["command"] == "make run"
        assert result["port"] is None

    def test_status_patterns_round_trip(self, config_path):
        config = {
            **SAMPLE_CONFIG,
            "status_patterns": [
                {"pattern": "Task.*:compile", "status": "COMPILING"},
                {"pattern": "Starting \\w+.*on", "status": "BOOTING"},
            ],
        }
        save_config(config_path, config)
        result = load_config(config_path)
        assert len(result["status_patterns"]) == 2
        assert result["status_patterns"][0]["pattern"] == "Task.*:compile"
        assert result["status_patterns"][0]["status"] == "COMPILING"
        assert result["status_patterns"][1]["status"] == "BOOTING"

    def test_no_status_patterns(self, config_path):
        save_config(config_path, SAMPLE_CONFIG)
        result = load_config(config_path)
        assert result["status_patterns"] == []
