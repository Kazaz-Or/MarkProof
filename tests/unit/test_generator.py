"""Tests for markproof.config and markproof.generator."""

from pathlib import Path

import pytest

# Import executor and parser at module level so Pydantic generates their schemas
# with the real pathlib.Path — before any pyfakefs fixture patches it.
from markproof import executor as _executor_mod  # noqa: F401
from markproof import parser as _parser_mod  # noqa: F401
from markproof.config import (
    ALL_SECTIONS,
    SECTION_ARCHITECTURE,
    SECTION_INSTALLATION,
    SECTION_TECH_STACK,
    MarkProofConfig,
    ReadmeConfig,
    SectionsConfig,
    load_config,
)
from markproof.generator import (
    ReadmeGenerator,
    _begin_marker,
    _build_tree,
    _end_marker,
    _parse_pyproject,
    _render_architecture,
    _render_installation,
    _render_tech_stack,
    _section_present,
    _should_ignore,
    _update_section,
    _wrap_section,
    check_readme,
)

# ---------------------------------------------------------------------------
# Shared fake-filesystem fixtures
# ---------------------------------------------------------------------------

_MINIMAL_PYPROJECT = """\
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "mylib"
version = "1.0.0"
description = "A sample library."
requires-python = ">=3.12"
dependencies = [
    "httpx>=0.27",
    "typer>=0.12",
]

[dependency-groups]
dev = ["pytest>=8.0", "ruff>=0.4"]

[project.scripts]
mylib = "mylib.cli:app"
"""


def _make_project(fs, *, with_config: bool = False, config_content: str = "") -> Path:
    """Create a minimal fake project layout under /project."""
    root = Path("/project")
    fs.create_dir(root)
    fs.create_file(root / "pyproject.toml", contents=_MINIMAL_PYPROJECT)
    fs.create_dir(root / "src" / "mylib")
    fs.create_file(root / "src" / "mylib" / "__init__.py", contents="")
    fs.create_file(root / "src" / "mylib" / "cli.py", contents="")
    fs.create_dir(root / "tests")
    fs.create_file(root / "tests" / "test_cli.py", contents="")
    if with_config:
        fs.create_file(root / "markproof.toml", contents=config_content)
    return root


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------


class TestLoadConfig:
    def test_defaults_when_no_file(self, fs) -> None:  # noqa: ANN001
        fs.create_dir("/project")
        cfg = load_config(Path("/project"))
        assert cfg.readme.path == "README.md"
        assert set(cfg.sections.managed) == set(ALL_SECTIONS)

    def test_reads_readme_path(self, fs) -> None:  # noqa: ANN001
        fs.create_dir("/project")
        fs.create_file(
            "/project/markproof.toml",
            contents='[readme]\npath = "DOCS.md"\n',
        )
        cfg = load_config(Path("/project"))
        assert cfg.readme.path == "DOCS.md"

    def test_reads_managed_sections(self, fs) -> None:  # noqa: ANN001
        fs.create_dir("/project")
        fs.create_file(
            "/project/markproof.toml",
            contents='[sections]\nmanaged = ["installation"]\n',
        )
        cfg = load_config(Path("/project"))
        assert cfg.sections.managed == ["installation"]

    def test_partial_config_keeps_other_defaults(self, fs) -> None:  # noqa: ANN001
        fs.create_dir("/project")
        fs.create_file(
            "/project/markproof.toml",
            contents='[readme]\npath = "DOCS.md"\n',
        )
        cfg = load_config(Path("/project"))
        assert set(cfg.sections.managed) == set(ALL_SECTIONS)

    def test_empty_toml_returns_defaults(self, fs) -> None:  # noqa: ANN001
        fs.create_dir("/project")
        fs.create_file("/project/markproof.toml", contents="")
        cfg = load_config(Path("/project"))
        assert cfg.readme.path == "README.md"


# ---------------------------------------------------------------------------
# MarkProofConfig model
# ---------------------------------------------------------------------------


class TestMarkProofConfig:
    def test_default_construction(self) -> None:
        cfg = MarkProofConfig()
        assert isinstance(cfg.readme, ReadmeConfig)
        assert isinstance(cfg.sections, SectionsConfig)

    def test_all_sections_constant(self) -> None:
        assert SECTION_INSTALLATION in ALL_SECTIONS
        assert SECTION_ARCHITECTURE in ALL_SECTIONS
        assert SECTION_TECH_STACK in ALL_SECTIONS


