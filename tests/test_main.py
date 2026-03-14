"""Tests for the CLI entry point."""

import pytest
from unittest.mock import patch, MagicMock
from terminal_watching.main import main, cmd_list, cmd_init


class TestCmdList:
    def test_prints_all_types(self, capsys):
        cmd_list()
        output = capsys.readouterr().out
        assert "Java Spring Boot" in output
        assert "Next.js" in output
        assert "Go" in output
        assert "Rust" in output
        assert "Django" in output
        assert "Docker" in output
        assert "tw init" in output


class TestMain:
    @patch("sys.argv", ["tw", "list"])
    def test_list_command(self, capsys):
        main()
        output = capsys.readouterr().out
        assert "Supported project types" in output

    @patch("sys.argv", ["tw", "init"])
    @patch("terminal_watching.main.cmd_init")
    def test_init_command(self, mock_init):
        main()
        mock_init.assert_called_once()

    @patch("sys.argv", ["tw", "/nonexistent/path/xyz"])
    def test_invalid_path(self):
        with pytest.raises(SystemExit):
            main()

    @patch("sys.argv", ["tw"])
    @patch("terminal_watching.main.cmd_run")
    def test_default_runs_current_dir(self, mock_run):
        main()
        mock_run.assert_called_once()


class TestCmdInit:
    @patch("terminal_watching.main.detect_project")
    @patch("terminal_watching.main.save_config")
    @patch("builtins.input", return_value="y")
    def test_auto_detected(self, mock_input, mock_save, mock_detect, tmp_path):
        mock_detect.return_value = {
            "name": "Go",
            "command": "go run .",
            "port": 8080,
        }
        cmd_init(str(tmp_path))
        mock_save.assert_called_once()

    @patch("terminal_watching.main.detect_project", return_value=None)
    @patch("terminal_watching.main.run_wizard")
    @patch("terminal_watching.main.save_config")
    def test_no_detection_runs_wizard(self, mock_save, mock_wizard, mock_detect, tmp_path):
        mock_wizard.return_value = {"name": "Custom", "command": "make"}
        cmd_init(str(tmp_path))
        mock_wizard.assert_called_once()
        mock_save.assert_called_once()
