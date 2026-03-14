"""Load and save tw.yml config files."""

import os
import re
from typing import Optional


def config_exists(path: str) -> bool:
    return os.path.isfile(path)


def save_config(path: str, config: dict) -> None:
    """Save config as YAML (simple writer, no pyyaml dependency)."""
    lines = []
    lines.append(f"name: \"{config.get('name', 'My Project')}\"")
    lines.append(f"command: \"{config.get('command', '')}\"")

    port = config.get('port')
    if port:
        lines.append(f"port: {port}")

    lines.append(f"ready_pattern: \"{config.get('ready_pattern', '')}\"")

    error_patterns = config.get('error_patterns', [])
    if error_patterns:
        lines.append("error_patterns:")
        for p in error_patterns:
            lines.append(f"  - \"{p}\"")

    watch = config.get('watch', {})
    lines.append("watch:")

    dirs = watch.get('dirs', ['src'])
    lines.append("  dirs:")
    for d in dirs:
        lines.append(f"    - \"{d}\"")

    exts = watch.get('extensions', [])
    if exts:
        lines.append("  extensions:")
        for e in exts:
            lines.append(f"    - \"{e}\"")

    exclude = watch.get('exclude', [])
    if exclude:
        lines.append("  exclude:")
        for e in exclude:
            lines.append(f"    - \"{e}\"")

    with open(path, 'w') as f:
        f.write('\n'.join(lines) + '\n')


def load_config(path: str) -> dict:
    """Load config from YAML (simple parser, no pyyaml dependency)."""
    config = {
        'name': '',
        'command': '',
        'port': None,
        'ready_pattern': '',
        'error_patterns': [],
        'watch': {
            'dirs': [],
            'extensions': [],
            'exclude': [],
        },
    }

    with open(path) as f:
        content = f.read()

    # Simple YAML-like parser for our specific format
    current_list = None
    current_section = None

    for line in content.split('\n'):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue

        # Top-level key: value
        match = re.match(r'^(\w+):\s*"?([^"]*)"?\s*$', stripped)
        if match and not line.startswith(' '):
            key, value = match.group(1), match.group(2).strip()
            current_list = None
            current_section = None

            if key == 'name':
                config['name'] = value
            elif key == 'command':
                config['command'] = value
            elif key == 'port':
                try:
                    config['port'] = int(value)
                except ValueError:
                    pass
            elif key == 'ready_pattern':
                config['ready_pattern'] = value
            elif key == 'error_patterns':
                current_list = config['error_patterns']
            elif key == 'watch':
                current_section = 'watch'
            continue

        # Section keys (watch.dirs, watch.extensions, etc.)
        if current_section == 'watch':
            sub_match = re.match(r'^\s{2}(\w+):', stripped)
            if sub_match:
                sub_key = sub_match.group(1)
                if sub_key in config['watch']:
                    current_list = config['watch'][sub_key]
                continue

        # List items
        if current_list is not None:
            item_match = re.match(r'^\s*-\s*"?([^"]*)"?\s*$', stripped)
            if item_match:
                current_list.append(item_match.group(1).strip())

    return config