# ---------------------------------------------------------------------------
# _should_ignore
# ---------------------------------------------------------------------------


class TestShouldIgnore:
    @pytest.mark.parametrize(
        "name",
        [".git", ".venv", "venv", "__pycache__", ".pytest_cache", "dist", "build"],
    )
    def test_ignores_known_dirs(self, name: str, fs) -> None:  # noqa: ANN001
        p = Path(f"/project/{name}")
        fs.create_dir(p)
        assert _should_ignore(p) is True

    def test_ignores_pyc(self, fs) -> None:  # noqa: ANN001
        p = Path("/project/foo.pyc")
        fs.create_file(p, contents="")
        assert _should_ignore(p) is True

    def test_ignores_egg_info(self, fs) -> None:  # noqa: ANN001
        p = Path("/project/mylib.egg-info")
        fs.create_dir(p)
        assert _should_ignore(p) is True

    def test_does_not_ignore_normal_files(self, fs) -> None:  # noqa: ANN001
        p = Path("/project/main.py")
        fs.create_file(p, contents="")
        assert _should_ignore(p) is False

    def test_keeps_gitignore(self, fs) -> None:  # noqa: ANN001
        p = Path("/project/.gitignore")
        fs.create_file(p, contents="")
        assert _should_ignore(p) is False

    def test_keeps_python_version(self, fs) -> None:  # noqa: ANN001
        p = Path("/project/.python-version")
        fs.create_file(p, contents="")
        assert _should_ignore(p) is False


# ---------------------------------------------------------------------------
# _build_tree
# ---------------------------------------------------------------------------


class TestBuildTree:
    def test_empty_directory(self, fs) -> None:  # noqa: ANN001
        fs.create_dir("/project")
        lines = _build_tree(Path("/project"))
        assert lines == []

    def test_single_file(self, fs) -> None:  # noqa: ANN001
        fs.create_dir("/project")
        fs.create_file("/project/main.py", contents="")
        lines = _build_tree(Path("/project"))
        assert any("main.py" in line for line in lines)

    def test_dirs_before_files(self, fs) -> None:  # noqa: ANN001
        fs.create_dir("/project/src")
        fs.create_file("/project/pyproject.toml", contents="")
        lines = _build_tree(Path("/project"))
        names = [line.split("── ")[1].rstrip("/") for line in lines]
        src_idx = names.index("src")
        toml_idx = names.index("pyproject.toml")
        assert src_idx < toml_idx

    def test_git_dir_excluded(self, fs) -> None:  # noqa: ANN001
        fs.create_dir("/project/.git")
        fs.create_file("/project/README.md", contents="")
        lines = _build_tree(Path("/project"))
        assert not any(".git" in line for line in lines)

    def test_venv_excluded(self, fs) -> None:  # noqa: ANN001
        fs.create_dir("/project/.venv")
        fs.create_file("/project/README.md", contents="")
        lines = _build_tree(Path("/project"))
        assert not any(".venv" in line for line in lines)

    def test_nested_structure(self, fs) -> None:  # noqa: ANN001
        fs.create_dir("/project/src/mylib")
        fs.create_file("/project/src/mylib/__init__.py", contents="")
        lines = _build_tree(Path("/project"))
        flat = "\n".join(lines)
        assert "src" in flat
        assert "mylib" in flat
        assert "__init__.py" in flat

    def test_last_item_uses_corner(self, fs) -> None:  # noqa: ANN001
        fs.create_file("/project/only.py", contents="")
        lines = _build_tree(Path("/project"))
        assert lines[-1].startswith("└── ")

    def test_non_last_item_uses_tee(self, fs) -> None:  # noqa: ANN001
        fs.create_file("/project/a.py", contents="")
        fs.create_file("/project/b.py", contents="")
        lines = _build_tree(Path("/project"))
        assert lines[0].startswith("├── ")


# ---------------------------------------------------------------------------
# _parse_pyproject
# ---------------------------------------------------------------------------


