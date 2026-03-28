"""Tests for markproof.parser and markproof.models."""

from pathlib import Path

import pytest

from markproof.models import CodeBlock, CodeBlockKind, ParseResult
from markproof.parser import (
    _classify,
    _closing_fence_re,
    _parse_comment_metadata,
    parse_file,
    parse_text,
)


class TestParseCommentMetadata:
    def test_single_key_value(self) -> None:
        assert _parse_comment_metadata("version=3.10") == {"version": "3.10"}

    def test_bare_flag(self) -> None:
        assert _parse_comment_metadata("skip") == {"skip": "true"}

    def test_multiple_tokens(self) -> None:
        result = _parse_comment_metadata("skip version=3.10 id=ex-1")
        assert result == {"skip": "true", "version": "3.10", "id": "ex-1"}

    def test_empty_string(self) -> None:
        assert _parse_comment_metadata("") == {}

    def test_extra_whitespace(self) -> None:
        result = _parse_comment_metadata("  key=val  ")
        assert result == {"key": "val"}


class TestClassify:
    @pytest.mark.parametrize(
        "source",
        [
            "pip install requests",
            "pip3 install requests",
            "uv add requests",
            "uv pip install requests",
            "conda install numpy",
            "poetry add fastapi",
            "pipenv install httpx",
            "  pip install requests  ",
        ],
    )
    def test_install_patterns(self, source: str) -> None:
        assert _classify(source) == CodeBlockKind.INSTALL

    def test_usage_import(self) -> None:
        source = "import requests\nrequests.get('https://example.com')"
        assert _classify(source) == CodeBlockKind.USAGE

    def test_usage_empty(self) -> None:
        assert _classify("") == CodeBlockKind.USAGE

    def test_install_multiline_block(self) -> None:
        source = "# first install the library\npip install rich\n"
        assert _classify(source) == CodeBlockKind.INSTALL

    def test_usage_similar_but_not_install(self) -> None:
        assert _classify("# reinstall everything") == CodeBlockKind.USAGE


class TestClosingFenceRe:
    def test_backtick_three(self) -> None:
        pat = _closing_fence_re("```")
        assert pat.match("```")
        assert pat.match("````")
        assert not pat.match("``")
        assert not pat.match("~~~")

    def test_tilde_four(self) -> None:
        pat = _closing_fence_re("~~~~")
        assert pat.match("~~~~")
        assert pat.match("~~~~~")
        assert not pat.match("~~~")

    def test_trailing_whitespace_allowed(self) -> None:
        pat = _closing_fence_re("```")
        assert pat.match("```   ")

    def test_no_match_with_language(self) -> None:
        pat = _closing_fence_re("```")
        assert not pat.match("```python")


