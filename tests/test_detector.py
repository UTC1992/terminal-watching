"""Tests for project type detector."""

import json
import os
import pytest
from terminal_watching.infrastructure.detector import (
    detect_project,
    _file_exists,
    _detect_gradle_modules,
    _detect_node_command,
    SUPPORTED_TYPES,
)


@pytest.fixture
def project_dir(tmp_path):
    return tmp_path


class TestFileExists:
    def test_exact_match(self, project_dir):
        (project_dir / "build.gradle").touch()
        assert _file_exists(str(project_dir), "build.gradle") is True

    def test_prefix_match(self, project_dir):
        (project_dir / "next.config.js").touch()
        assert _file_exists(str(project_dir), "next.config") is True

    def test_no_match(self, project_dir):
        assert _file_exists(str(project_dir), "missing.file") is False


class TestDetectGradleModules:
    def test_multi_module(self, project_dir):
        (project_dir / "moduleA" / "src").mkdir(parents=True)
        (project_dir / "moduleB" / "src").mkdir(parents=True)
        (project_dir / "src").mkdir()
        dirs = _detect_gradle_modules(str(project_dir))
        assert "src" in dirs
        assert "moduleA/src" in dirs
        assert "moduleB/src" in dirs

    def test_single_module(self, project_dir):
        (project_dir / "src").mkdir()
        dirs = _detect_gradle_modules(str(project_dir))
        assert dirs == ["src"]

    def test_no_src_defaults(self, project_dir):
        dirs = _detect_gradle_modules(str(project_dir))
        assert dirs == ["src"]


class TestDetectNodeCommand:
    def test_dev_script(self, project_dir):
        pkg = {"scripts": {"dev": "vite", "start": "node ."}}
        (project_dir / "package.json").write_text(json.dumps(pkg))
        assert _detect_node_command(str(project_dir)) == "npm run dev"

    def test_start_script(self, project_dir):
        pkg = {"scripts": {"start": "node ."}}
        (project_dir / "package.json").write_text(json.dumps(pkg))
        assert _detect_node_command(str(project_dir)) == "npm start"

    def test_serve_script(self, project_dir):
        pkg = {"scripts": {"serve": "http-server"}}
        (project_dir / "package.json").write_text(json.dumps(pkg))
        assert _detect_node_command(str(project_dir)) == "npm run serve"

    def test_no_scripts(self, project_dir):
        (project_dir / "package.json").write_text("{}")
        assert _detect_node_command(str(project_dir)) == "npm run dev"

    def test_missing_file(self, project_dir):
        assert _detect_node_command(str(project_dir)) == "npm run dev"

    def test_invalid_json(self, project_dir):
        (project_dir / "package.json").write_text("not json")
        assert _detect_node_command(str(project_dir)) == "npm run dev"


class TestDetectProject:
    def test_spring_boot_gradle(self, project_dir):
        (project_dir / "build.gradle").touch()
        (project_dir / "src" / "main" / "java").mkdir(parents=True)
        result = detect_project(str(project_dir))
        assert result is not None
        assert "Spring Boot" in result["name"] or "Gradle" in result["name"]
        assert result["port"] == 8080

    def test_spring_boot_maven(self, project_dir):
        (project_dir / "pom.xml").touch()
        (project_dir / "src" / "main" / "java").mkdir(parents=True)
        result = detect_project(str(project_dir))
        assert result is not None
        assert "Maven" in result["name"]

    def test_nextjs(self, project_dir):
        pkg = {"scripts": {"dev": "next dev"}}
        (project_dir / "package.json").write_text(json.dumps(pkg))
        (project_dir / "next.config.js").touch()
        result = detect_project(str(project_dir))
        assert result is not None
        assert "Next" in result["name"]
        assert result["port"] == 3000

    def test_vite(self, project_dir):
        pkg = {"scripts": {"dev": "vite"}}
        (project_dir / "package.json").write_text(json.dumps(pkg))
        (project_dir / "vite.config.ts").touch()
        (project_dir / "src").mkdir()
        result = detect_project(str(project_dir))
        assert result is not None
        assert "Vite" in result["name"]
        assert result["port"] == 5173

    def test_node_express(self, project_dir):
        pkg = {"scripts": {"dev": "nodemon"}}
        (project_dir / "package.json").write_text(json.dumps(pkg))
        result = detect_project(str(project_dir))
        assert result is not None
        assert "Node" in result["name"]

    def test_go(self, project_dir):
        (project_dir / "go.mod").touch()
        result = detect_project(str(project_dir))
        assert result is not None
        assert result["name"] == "Go"

    def test_rust(self, project_dir):
        (project_dir / "Cargo.toml").touch()
        (project_dir / "src").mkdir()
        result = detect_project(str(project_dir))
        assert result is not None
        assert "Rust" in result["name"]

    def test_django(self, project_dir):
        (project_dir / "manage.py").touch()
        result = detect_project(str(project_dir))
        assert result is not None
        assert "Django" in result["name"]
        assert result["port"] == 8000

    def test_flask(self, project_dir):
        (project_dir / "requirements.txt").touch()
        result = detect_project(str(project_dir))
        assert result is not None
        assert "Flask" in result["name"]
        assert result["port"] == 5000

    def test_docker_compose(self, project_dir):
        (project_dir / "docker-compose.yml").touch()
        result = detect_project(str(project_dir))
        assert result is not None
        assert "Docker" in result["name"]
        assert result["port"] is None

    def test_unknown_project(self, project_dir):
        (project_dir / "random.txt").touch()
        result = detect_project(str(project_dir))
        assert result is None

    def test_empty_directory(self, project_dir):
        result = detect_project(str(project_dir))
        assert result is None

    def test_invalid_directory(self):
        result = detect_project("/nonexistent/path/xyz")
        assert result is None

    def test_result_has_watch_config(self, project_dir):
        (project_dir / "go.mod").touch()
        result = detect_project(str(project_dir))
        assert "watch" in result
        assert "dirs" in result["watch"]
        assert "extensions" in result["watch"]

    def test_priority_nextjs_over_node(self, project_dir):
        """Next.js should be detected before generic Node.js."""
        pkg = {"scripts": {"dev": "next dev"}}
        (project_dir / "package.json").write_text(json.dumps(pkg))
        (project_dir / "next.config.js").touch()
        result = detect_project(str(project_dir))
        assert "Next" in result["name"]

    def test_watch_dirs_filtered_to_existing(self, project_dir):
        (project_dir / "go.mod").touch()
        # Go wants to watch "." which exists
        result = detect_project(str(project_dir))
        for d in result["watch"]["dirs"]:
            assert os.path.isdir(os.path.join(str(project_dir), d))


class TestSupportedTypes:
    def test_all_have_required_keys(self):
        required = {"name", "detect_by", "files", "command",
                    "ready_pattern", "error_patterns", "port", "watch"}
        for t in SUPPORTED_TYPES:
            missing = required - set(t.keys())
            assert not missing, f"{t['name']} missing keys: {missing}"

    def test_watch_has_required_keys(self):
        for t in SUPPORTED_TYPES:
            assert "dirs" in t["watch"]
            assert "extensions" in t["watch"]
            assert "exclude" in t["watch"]

    def test_at_least_10_types(self):
        assert len(SUPPORTED_TYPES) >= 10
