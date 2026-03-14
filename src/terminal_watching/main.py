#!/usr/bin/env python3
"""Terminal Watching — Dev dashboard for any project."""

import argparse
import os
import sys

from terminal_watching.infrastructure.detector import detect_project, SUPPORTED_TYPES
from terminal_watching.infrastructure.config_loader import load_config, save_config, config_exists
from terminal_watching.infrastructure.wizard import run_wizard
from terminal_watching.infrastructure.process_manager import AppProcessRunner
from terminal_watching.infrastructure.log_monitor import FileLogWatcher
from terminal_watching.infrastructure.file_watcher import FsWatchFileWatcher
from terminal_watching.ui.terminal import CursesRenderer
from terminal_watching.application.dashboard import Dashboard


CONFIG_FILE = "tw.yml"
LOG_FILE = "/tmp/terminal-watching-dev.log"


def cmd_init(project_dir: str) -> None:
    """Generate tw.yml config for the project."""
    detection = detect_project(project_dir)

    if detection:
        print(f"\nDetected: {detection['name']}")
        print(f"Command:  {detection['command']}")
        print(f"Port:     {detection.get('port', 'N/A')}")
        print()
        answer = input("Use this config? (Y/n): ").strip().lower()
        if answer in ('', 'y', 'yes'):
            config = detection
        else:
            config = run_wizard(project_dir, prefill=detection)
    else:
        print("\nCould not auto-detect project type.")
        print("Starting manual setup...\n")
        config = run_wizard(project_dir)

    config_path = os.path.join(project_dir, CONFIG_FILE)
    save_config(config_path, config)
    print(f"\nSaved: {config_path}")
    print("Edit this file anytime to customize. Run 'tw' to start.\n")


def cmd_run(project_dir: str, config_path: str = None) -> None:
    """Run the dashboard."""
    if config_path is None:
        config_path = os.path.join(project_dir, CONFIG_FILE)

    # Try loading existing config
    if config_exists(config_path):
        config = load_config(config_path)
    else:
        # Auto-detect
        config = detect_project(project_dir)
        if config:
            print(f"Auto-detected: {config['name']}")
            print("Run 'tw init' to customize.\n")
        else:
            print("Could not detect project type.")
            print("Run 'tw init' to set up manually.\n")
            sys.exit(1)

    # Build command
    command = config['command']
    if isinstance(command, str):
        command = command.split()

    # Resolve watch dirs
    watch_dirs = []
    for d in config.get('watch', {}).get('dirs', ['src']):
        full = os.path.join(project_dir, d)
        if os.path.isdir(full):
            watch_dirs.append(full)

    extensions = config.get('watch', {}).get('extensions', [])

    dashboard = Dashboard(
        process_runner=AppProcessRunner(),
        log_watcher=FileLogWatcher(),
        file_watcher=FsWatchFileWatcher(),
        ui=CursesRenderer(),
        project_dir=project_dir,
        project_name=config.get('name', 'Project'),
        command=command,
        log_file=LOG_FILE,
        watch_dirs=watch_dirs,
        watch_extensions=extensions,
        port=config.get('port', None),
        ready_pattern=config.get('ready_pattern', ''),
        error_patterns=config.get('error_patterns', []),
    )

    try:
        dashboard.run()
    except KeyboardInterrupt:
        pass


def cmd_list() -> None:
    """List supported project types."""
    print("\nSupported project types (auto-detected):\n")
    for t in SUPPORTED_TYPES:
        print(f"  {t['name']:<30} {t['detect_by']}")
    print("\n  Any project can be configured manually with 'tw init'\n")


def main():
    parser = argparse.ArgumentParser(
        prog='tw',
        description='Terminal Watching — Dev dashboard for any project',
    )
    parser.add_argument(
        'command_or_path',
        nargs='?',
        default='.',
        help="'init', 'list', or project path (default: current dir)",
    )
    parser.add_argument(
        '--config', '-c',
        help='Path to config file (default: tw.yml in project dir)',
    )

    args = parser.parse_args()

    if args.command_or_path == 'init':
        cmd_init(os.path.abspath('.'))
    elif args.command_or_path == 'list':
        cmd_list()
    else:
        project_dir = os.path.abspath(args.command_or_path)
        if not os.path.isdir(project_dir):
            print(f"Error: '{project_dir}' is not a directory")
            sys.exit(1)
        os.chdir(project_dir)
        cmd_run(project_dir, config_path=args.config)


if __name__ == '__main__':
    main()