class TestParseTextBasic:
    def test_empty_document(self) -> None:
        result = parse_text("", Path("empty.md"))
        assert isinstance(result, ParseResult)
        assert result.blocks == []
        assert result.path == Path("empty.md")

    def test_no_code_blocks(self) -> None:
        md = "# Hello\n\nJust prose, no code.\n"
        result = parse_text(md, Path("doc.md"))
        assert result.blocks == []

    def test_single_python_block(self) -> None:
        md = "```python\nimport os\n```"
        result = parse_text(md, Path("a.md"))
        assert len(result.blocks) == 1
        block = result.blocks[0]
        assert block.language == "python"
        assert block.source == "import os"
        assert block.line_number == 1
        assert block.kind == CodeBlockKind.USAGE
        assert block.metadata == {}

    def test_line_number_is_one_based(self) -> None:
        md = "# Title\n\n```python\npass\n```"
        result = parse_text(md, Path("x.md"))
        assert result.blocks[0].line_number == 3

    def test_language_normalised_to_lowercase(self) -> None:
        md = "```Python\npass\n```"
        result = parse_text(md, Path("x.md"))
        assert result.blocks[0].language == "python"

    def test_no_language_tag(self) -> None:
        md = "```\nsome text\n```"
        result = parse_text(md, Path("x.md"))
        assert result.blocks[0].language == ""

    def test_multiple_blocks(self) -> None:
        md = "```bash\npip install rich\n```\n\n```python\nimport rich\n```\n"
        result = parse_text(md, Path("multi.md"))
        assert len(result.blocks) == 2
        assert result.blocks[0].kind == CodeBlockKind.INSTALL
        assert result.blocks[1].kind == CodeBlockKind.USAGE

    def test_tilde_fence(self) -> None:
        md = "~~~python\nprint('hi')\n~~~"
        result = parse_text(md, Path("t.md"))
        assert len(result.blocks) == 1
        assert result.blocks[0].source == "print('hi')"

    def test_four_backtick_fence(self) -> None:
        md = "````python\ncode\n````"
        result = parse_text(md, Path("t.md"))
        assert result.blocks[0].source == "code"

    def test_fence_not_closed_eof(self) -> None:
        """Unclosed fences are collected to end-of-file."""
        md = "```python\nimport sys\n"
        result = parse_text(md, Path("t.md"))
        assert len(result.blocks) == 1
        assert result.blocks[0].source == "import sys"

    def test_inner_shorter_fence_is_content(self) -> None:
        """A `` inside a ```` block is content, not a closer."""
        md = "````python\n```\nstill content\n```\n````"
        result = parse_text(md, Path("t.md"))
        assert len(result.blocks) == 1
        assert "still content" in result.blocks[0].source

    def test_multiline_source_preserved(self) -> None:
        md = "```python\na = 1\nb = 2\nc = 3\n```"
        result = parse_text(md, Path("t.md"))
        assert result.blocks[0].source == "a = 1\nb = 2\nc = 3"


class TestParseTextMetadata:
    def test_single_flag_before_block(self) -> None:
        md = "<!-- markproof:skip -->\n```python\npass\n```"
        result = parse_text(md, Path("m.md"))
        assert result.blocks[0].metadata == {"skip": "true"}

    def test_key_value_before_block(self) -> None:
        md = "<!-- markproof:version=3.10 -->\n```python\npass\n```"
        result = parse_text(md, Path("m.md"))
        assert result.blocks[0].metadata == {"version": "3.10"}

    def test_multiple_tokens_in_one_comment(self) -> None:
        md = "<!-- markproof:skip id=example-1 -->\n```python\npass\n```"
        result = parse_text(md, Path("m.md"))
        assert result.blocks[0].metadata == {"skip": "true", "id": "example-1"}

    def test_multiple_comments_merged(self) -> None:
        md = (
            "<!-- markproof:skip -->\n"
            "<!-- markproof:version=3.12 -->\n"
            "```python\npass\n```"
        )
        result = parse_text(md, Path("m.md"))
        assert result.blocks[0].metadata == {"skip": "true", "version": "3.12"}

    def test_blank_lines_between_comment_and_block(self) -> None:
        md = "<!-- markproof:skip -->\n\n\n```python\npass\n```"
        result = parse_text(md, Path("m.md"))
        assert result.blocks[0].metadata == {"skip": "true"}

    def test_prose_resets_metadata(self) -> None:
        """A non-blank non-comment line between comment and block clears metadata."""
        md = "<!-- markproof:skip -->\nsome prose here\n```python\npass\n```"
        result = parse_text(md, Path("m.md"))
        assert result.blocks[0].metadata == {}

    def test_metadata_not_shared_between_blocks(self) -> None:
        md = "<!-- markproof:skip -->\n```python\npass\n```\n```python\npass\n```\n"
        result = parse_text(md, Path("m.md"))
        assert result.blocks[0].metadata == {"skip": "true"}
        assert result.blocks[1].metadata == {}

    def test_comment_case_insensitive(self) -> None:
        md = "<!-- MARKPROOF:skip -->\n```python\npass\n```"
        result = parse_text(md, Path("m.md"))
        assert result.blocks[0].metadata == {"skip": "true"}

    def test_comment_not_markproof_namespace_ignored(self) -> None:
        md = "<!-- some other comment -->\n```python\npass\n```"
        result = parse_text(md, Path("m.md"))
        assert result.blocks[0].metadata == {}


