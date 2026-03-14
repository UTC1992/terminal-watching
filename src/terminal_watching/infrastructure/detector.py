"""Auto-detect project type by scanning files in the directory."""

import os
import json
from typing import Optional


SUPPORTED_TYPES = [
    {
        "name": "Java Spring Boot (Gradle)",
        "detect_by": "build.gradle + src/main/java",
        "files": ["build.gradle"],
        "command": "./gradlew bootRun",
        "ready_pattern": "Started Application",
        "error_patterns": ["BUILD FAILED", "Exception", "ERROR"],
        "port": 8080,
        "watch": {
            "dirs": ["src"],
            "extensions": ["java", "kt", "graphqls", "yml", "yaml", "properties"],
            "exclude": ["build/", ".gradle/"],
        },
    },
    {
        "name": "Java Spring Boot (Maven)",
        "detect_by": "pom.xml + src/main/java",
        "files": ["pom.xml"],
        "command": "./mvnw spring-boot:run",
        "ready_pattern": "Started Application",
        "error_patterns": ["BUILD FAILURE", "Exception", "ERROR"],
        "port": 8080,
        "watch": {
            "dirs": ["src"],
            "extensions": ["java", "kt", "xml", "yml", "yaml", "properties"],
            "exclude": ["target/"],
        },
    },
    {
        "name": "Next.js",
        "detect_by": "package.json + next.config.*",
        "files": ["package.json", "next.config"],
        "command": "npm run dev",
        "ready_pattern": "ready on|Ready in|started server on",
        "error_patterns": ["Error", "error", "EADDRINUSE"],
        "port": 3000,
        "watch": {
            "dirs": ["src", "app", "pages", "components"],
            "extensions": ["ts", "tsx", "js", "jsx", "css", "scss"],
            "exclude": ["node_modules/", ".next/"],
        },
    },
    {
        "name": "Vite (React/Vue/Svelte)",
        "detect_by": "package.json + vite.config.*",
        "files": ["package.json", "vite.config"],
        "command": "npm run dev",
        "ready_pattern": "ready in|Local:|VITE",
        "error_patterns": ["Error", "error", "EADDRINUSE"],
        "port": 5173,
        "watch": {
            "dirs": ["src"],
            "extensions": ["ts", "tsx", "js", "jsx", "vue", "svelte", "css", "scss"],
            "exclude": ["node_modules/", "dist/"],
        },
    },
    {
        "name": "Node.js (Express/Generic)",
        "detect_by": "package.json",
        "files": ["package.json"],
        "command": "npm run dev",
        "ready_pattern": "listening on|started|ready|Server running",
        "error_patterns": ["Error", "error", "EADDRINUSE"],
        "port": 3000,
        "watch": {
            "dirs": ["src", "lib", "routes"],
            "extensions": ["ts", "js", "json"],
            "exclude": ["node_modules/", "dist/"],
        },
    },
    {
        "name": "Go",
        "detect_by": "go.mod",
        "files": ["go.mod"],
        "command": "go run .",
        "ready_pattern": "listening|started|serving",
        "error_patterns": ["panic", "fatal", "error"],
        "port": 8080,
        "watch": {
            "dirs": ["."],
            "extensions": ["go", "html", "yml", "yaml"],
            "exclude": ["vendor/"],
        },
    },
    {
        "name": "Rust (Cargo)",
        "detect_by": "Cargo.toml",
        "files": ["Cargo.toml"],
        "command": "cargo run",
        "ready_pattern": "listening|started|serving",
        "error_patterns": ["error\\[", "panic", "fatal"],
        "port": 8080,
        "watch": {
            "dirs": ["src"],
            "extensions": ["rs", "toml", "html"],
            "exclude": ["target/"],
        },
    },
    {
        "name": "Python Django",
        "detect_by": "manage.py",
        "files": ["manage.py"],
        "command": "python manage.py runserver",
        "ready_pattern": "Starting development server|Watching for file changes",
        "error_patterns": ["Error", "Exception", "Traceback"],
        "port": 8000,
        "watch": {
            "dirs": ["."],
            "extensions": ["py", "html", "css", "js", "yml"],
            "exclude": ["__pycache__/", ".venv/", "venv/"],
        },
    },
    {
        "name": "Python Flask",
        "detect_by": "app.py or wsgi.py + requirements.txt",
        "files": ["requirements.txt"],
        "command": "flask run",
        "ready_pattern": "Running on|Serving Flask app",
        "error_patterns": ["Error", "Exception", "Traceback"],
        "port": 5000,
        "watch": {
            "dirs": ["."],
            "extensions": ["py", "html", "css", "js"],
            "exclude": ["__pycache__/", ".venv/", "venv/"],
        },
    },
    {
        "name": "Docker Compose",
        "detect_by": "docker-compose.yml or compose.yml",
        "files": ["docker-compose.yml", "compose.yml"],
        "command": "docker compose up",
        "ready_pattern": "ready|started|listening|Running",
        "error_patterns": ["error", "Error", "fatal"],
        "port": None,
        "watch": {
            "dirs": ["src", "."],
            "extensions": [],
            "exclude": ["node_modules/", ".git/"],
        },
    },
]


def _file_exists(directory: str, name: str) -> bool:
    """Check if a file or file pattern exists in directory."""
    for f in os.listdir(directory):
        if f == name or f.startswith(name):
            return True
    return False


def _detect_gradle_modules(directory: str) -> list[str]:
    """Find all src/ dirs in a Gradle multi-module project."""
    dirs = []
    for item in os.listdir(directory):
        src_path = os.path.join(directory, item, 'src')
        if os.path.isdir(src_path):
            dirs.append(os.path.join(item, 'src'))
    # Also check root src
    if os.path.isdir(os.path.join(directory, 'src')):
        dirs.append('src')
    return dirs if dirs else ['src']


def _detect_node_command(directory: str) -> str:
    """Read package.json to find the right dev command."""
    pkg_path = os.path.join(directory, 'package.json')
    try:
        with open(pkg_path) as f:
            pkg = json.load(f)
        scripts = pkg.get('scripts', {})
        if 'dev' in scripts:
            return 'npm run dev'
        if 'start' in scripts:
            return 'npm start'
        if 'serve' in scripts:
            return 'npm run serve'
        return 'npm run dev'
    except (FileNotFoundError, json.JSONDecodeError):
        return 'npm run dev'


def detect_project(directory: str) -> Optional[dict]:
    """Detect project type and return config dict, or None."""
    try:
        files = os.listdir(directory)
    except OSError:
        return None

    # Check each type (order matters — more specific first)
    for project_type in SUPPORTED_TYPES:
        required_files = project_type['files']
        if all(_file_exists(directory, f) for f in required_files):
            config = {
                'name': project_type['name'],
                'command': project_type['command'],
                'ready_pattern': project_type['ready_pattern'],
                'error_patterns': project_type['error_patterns'],
                'port': project_type['port'],
                'watch': dict(project_type['watch']),
            }

            # Specific enhancements
            if 'build.gradle' in required_files:
                modules = _detect_gradle_modules(directory)
                config['watch']['dirs'] = modules

            if 'package.json' in required_files:
                config['command'] = _detect_node_command(directory)

            # Filter watch dirs to only existing ones
            config['watch']['dirs'] = [
                d for d in config['watch']['dirs']
                if os.path.isdir(os.path.join(directory, d))
            ] or ['src']

            return config

    return None
