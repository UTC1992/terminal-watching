"""Tests for the CLI entry point."""

import pytest
from unittest.mock import patch, MagicMock
from terminal_watching.main import main, cmd_list, cmd_init, cmd_run


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


class TestCmdRunAutoInit:
    @patch("terminal_watching.main.config_exists", return_value=False)
    @patch("terminal_watching.main.detect_project", return_value=None)
    @patch("terminal_watching.main.cmd_init")
    def test_no_detection_launches_init(self, mock_init, mock_detect, mock_cfg, tmp_path):
        """When no tw.yml and no detection, cmd_run should launch init instead of exiting."""
        cmd_run(str(tmp_path))
        mock_init.assert_called_once_with(str(tmp_path))

    @patch("terminal_watching.main.Dashboard")
    @patch("terminal_watching.main.cmd_init")
    @patch("terminal_watching.main.detect_project", return_value=None)
    def test_after_init_starts_dashboard(self, mock_detect, mock_init, mock_dash, tmp_path):
        """After init creates tw.yml, cmd_run should start the dashboard."""
        config_path = str(tmp_path / "tw.yml")
        sample = {
            "name": "Custom",
            "command": "make run",
            "port": 3000,
            "ready_pattern": "ready",
            "error_patterns": ["Error"],
            "watch": {"dirs": ["src"], "extensions": ["py"], "exclude": []},
        }
        # Simulate init creating the config file
        from terminal_watching.infrastructure.config_loader import save_config
        mock_init.side_effect = lambda d: save_config(config_path, sample)

        mock_dash_instance = MagicMock()
        mock_dash.return_value = mock_dash_instance

        cmd_run(str(tmp_path))
        mock_init.assert_called_once()
        mock_dash_instance.run.assert_called_once()