class TestParseTextClassification:
    def test_bash_pip_install(self) -> None:
        md = "```bash\npip install requests\n```"
        result = parse_text(md, Path("c.md"))
        assert result.blocks[0].kind == CodeBlockKind.INSTALL

    def test_python_import_is_usage(self) -> None:
        md = "```python\nimport requests\nrequests.get('/')\n```"
        result = parse_text(md, Path("c.md"))
        assert result.blocks[0].kind == CodeBlockKind.USAGE

    def test_unlabelled_block_with_pip(self) -> None:
        md = "```\npip install httpx\n```"
        result = parse_text(md, Path("c.md"))
        assert result.blocks[0].kind == CodeBlockKind.INSTALL

    def test_uv_add(self) -> None:
        md = "```sh\nuv add pydantic\n```"
        result = parse_text(md, Path("c.md"))
        assert result.blocks[0].kind == CodeBlockKind.INSTALL

    def test_conda_install(self) -> None:
        md = "```shell\nconda install numpy\n```"
        result = parse_text(md, Path("c.md"))
        assert result.blocks[0].kind == CodeBlockKind.INSTALL


class TestParseFile:
    def test_parse_file_reads_path(self, fs) -> None:  # noqa: ANN001
        fs.create_file(
            "/docs/guide.md",
            contents="```python\nimport os\n```\n",
        )
        result = parse_file(Path("/docs/guide.md"))
        assert result.path == Path("/docs/guide.md")
        assert len(result.blocks) == 1
        assert result.blocks[0].source == "import os"

    def test_parse_file_empty(self, fs) -> None:  # noqa: ANN001
        fs.create_file("/docs/empty.md", contents="")
        result = parse_file(Path("/docs/empty.md"))
        assert result.blocks == []

    def test_parse_file_with_metadata(self, fs) -> None:  # noqa: ANN001
        content = "<!-- markproof:skip -->\n```python\npass\n```\n"
        fs.create_file("/docs/meta.md", contents=content)
        result = parse_file(Path("/docs/meta.md"))
        assert result.blocks[0].metadata == {"skip": "true"}

    def test_parse_file_missing_raises(self, fs) -> None:  # noqa: ANN001
        with pytest.raises(FileNotFoundError):
            parse_file(Path("/does/not/exist.md"))

    def test_parse_file_install_and_usage(self, fs) -> None:  # noqa: ANN001
        content = (
            "## Install\n\n"
            "```bash\npip install mylib\n```\n\n"
            "## Usage\n\n"
            "```python\nimport mylib\nmylib.run()\n```\n"
        )
        fs.create_file("/docs/readme.md", contents=content)
        result = parse_file(Path("/docs/readme.md"))
        assert len(result.blocks) == 2
        assert result.blocks[0].kind == CodeBlockKind.INSTALL
        assert result.blocks[1].kind == CodeBlockKind.USAGE


class TestModels:
    def test_code_block_kind_values(self) -> None:
        assert CodeBlockKind.INSTALL == "install"
        assert CodeBlockKind.USAGE == "usage"

    def test_parse_result_path_stored(self) -> None:
        result = parse_text("", Path("x/y/z.md"))
        assert result.path == Path("x/y/z.md")

    def test_code_block_fields(self) -> None:
        block = CodeBlock(
            source="import os",
            language="python",
            line_number=5,
            kind=CodeBlockKind.USAGE,
            metadata={"id": "ex"},
        )
        assert block.source == "import os"
        assert block.language == "python"
        assert block.line_number == 5
        assert block.kind == CodeBlockKind.USAGE
        assert block.metadata == {"id": "ex"}
