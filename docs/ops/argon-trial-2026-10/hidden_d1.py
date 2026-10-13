"""CTO acceptance cases for job D1 (comment-only checker), run on both outputs. Not shown to the workers.

    python hidden_d1.py <worktree>
"""
import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

wt = Path(sys.argv[1])
sys.path.insert(0, str(wt))
spec = importlib.util.spec_from_file_location("coc", wt / "tools" / "comment_only_check.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
cc = m.code_changed

CASES = [  # (name, old, new, path, expected code_changed)
    ("py comment only", "x = 1  # one\ny = 2\n", "x = 1  # uno\ny = 2\n", "a.py", False),
    ("py func docstring", 'def f():\n    """Doc."""\n    return 1\n', 'def f():\n    """Docs, changed."""\n    return 1\n', "a.py", False),
    ("py module docstring", '"""Mod."""\nimport os\n', '"""Module text."""\nimport os\n', "a.py", False),
    ("py class docstring", 'class A:\n    """A."""\n    x = 1\n', 'class A:\n    """Class A."""\n    x = 1\n', "a.py", False),
    ("py comment line added", "x = 1\ny = 2\n", "x = 1\n# note\ny = 2\n", "a.py", False),
    ("py comment line in block", "def f():\n    # a\n    return 1\n", "def f():\n    # b\n    # c\n    return 1\n", "a.py", False),
    ("py string literal", 'x = "a"\n', 'x = "b"\n', "a.py", True),
    ("py identifier", "x = 1\n", "y = 1\n", "a.py", True),
    ("py number", "x = 1\n", "x = 2\n", "a.py", True),
    ("py hash in string", 'x = "a # b"\n', 'x = "a # c"\n', "a.py", True),
    ("py non-docstring string expr after code", 'x = 1\ny = "s"\n', 'x = 1\ny = "t"\n', "a.py", True),
    ("js line comment", "const a = 1; // one\n", "const a = 1; // uno\n", "a.js", False),
    ("js block comment", "/* one */\nconst a = 1;\n", "/* uno\n dos */\nconst a = 1;\n", "a.js", False),
    ("js slashes in string", 'const u = "http://a";\n', 'const u = "http://b";\n', "a.js", True),
    ("js template literal", "const t = `x // y`;\n", "const t = `x // z`;\n", "a.ts", True),
    ("js code", "const a = 1;\n", "const a = 2;\n", "a.mjs", True),
    ("go comment", "package m\n// F does\nfunc F() {}\n", "package m\n// F does it\nfunc F() {}\n", "a.go", False),
    ("sh comment", "#!/bin/bash\n# one\necho hi\n", "#!/bin/bash\n# uno\necho hi\n", "a.sh", False),
    ("sh hash in quotes", 'echo "a # b"\n', 'echo "a # c"\n', "a.sh", True),
    ("sh shebang is code", "#!/bin/bash\necho hi\n", "#!/bin/sh\necho hi\n", "a.sh", True),
    ("yaml comment", "a: 1  # one\n", "a: 1  # uno\n", "a.yaml", False),
    ("yaml value", "a: 1\n", "a: 2\n", "a.yml", True),
    # Round 2 (r1 feedback): indentation is code in Python and YAML, token spacing is code in shell.
    ("py statement leaves block", "if x:\n    y()\n    z()\n", "if x:\n    y()\nz()\n", "a.py", True),
    ("py statement enters block", "for i in r:\n    a()\nb()\n", "for i in r:\n    a()\n    b()\n", "a.py", True),
    ("py comment re-indented", "def f():\n    # a\n    return 1\n", "def f():\n        # a\n    return 1\n", "a.py", False),
    ("py spacing between tokens", "x=1\n", "x = 1\n", "a.py", False),
    ("yaml key leaves mapping", "a:\n  b: 1\n", "a:\nb: 1\n", "a.yaml", True),
    ("yaml list item dedented", "a:\n  - 1\n  - 2\n", "a:\n  - 1\n- 2\n", "a.yml", True),
    ("yaml trailing comment changed", "a:\n  b: 1  # x\n", "a:\n  b: 1  # y\n", "a.yaml", False),
    ("sh assignment becomes command", "x=1\n", "x = 1\n", "a.sh", True),
    ("sh trailing comment changed", "x=1   # c\n", "x=1 # d\n", "a.sh", False),
    ("sh run of spaces between words", "echo a  b\n", "echo a b\n", "a.sh", False),
]

ok = 0
for name, old, new, path, want in CASES:
    try:
        got = cc(old, new, path)
        res = "PASS" if bool(got) == want else f"FAIL (got {got}, want {want})"
    except Exception as e:  # noqa: BLE001
        res = f"ERROR {type(e).__name__}: {e}"[:160]
    ok += res == "PASS"
    print(f"{res:<8} {name}")

try:
    cc("# a\n", "# b\n", "a.md")
    print("FAIL     unsupported .md did not raise"); bad = 1
except ValueError:
    print("PASS     unsupported .md raises ValueError"); ok += 1
except Exception as e:  # noqa: BLE001
    print(f"FAIL     unsupported .md raised {type(e).__name__}")

# CLI on a throwaway repo
with tempfile.TemporaryDirectory() as d:
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    run = lambda *a: subprocess.run(a, cwd=d, capture_output=True, text=True, env=env)
    run("git", "init", "-q")
    Path(d, "a.py").write_text("x = 1  # one\n")
    Path(d, "b.js").write_text("const a = 1;\n")
    run("git", "add", "-A"); run("git", "commit", "-qm", "base")
    Path(d, "a.py").write_text("x = 1  # uno\n")
    p = run(sys.executable, str(wt / "tools" / "comment_only_check.py"), "--base", "HEAD")
    good = p.returncode == 0 and "OK a.py" in p.stdout
    print(("PASS" if good else f"FAIL (exit {p.returncode}: {p.stdout.strip()[:120]} {p.stderr.strip()[-160:]})").ljust(8), "CLI comment-only edit exits 0, prints OK a.py")
    ok += good
    Path(d, "b.js").write_text("const a = 2;\n")
    p = run(sys.executable, str(wt / "tools" / "comment_only_check.py"), "--base", "HEAD")
    good = p.returncode == 1 and "CODE b.js" in p.stdout
    print(("PASS" if good else f"FAIL (exit {p.returncode}: {p.stdout.strip()[:120]})").ljust(8), "CLI code edit exits 1, prints CODE b.js")
    ok += good

total = len(CASES) + 3
print(f"hidden acceptance: {ok}/{total} pass")