class TestParsePyproject:
    def test_returns_empty_dict_when_absent(self, fs) -> None:  # noqa: ANN001
        fs.create_dir("/project")
        data = _parse_pyproject(Path("/project"))
        assert data == {}

    def test_parses_project_name(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        data = _parse_pyproject(root)
        assert data["project"]["name"] == "mylib"

    def test_parses_dependencies(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        data = _parse_pyproject(root)
        assert "httpx>=0.27" in data["project"]["dependencies"]

    def test_parses_dev_dependencies(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        data = _parse_pyproject(root)
        assert "pytest>=8.0" in data["dependency-groups"]["dev"]


# ---------------------------------------------------------------------------
# _render_architecture
# ---------------------------------------------------------------------------


class TestRenderArchitecture:
    def test_contains_heading(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        output = _render_architecture(root)
        assert "## Architecture" in output

    def test_contains_root_name(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        output = _render_architecture(root)
        assert "project" in output

    def test_contains_fenced_block(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        output = _render_architecture(root)
        assert "```" in output

    def test_contains_source_files(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        output = _render_architecture(root)
        assert "src" in output
        assert "tests" in output

    def test_excludes_ignored_paths(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        fs.create_dir(root / ".git")
        fs.create_dir(root / "__pycache__")
        output = _render_architecture(root)
        assert ".git" not in output
        assert "__pycache__" not in output

    def test_dirs_have_trailing_slash(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        output = _render_architecture(root)
        assert "src/" in output


# ---------------------------------------------------------------------------
# _render_tech_stack
# ---------------------------------------------------------------------------


class TestRenderTechStack:
    def test_contains_heading(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        output = _render_tech_stack(root)
        assert "## Tech Stack" in output

    def test_contains_python_version(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        output = _render_tech_stack(root)
        assert ">=3.12" in output

    def test_contains_uv_link(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        output = _render_tech_stack(root)
        assert "uv" in output

    def test_lists_core_dependencies(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        output = _render_tech_stack(root)
        assert "httpx>=0.27" in output
        assert "typer>=0.12" in output

    def test_lists_dev_dependencies(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        output = _render_tech_stack(root)
        assert "pytest>=8.0" in output
        assert "ruff>=0.4" in output

    def test_no_pyproject_uses_fallback(self, fs) -> None:  # noqa: ANN001
        fs.create_dir("/empty")
        output = _render_tech_stack(Path("/empty"))
        assert "## Tech Stack" in output
        assert ">=3.12" in output  # default python version

    def test_table_structure(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        output = _render_tech_stack(root)
        assert "|" in output
        assert "Python" in output
        assert "Package Manager" in output


# ---------------------------------------------------------------------------
# _render_installation
# ---------------------------------------------------------------------------


class TestRenderInstallation:
    def test_contains_heading(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        output = _render_installation(root)
        assert "## Installation" in output

    def test_contains_uv_sync(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        output = _render_installation(root)
        assert "uv sync" in output

    def test_contains_dev_install(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        output = _render_installation(root)
        assert "uv sync --dev" in output

    def test_contains_project_name(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        output = _render_installation(root)
        assert "mylib" in output

    def test_bash_code_blocks(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        output = _render_installation(root)
        assert "```bash" in output

    def test_no_pyproject_uses_dir_name(self, fs) -> None:  # noqa: ANN001
        fs.create_dir("/myproject")
        output = _render_installation(Path("/myproject"))
        assert "myproject" in output


# ---------------------------------------------------------------------------
# _update_section / marker helpers
# ---------------------------------------------------------------------------


class TestMarkerHelpers:
    def test_begin_marker_format(self) -> None:
        assert _begin_marker("foo") == "<!-- markproof:begin:foo -->"

    def test_end_marker_format(self) -> None:
        assert _end_marker("foo") == "<!-- markproof:end:foo -->"

    def test_wrap_section_contains_body(self) -> None:
        wrapped = _wrap_section("foo", "## Foo\n\ncontent")
        assert "## Foo" in wrapped
        assert "content" in wrapped
        assert _begin_marker("foo") in wrapped
        assert _end_marker("foo") in wrapped

    def test_section_present_true(self) -> None:
        content = f"{_begin_marker('foo')}\ncontent\n{_end_marker('foo')}\n"
        assert _section_present(content, "foo") is True

    def test_section_present_false(self) -> None:
        assert _section_present("# Just a heading\n", "foo") is False


class TestUpdateSection:
    def test_replaces_existing_section(self) -> None:
        original = (
            "# Title\n\n"
            f"{_begin_marker('foo')}\n"
            "## Foo\n\nold content\n"
            f"{_end_marker('foo')}\n"
        )
        updated = _update_section(original, "foo", "## Foo\n\nnew content")
        assert "new content" in updated
        assert "old content" not in updated

    def test_preserves_content_before_section(self) -> None:
        original = (
            "# Title\n\nProse before.\n\n"
            f"{_begin_marker('foo')}\n## Foo\n{_end_marker('foo')}\n"
        )
        updated = _update_section(original, "foo", "## Foo\n\nupdated")
        assert "Prose before." in updated

    def test_preserves_content_after_section(self) -> None:
        original = (
            f"{_begin_marker('foo')}\n## Foo\n{_end_marker('foo')}\n\nProse after.\n"
        )
        updated = _update_section(original, "foo", "## Foo\n\nupdated")
        assert "Prose after." in updated

    def test_appends_when_section_absent(self) -> None:
        content = "# Title\n\nProse.\n"
        updated = _update_section(content, "bar", "## Bar\n\nbody")
        assert "## Bar" in updated
        assert "Prose." in updated
        assert _begin_marker("bar") in updated

    def test_marker_appears_once_after_replace(self) -> None:
        original = f"{_begin_marker('foo')}\n## Foo\nold\n{_end_marker('foo')}\n"
        updated = _update_section(original, "foo", "## Foo\nnew")
        assert updated.count(_begin_marker("foo")) == 1

    def test_marker_appears_once_after_append(self) -> None:
        content = "# Title\n"
        updated = _update_section(content, "bar", "## Bar")
        assert updated.count(_begin_marker("bar")) == 1

    def test_multiple_sections_independent(self) -> None:
        content = "# Title\n"
        content = _update_section(content, "foo", "## Foo\n\nfoo body")
        content = _update_section(content, "bar", "## Bar\n\nbar body")
        assert "foo body" in content
        assert "bar body" in content
        # Update only foo
        content = _update_section(content, "foo", "## Foo\n\nfoo updated")
        assert "foo updated" in content
        assert "bar body" in content  # bar untouched


# ---------------------------------------------------------------------------
# ReadmeGenerator.generate
# ---------------------------------------------------------------------------


class TestReadmeGenerator:
    def test_creates_readme_when_absent(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        gen = ReadmeGenerator(root=root)
        path = gen.generate()
        assert path.exists()

    def test_default_output_path(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        path = ReadmeGenerator(root=root).generate()
        assert path == root / "README.md"

    def test_custom_output_path(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        out = root / "DOCS.md"
        path = ReadmeGenerator(root=root).generate(output=out)
        assert path == out
        assert out.exists()

    def test_readme_contains_project_title(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        path = ReadmeGenerator(root=root).generate()
        content = path.read_text()
        assert "# mylib" in content

    def test_readme_contains_description(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        path = ReadmeGenerator(root=root).generate()
        content = path.read_text()
        assert "A sample library." in content

    def test_all_managed_sections_present(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        path = ReadmeGenerator(root=root).generate()
        content = path.read_text()
        for sid in ALL_SECTIONS:
            assert _begin_marker(sid) in content, f"missing: {sid}"
            assert _end_marker(sid) in content, f"missing end: {sid}"

    def test_updates_existing_readme_sections(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        gen = ReadmeGenerator(root=root)
        path = gen.generate()

        # simulate stale content in installation section
        old = path.read_text()
        stale = _update_section(
            old, SECTION_INSTALLATION, "## Installation\n\nold stuff"
        )
        path.write_text(stale)

        gen.generate()
        content = path.read_text()
        assert "old stuff" not in content
        assert "uv sync" in content

    def test_preserves_user_prose_outside_sections(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        readme = root / "README.md"
        readme.write_text(
            "# mylib\n\nUser prose here.\n\n## My Custom Section\n\nKeep this.\n"
        )
        ReadmeGenerator(root=root).generate()
        content = readme.read_text()
        assert "User prose here." in content
        assert "Keep this." in content

    def test_only_managed_sections_rendered(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        cfg = MarkProofConfig(sections=SectionsConfig(managed=[SECTION_INSTALLATION]))
        path = ReadmeGenerator(root=root, config=cfg).generate()
        content = path.read_text()
        assert _begin_marker(SECTION_INSTALLATION) in content
        assert _begin_marker(SECTION_ARCHITECTURE) not in content
        assert _begin_marker(SECTION_TECH_STACK) not in content

    def test_creates_parent_dirs(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        out = root / "docs" / "README.md"
        ReadmeGenerator(root=root).generate(output=out)
        assert out.exists()

    def test_config_readme_path_respected(self, fs) -> None:  # noqa: ANN001
        root = _make_project(
            fs,
            with_config=True,
            config_content='[readme]\npath = "DOCS.md"\n',
        )
        path = ReadmeGenerator(root=root).generate()
        assert path.name == "DOCS.md"

    def test_config_managed_sections_respected(self, fs) -> None:  # noqa: ANN001
        root = _make_project(
            fs,
            with_config=True,
            config_content=f'[sections]\nmanaged = ["{SECTION_TECH_STACK}"]\n',
        )
        path = ReadmeGenerator(root=root).generate()
        content = path.read_text()
        assert _begin_marker(SECTION_TECH_STACK) in content
        assert _begin_marker(SECTION_INSTALLATION) not in content


# ---------------------------------------------------------------------------
# check_readme
# ---------------------------------------------------------------------------


class TestCheckReadme:
    def test_passes_for_fully_generated_readme(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        path = ReadmeGenerator(root=root).generate()
        from markproof.config import load_config

        cfg = load_config(root)
        result = check_readme(path, cfg)
        assert result.passed is True
        assert result.missing_sections == []
        assert result.block_errors == []

    def test_fails_for_missing_section(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        readme = root / "README.md"
        readme.write_text("# mylib\n\nNo managed sections yet.\n")
        cfg = MarkProofConfig()
        result = check_readme(readme, cfg)
        assert result.passed is False
        assert SECTION_INSTALLATION in result.missing_sections

    def test_fails_for_nonexistent_readme(self, fs) -> None:  # noqa: ANN001
        fs.create_dir("/project")
        result = check_readme(Path("/project/README.md"), MarkProofConfig())
        assert result.passed is False
        assert result.block_errors  # "File not found" error

    def test_detects_python_block_error(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        path = ReadmeGenerator(root=root).generate()
        # Inject a broken Python block into the readme
        content = path.read_text()
        broken_block = "\n\n```python\nraise ValueError('injected error')\n```\n"
        path.write_text(content + broken_block)

        from markproof.config import load_config

        cfg = load_config(root)
        result = check_readme(path, cfg)
        assert result.passed is False
        assert any("ValueError" in e for e in result.block_errors)

    def test_passes_with_only_bash_blocks(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        path = ReadmeGenerator(root=root).generate()
        from markproof.config import load_config

        cfg = load_config(root)
        result = check_readme(path, cfg)
        # Installation section has bash blocks — executor skips them, no errors
        assert result.block_errors == []

    def test_check_result_readme_path(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        path = ReadmeGenerator(root=root).generate()
        cfg = MarkProofConfig()
        result = check_readme(path, cfg)
        assert result.readme_path == path

    def test_partial_missing_sections(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        readme = root / "README.md"
        # Only install section present
        readme.write_text(
            f"{_begin_marker(SECTION_INSTALLATION)}\n"
            "## Installation\n"
            f"{_end_marker(SECTION_INSTALLATION)}\n"
        )
        cfg = MarkProofConfig()
        result = check_readme(readme, cfg)
        assert SECTION_INSTALLATION not in result.missing_sections
        assert SECTION_ARCHITECTURE in result.missing_sections
        assert SECTION_TECH_STACK in result.missing_sections


# ---------------------------------------------------------------------------
# Integration: generate → check roundtrip
# ---------------------------------------------------------------------------


class TestGenerateCheckRoundtrip:
    def test_generated_readme_passes_check(self, fs) -> None:  # noqa: ANN001
        root = _make_project(fs)
        path = ReadmeGenerator(root=root).generate()
        from markproof.config import load_config

        cfg = load_config(root)
        result = check_readme(path, cfg)
        assert result.passed is True

    def test_idempotent_generate(self, fs) -> None:  # noqa: ANN001
        """Running generate twice yields the same output."""
        root = _make_project(fs)
        gen = ReadmeGenerator(root=root)
        path = gen.generate()
        first = path.read_text()
        gen.generate()
        second = path.read_text()
        assert first == second

    def test_custom_sections_config_roundtrip(self, fs) -> None:  # noqa: ANN001
        root = _make_project(
            fs,
            with_config=True,
            config_content=(
                '[readme]\npath = "README.md"\n'
                "[sections]\n"
                f'managed = ["{SECTION_INSTALLATION}", "{SECTION_TECH_STACK}"]\n'
            ),
        )
        gen = ReadmeGenerator(root=root)
        path = gen.generate()
        from markproof.config import load_config

        cfg = load_config(root)
        result = check_readme(path, cfg)
        assert result.passed is True
        assert result.missing_sections == []
