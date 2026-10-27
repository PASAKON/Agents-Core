"""scripts/security/github-scan-report.sh against a stub `gh`: no network, no real repo, and the
script must only ever READ (a PATCH is printed for a human, never run)."""
import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "security" / "github-scan-report.sh"

STUB = """#!/bin/sh
echo "$*" >> "$GH_LOG"
case "$1" in
  repo) printf 'pub-open\\tPUBLIC\\tfalse\\npub-ok\\tPUBLIC\\tfalse\\npriv\\tPRIVATE\\tfalse\\npub-arch\\tPUBLIC\\ttrue\\npub-blind\\tPUBLIC\\tfalse\\n' ;;
  api) case "$2" in
         repos/O/pub-open) printf 'enabled\\tdisabled\\n' ;;
         repos/O/pub-ok) printf 'enabled\\tenabled\\n' ;;
         repos/O/pub-arch) printf 'disabled\\tdisabled\\n' ;;
         *) printf 'unknown\\tunknown\\n' ;;
       esac ;;
esac
"""


def test_prints_a_patch_line_only_for_an_open_public_repo_and_never_runs_it(tmp_path):
    gh = tmp_path / "gh"
    gh.write_text(STUB)
    gh.chmod(0o755)
    log = tmp_path / "gh.log"
    env = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}", "GH_LOG": str(log)}
    result = subprocess.run(["bash", str(SCRIPT), "O"], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    patch_lines = [l for l in result.stdout.splitlines() if l.startswith("gh api -X PATCH")]
    assert patch_lines == [
        "gh api -X PATCH repos/O/pub-open -f 'security_and_analysis[secret_scanning][status]=enabled' "
        "-f 'security_and_analysis[secret_scanning_push_protection][status]=enabled'"
    ]
    assert "repos=5 public-not-fully-protected=1 public-unreadable=1 owner=O" in result.stdout
    assert "pub-blind\tPUBLIC\tunknown\tunknown\tcannot read settings" in result.stdout
    assert "pub-arch\tPUBLIC\tdisabled\tdisabled\tarchived" in result.stdout  # archived: reported, no PATCH
    assert "PATCH" not in log.read_text()                                      # the script itself only ever read
