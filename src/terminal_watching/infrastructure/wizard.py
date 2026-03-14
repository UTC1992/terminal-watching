"""Interactive wizard for manual project configuration."""

from typing import Optional


def run_wizard(project_dir: str, prefill: Optional[dict] = None) -> dict:
    """Step-by-step wizard to configure a project."""

    if prefill is None:
        prefill = {}

    print("=" * 50)
    print("  Terminal Watching — Project Setup")
    print("=" * 50)
    print()

    # Step 1: Name
    default_name = prefill.get('name', '')
    prompt = f"Step 1/6 — Project name"
    if default_name:
        prompt += f" [{default_name}]"
    prompt += ": "
    name = input(prompt).strip() or default_name or "My Project"
    print()

    # Step 2: Command
    default_cmd = prefill.get('command', '')
    prompt = f"Step 2/6 — Start command (what you run to start the app)"
    if default_cmd:
        prompt += f"\n  [{default_cmd}]"
    prompt += ": "
    command = input(prompt).strip() or default_cmd
    if not command:
        print("  Command is required!")
        command = input("  Enter command: ").strip()
    print()

    # Step 3: Port
    default_port = prefill.get('port', '')
    prompt = f"Step 3/6 — Port (leave empty if none)"
    if default_port:
        prompt += f" [{default_port}]"
    prompt += ": "
    port_str = input(prompt).strip() or str(default_port or '')
    port = None
    if port_str:
        try:
            port = int(port_str)
        except ValueError:
            print("  Invalid port, skipping.")
    print()

    # Step 4: Ready pattern
    default_ready = prefill.get('ready_pattern', '')
    print("Step 4/6 — How do you know it's ready?")
    print("  (text that appears in logs when the app has started)")
    if default_ready:
        print(f"  [{default_ready}]")
    print()
    print("  Common patterns:")
    print('  1. "Started Application"     (Spring Boot)')
    print('  2. "ready in"                (Vite)')
    print('  3. "listening on"            (Node.js)')
    print('  4. "Running on"              (Flask)')
    print('  5. Custom — type your own')
    print()
    choice = input("  Choose (1-5) or type pattern: ").strip()

    pattern_map = {
        '1': 'Started Application',
        '2': 'ready in|Local:',
        '3': 'listening on|started',
        '4': 'Running on|Serving',
    }
    ready_pattern = pattern_map.get(choice, '')
    if not ready_pattern:
        ready_pattern = choice or default_ready
    print()

    # Step 5: Error patterns
    default_errors = prefill.get('error_patterns', ['ERROR', 'Exception', 'error'])
    print(f"Step 5/6 — Error patterns (comma separated)")
    print(f"  [{', '.join(default_errors)}]")
    errors_input = input("  : ").strip()
    if errors_input:
        error_patterns = [e.strip() for e in errors_input.split(',')]
    else:
        error_patterns = default_errors
    print()

    # Step 6: Watch
    default_watch = prefill.get('watch', {})
    default_dirs = default_watch.get('dirs', ['src'])
    default_exts = default_watch.get('extensions', [])

    print("Step 6/6 — Watch for file changes:")
    print(f"  Directories (comma separated) [{', '.join(default_dirs)}]")
    dirs_input = input("  : ").strip()
    if dirs_input:
        watch_dirs = [d.strip() for d in dirs_input.split(',')]
    else:
        watch_dirs = default_dirs

    if default_exts:
        print(f"  File extensions (comma separated) [{', '.join(default_exts)}]")
    else:
        print("  File extensions (comma separated, or Enter for all)")
    exts_input = input("  : ").strip()
    if exts_input:
        watch_exts = [e.strip().lstrip('.') for e in exts_input.split(',')]
    else:
        watch_exts = default_exts
    print()

    config = {
        'name': name,
        'command': command,
        'port': port,
        'ready_pattern': ready_pattern,
        'error_patterns': error_patterns,
        'watch': {
            'dirs': watch_dirs,
            'extensions': watch_exts,
            'exclude': default_watch.get('exclude', []),
        },
    }

    # Preview
    print("=" * 50)
    print("  Configuration preview:")
    print("=" * 50)
    print(f"  Name:          {name}")
    print(f"  Command:       {command}")
    print(f"  Port:          {port or 'N/A'}")
    print(f"  Ready pattern: {ready_pattern}")
    print(f"  Error patterns: {', '.join(error_patterns)}")
    print(f"  Watch dirs:    {', '.join(watch_dirs)}")
    print(f"  Watch exts:    {', '.join(watch_exts) or 'all'}")
    print("=" * 50)
    print()

    return config
