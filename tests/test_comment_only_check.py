"""Tests for tools/comment_only_check.py."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tools.comment_only_check import code_changed, main


# ── Python (.py) ──────────────────────────────────────────────────────────────


def test_python_comment_only_change_passes():
    old = (
        "# หัวข้อไฟล์\n"
        "def compute(x: int) -> int:\n"
        "    # คำนวณค่า\n"
        "    return x + 1  # บวกหนึ่ง\n"
    )
    new = (
        "# File header\n"
        "# Extra comment line added\n\n"
        "def compute(x: int) -> int:\n"
        "    # Compute value\n"
        "    # Second comment line\n"
        "    return x + 1  # plus one\n"
    )
    assert code_changed(old, new, "pkg/mod.py") is False


def test_python_docstring_only_change_passes():
    old = (
        '"""ด็อกสตริงระดับโมดูล"""\n\n'
        "class Service:\n"
        "    # คอมเมนต์ก่อนด็อกสตริง\n"
        '    """ด็อกสตริงของคลาส"""\n\n'
        "    def run(self) -> int:\n"
        '        """ด็อกสตริงของเมธอด"""\n'
        "        return 42\n\n"
        "    async def arun(self) -> int:\n"
        '        """ด็อกสตริงของ async"""\n'
        "        return 42\n"
    )
    new = (
        '"""Module docstring in English."""\n\n'
        "class Service:\n"
        "    # Comment before docstring\n"
        '    """Class docstring in English."""\n\n'
        "    def run(self) -> int:\n"
        '        """Method docstring in English."""\n'
        "        return 42\n\n"
        "    async def arun(self) -> int:\n"
        '        """Async method docstring in English."""\n'
        "        return 42\n"
    )
    assert code_changed(old, new, "pkg/service.py") is False


def test_python_changed_string_literal_fails():
    old = 'def greet() -> str:\n    """คำอธิบาย"""\n    msg = "สวัสดี"\n    return msg\n'
    new = 'def greet() -> str:\n    """Description"""\n    msg = "Hello"\n    return msg\n'
    assert code_changed(old, new, "pkg/greet.py") is True

    # A standalone string that is not the first statement of a body is not a docstring.
    old_non_doc = 'def f():\n    x = 1\n    "สวัสดี"\n    return x\n'
    new_non_doc = 'def f():\n    x = 1\n    "Hello"\n    return x\n'
    assert code_changed(old_non_doc, new_non_doc, "pkg/f.py") is True


def test_python_changed_identifier_or_number_fails():
    base = "def calc(value: int) -> int:\n    return value + 10\n"
    assert code_changed(base, "def calc(val: int) -> int:\n    return val + 10\n", "a.py") is True
    assert code_changed(base, "def calc(value: int) -> int:\n    return value + 20\n", "a.py") is True


def test_python_indentation_change_fails_and_comment_reindent_passes():
    assert code_changed("if x:\n    y()\n    z()\n", "if x:\n    y()\nz()\n", "a.py") is True
    assert (
        code_changed(
            "if x:\n    # คอมเมนต์\n    y()\n",
            "if x:\n  # comment\n    y()\n",
            "a.py",
        )
        is False
    )
    assert (
        code_changed(
            'def f():\n    """ด็อกสตริง"""\n    return 1\n',
            "def f():\n    return 1\n",
            "a.py",
        )
        is False
    )


# ── C-like (.js .mjs .cjs .ts .tsx .jsx .go) ──────────────────────────────────


@pytest.mark.parametrize("ext", [".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".go"])
def test_clike_comment_only_change_passes(ext: str):
    old = (
        "// คอมเมนต์บรรทัด\n"
        "/* คอมเมนต์\n"
        "   หลายบรรทัด */\n"
        "const x = 10; // ท้ายบรรทัด\n"
    )
    new = (
        "// Line comment\n"
        "/* Multi-line\n"
        "   block comment */\n"
        "const x = 10; // trailing\n"
    )
    assert code_changed(old, new, f"src/index{ext}") is False


def test_clike_slashes_inside_strings_are_not_comments():
    old = 'const url = "https://example.com//สวัสดี";\n'
    new = 'const url = "https://example.com//hello";\n'
    assert code_changed(old, new, "src/app.js") is True

    old_block = "const pat = '/* ไทย */';\n"
    new_block = "const pat = '/* eng */';\n"
    assert code_changed(old_block, new_block, "src/app.ts") is True

    old_tpl = "const tpl = `prefix // ไทย`;\n"
    new_tpl = "const tpl = `prefix // eng`;\n"
    assert code_changed(old_tpl, new_tpl, "src/app.tsx") is True


def test_clike_changed_string_identifier_or_number_fails():
    base = 'const count = 5;\nconst label = "สวัสดี";\n'
    assert code_changed(base, 'const count = 5;\nconst label = "hello";\n', "a.js") is True
    assert code_changed(base, 'const total = 5;\nconst label = "สวัสดี";\n', "a.js") is True
    assert code_changed(base, 'const count = 6;\nconst label = "สวัสดี";\n', "a.go") is True


# ── Hash (.sh .bash .yaml .yml .toml) ─────────────────────────────────────────


@pytest.mark.parametrize("ext", [".sh", ".bash", ".yaml", ".yml", ".toml"])
def test_hash_comment_only_change_passes(ext: str):
    old = "# คอมเมนต์ด้านบน\nkey = 123 # คอมเมนต์ท้ายบรรทัด\n"
    new = "# Top comment\nkey = 123 # Trailing comment\n"
    assert code_changed(old, new, f"config/file{ext}") is False


def test_yaml_indentation_and_trailing_comment():
    assert code_changed("a:\n  b: 1\n", "a:\nb: 1\n", "cfg.yaml") is True
    assert code_changed("a:\n  b: 1  # คอมเมนต์\n", "a:\n  b: 1 # comment\n", "cfg.yaml") is False


def test_shell_token_spacing_and_trailing_comment():
    assert code_changed("x=1\n", "x = 1\n", "run.sh") is True
    assert code_changed("x=1   # c\n", "x=1 # d\n", "run.sh") is False


def test_hash_inside_quoted_string_is_not_a_comment():
    old_dq = 'echo "สวัสดี # นี่ไม่ใช่คอมเมนต์" # คอมเมนต์จริง\n'
    new_dq = 'echo "สวัสดี # changed" # คอมเมนต์จริง\n'
    assert code_changed(old_dq, new_dq, "run.sh") is True

    old_sq = "echo 'สวัสดี # ไม่ใช่คอมเมนต์'\n"
    new_sq = "echo 'สวัสดี # changed'\n"
    assert code_changed(old_sq, new_sq, "run.bash") is True

    old_yaml = 'title: "หัวข้อ # 1" # คอมเมนต์\n'
    new_yaml = 'title: "หัวข้อ # 2" # คอมเมนต์\n'
    assert code_changed(old_yaml, new_yaml, "cfg.yaml") is True


@pytest.mark.parametrize(
    "old,new,path",
    [
        ("echo a#b\n", "echo a#c\n", "run.sh"),
        ("curl http://x/#one\n", "curl http://x/#two\n", "run.sh"),
        ("echo ${#a}\n", "echo ${#b}\n", "run.sh"),
        ("a: x#1\n", "a: x#2\n", "conf.yaml"),
        ("u: http://h/#a\n", "u: http://h/#b\n", "conf.yml"),
    ],
)
def test_hash_not_at_word_start_is_code(old: str, new: str, path: str):
    # Reviewer fix (cto-d1a121af): in shell `#` starts a comment only at the start of a word, in YAML only at
    # line start or after whitespace. Everything after a mid-word `#` is code and must be compared.
    assert code_changed(old, new, path) is True


def test_hash_after_a_word_break_is_still_a_comment():
    assert code_changed("echo a;# one\n", "echo a;# two\n", "run.sh") is False
    assert code_changed("a: 1 # one\n", "a: 1 # two\n", "conf.yaml") is False


def test_hash_shebang_is_code():
    old = "#!/usr/bin/env bash\n# คอมเมนต์\necho 1\n"
    new_comment_only = "#!/usr/bin/env bash\n# English comment\necho 1\n"
    new_shebang = "#!/usr/bin/env sh\n# คอมเมนต์\necho 1\n"
    assert code_changed(old, new_comment_only, "script.sh") is False
    assert code_changed(old, new_shebang, "script.sh") is True


def test_hash_changed_string_identifier_or_number_fails():
    base = 'port = 8080\nhost = "localhost"\n'
    assert code_changed(base, 'port = 8080\nhost = "127.0.0.1"\n', "cfg.toml") is True
    assert code_changed(base, 'listen_port = 8080\nhost = "localhost"\n', "cfg.toml") is True
    assert code_changed(base, 'port = 9090\nhost = "localhost"\n', "cfg.yml") is True


# ── Unsupported extensions ────────────────────────────────────────────────────


@pytest.mark.parametrize("path", ["README.md", "data.json", "notes.txt", "index.html", "Makefile"])
def test_unsupported_extension_raises_value_error(path: str):
    with pytest.raises(ValueError):
        code_changed("a\n", "a\n", path)


# ── CLI ───────────────────────────────────────────────────────────────────────


def test_cli_reports_ok_code_and_unsupported(tmp_path: Path, monkeypatch, capsys):
    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)

    git("init")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "Test User")

    (tmp_path / "ok.py").write_text('"""ไทย"""\nx = 1  # คอมเมนต์\n', encoding="utf-8")
    (tmp_path / "code.js").write_text('const a = "ไทย"; // คอมเมนต์\n', encoding="utf-8")
    (tmp_path / "gone.sh").write_text("# ไทย\necho 1\n", encoding="utf-8")
    (tmp_path / "doc.md").write_text("# ไทย\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-m", "base")

    # Modify files in working tree
    (tmp_path / "ok.py").write_text('"""English"""\nx = 1  # comment\n', encoding="utf-8")
    (tmp_path / "code.js").write_text('const a = "English"; // comment\n', encoding="utf-8")
    (tmp_path / "gone.sh").unlink()
    (tmp_path / "doc.md").write_text("# English\n", encoding="utf-8")
    (tmp_path / "added.py").write_text("# new file\n", encoding="utf-8")
    git("add", "added.py")

    monkeypatch.chdir(tmp_path)

    # Check only ok.py -> exit 0
    rc_ok = main(["--base", "HEAD", "ok.py"])
    out_ok = capsys.readouterr().out.strip().splitlines()
    assert rc_ok == 0
    assert out_ok == ["OK ok.py"]

    # Check all changed files in working tree -> exit 1
    rc_all = main(["--base", "HEAD"])
    lines = set(capsys.readouterr().out.strip().splitlines())
    assert rc_all == 1
    assert lines == {
        "OK ok.py",
        "CODE code.js",
        "CODE gone.sh",
        "CODE added.py",
        "UNSUPPORTED doc.md",
    }

    # Commit and verify --base with explicit --head
    git("add", "-A")
    git("commit", "-m", "head")
    assert main(["--base", "HEAD~1", "--head", "HEAD", "ok.py"]) == 0
    assert capsys.readouterr().out.strip().splitlines() == ["OK ok.py"]
    assert main(["--base", "HEAD~1", "--head", "HEAD"]) == 1
    assert set(capsys.readouterr().out.strip().splitlines()) == {
        "OK ok.py",
        "CODE code.js",
        "CODE gone.sh",
        "CODE added.py",
        "UNSUPPORTED doc.md",
    }
