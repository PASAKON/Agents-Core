"""
Tests for scripts/security/leak-guards.sh (HQSecurity M3).

Every test works on throwaway repos under tmp_path and a scrubbed git environment: no real repo,
no real hooks, no network (the push tests push to a bare repo on the same disk).

The tests that need gitleaks' real rules skip, with a reason, when gitleaks is not installed. The
rest (chaining, idempotency, --check, hooksPath, ...) run with a stub gitleaks so CI covers them.
"""
import os
import pwd
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "security" / "leak-guards.sh"
INSTALL_GIT_HOOKS = Path(__file__).resolve().parents[1] / "scripts" / "install-git-hooks.sh"
REAL_GITLEAKS = shutil.which("gitleaks")
needs_gitleaks = pytest.mark.skipif(REAL_GITLEAKS is None, reason="gitleaks is not installed on this machine")


def fake_key():
    # A GitHub-PAT-shaped string that gitleaks' default rules catch. It is random letters (no real
    # token has this checksum) and it is built from parts so this file never contains it whole.
    return "ghp_" + "Zk3QwR8vN2xT6yB9" + "mC4dL7fH1sJ5pA0gEuXo"


@pytest.fixture(autouse=True)
def _umask_022():
    """The ownership guard skips group/other-writable dirs; the repos these tests make must not be."""
    old = os.umask(0o022)
    yield
    os.umask(old)


@pytest.fixture
def env(tmp_path):
    """A scrubbed environment: no GIT_* from the caller, no global/system git config."""
    home = tmp_path / "home"
    home.mkdir()
    e = {k: v for k, v in os.environ.items()
         if not k.startswith("GIT_") and k not in ("ALLOW_NO_GITLEAKS", "TMPDIR")}
    e.update(HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"), GIT_CONFIG_NOSYSTEM="1",
             GIT_CONFIG_GLOBAL=os.devnull, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t.t",
             GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t.t")
    return e


@pytest.fixture
def stub_env(env, tmp_path):
    """env + a gitleaks that finds nothing, first on PATH."""
    bin_dir = tmp_path / "stubbin"
    bin_dir.mkdir()
    stub = bin_dir / "gitleaks"
    stub.write_text('#!/bin/sh\n[ "$1" = version ] && echo 8.30.1\nexit 0\n')
    stub.chmod(0o755)
    return {**env, "PATH": f"{bin_dir}:{env['PATH']}"}


def git(repo, *args, env, check=True):
    return subprocess.run(["git", "-C", str(repo), *args], env=env, capture_output=True, text=True, check=check)


def make_repo(parent, name, env):
    repo = Path(parent) / name
    repo.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], env=env, check=True)
    return repo


def lg(env, *args):
    return subprocess.run(["bash", str(SCRIPT), *map(str, args)], env=env, capture_output=True, text=True)


def hooks(repo):
    return Path(repo) / ".git" / "hooks"


def commit(repo, name, text, env, *extra):
    (repo / name).write_text(text)
    git(repo, "add", name, env=env)
    return git(repo, "commit", "-q", "-m", f"add {name}", *extra, env=env, check=False)


def snapshot(d):
    """name -> (bytes, mtime_ns) for everything in a hooks dir, samples excluded."""
    return {p.name: (p.read_bytes(), p.stat().st_mtime_ns)
            for p in sorted(Path(d).iterdir()) if not p.name.endswith(".sample")}


# ---------------------------------------------------------------------------- the five asked-for cases

@needs_gitleaks
def test_a_commit_with_a_planted_key_is_refused(tmp_path, env):
    repo = make_repo(tmp_path, "r", env)
    assert lg(env, "--install", tmp_path).returncode == 0
    result = commit(repo, "leak.txt", f"token = {fake_key()}\n", env)
    assert result.returncode != 0
    assert "commit BLOCKED" in result.stderr
    assert fake_key() not in result.stdout + result.stderr  # --redact
    assert git(repo, "rev-parse", "--verify", "HEAD", env=env, check=False).returncode != 0  # no commit made


@needs_gitleaks
def test_b_a_clean_commit_is_allowed(tmp_path, env):
    repo = make_repo(tmp_path, "r", env)
    assert lg(env, "--install", tmp_path).returncode == 0
    result = commit(repo, "ok.txt", "nothing secret here\n", env)
    assert result.returncode == 0, result.stderr
    assert git(repo, "rev-parse", "--verify", "HEAD", env=env).returncode == 0


def test_c_an_existing_pre_push_hook_still_runs_and_still_blocks(tmp_path, stub_env):
    repo = make_repo(tmp_path, "r", stub_env)
    proof, seen = tmp_path / "ran", tmp_path / "stdin-seen"
    old = hooks(repo) / "pre-push"
    old.write_text(f'#!/bin/sh\necho "$1" > "{proof}"\ncat > "{seen}"\nexit "${{OLD_RC:-0}}"\n')
    old.chmod(0o755)
    result = lg(stub_env, "--install", tmp_path)
    assert result.returncode == 0, result.stderr
    assert "pre-push=chained" in result.stdout
    assert (hooks(repo) / "pre-push.local").read_text().startswith("#!/bin/sh\necho")  # old one moved, intact
    line = "refs/heads/main " + "1" * 40 + " refs/heads/main " + "0" * 40 + "\n"
    hook = str(hooks(repo) / "pre-push")
    ok = subprocess.run([hook, "origin", "x"], input=line, env={**stub_env, "OLD_RC": "0"}, capture_output=True, text=True)
    assert ok.returncode == 0, ok.stderr
    assert proof.read_text().strip() == "origin"      # it ran, with the arguments git gave
    assert seen.read_text() == line                    # ... and with the stdin git gave
    stop = subprocess.run([hook, "origin", "x"], input=line, env={**stub_env, "OLD_RC": "3"}, capture_output=True, text=True)
    assert stop.returncode == 3                        # its refusal stops the push


# Contabo's Agents-Core .git/hooks/pre-push (CTO Main, 2026-10-15), logic unchanged, held sha parameterised.
HELD_COMMIT_HOOK = """#!/bin/sh
held=%s
git cat-file -e "$held^{commit}" 2>/dev/null || exit 0
while read local_ref local_sha remote_ref remote_sha; do
  case "$local_sha" in 0000000000000000000000000000000000000000) continue ;; esac
  if git merge-base --is-ancestor "$held" "$local_sha" 2>/dev/null; then
    echo "pre-push: REFUSED - $local_ref contains held commit $held" >&2
    exit 1
  fi
done
exit 0
"""


def test_the_contabo_held_commit_hook_keeps_refusing_after_install(tmp_path, stub_env):
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], env=stub_env, check=True)
    repo = make_repo(tmp_path / "work", "r", stub_env)
    git(repo, "remote", "add", "origin", str(remote), env=stub_env)
    assert commit(repo, "a.txt", "a\n", stub_env).returncode == 0
    before_held = git(repo, "rev-parse", "HEAD", env=stub_env).stdout.strip()
    assert commit(repo, "held.txt", "h\n", stub_env).returncode == 0
    held = git(repo, "rev-parse", "HEAD", env=stub_env).stdout.strip()
    assert commit(repo, "later.txt", "l\n", stub_env).returncode == 0
    (hooks(repo) / "pre-push").write_text(HELD_COMMIT_HOOK % held)
    (hooks(repo) / "pre-push").chmod(0o755)
    assert lg(stub_env, "--install", tmp_path / "work").returncode == 0
    refused = git(repo, "push", "origin", "main", env=stub_env, check=False)
    assert refused.returncode != 0 and f"contains held commit {held}" in refused.stderr
    assert git(repo, "push", "-q", "origin", f"{before_held}:refs/heads/ok", env=stub_env, check=False).returncode == 0


def test_d_installing_twice_changes_nothing(tmp_path, stub_env):
    plain = make_repo(tmp_path, "plain", stub_env)
    chained = make_repo(tmp_path, "chained", stub_env)
    (hooks(chained) / "pre-push").write_text("#!/bin/sh\nexit 0\n")
    (hooks(chained) / "pre-push").chmod(0o755)
    assert lg(stub_env, "--install", tmp_path).returncode == 0
    before = {r.name: snapshot(hooks(r)) for r in (plain, chained)}
    second = lg(stub_env, "--install", tmp_path)
    assert second.returncode == 0
    assert second.stdout.count("pre-commit=unchanged") == 2 and second.stdout.count("pre-push=unchanged") == 2
    assert {r.name: snapshot(hooks(r)) for r in (plain, chained)} == before  # bytes, names AND mtimes
    assert sorted(p.name for p in hooks(chained).glob("pre-push*") if p.suffix != ".sample") == ["pre-push", "pre-push.local"]


@needs_gitleaks
def test_e_a_pushed_range_holding_the_key_makes_pre_push_exit_non_zero(tmp_path, env):
    repo = make_repo(tmp_path, "r", env)
    assert lg(env, "--install", tmp_path).returncode == 0
    assert commit(repo, "a.txt", "clean\n", env).returncode == 0
    clean_sha = git(repo, "rev-parse", "HEAD", env=env).stdout.strip()
    assert commit(repo, "leak.txt", f"token = {fake_key()}\n", env, "--no-verify").returncode == 0
    leaky_sha = git(repo, "rev-parse", "HEAD", env=env).stdout.strip()
    hook = str(hooks(repo) / "pre-push")

    def push(local, remote):
        line = f"refs/heads/main {local} refs/heads/main {remote}\n"
        return subprocess.run([hook, "origin", "x"], input=line, cwd=repo, env=env, capture_output=True, text=True)

    bad = push(leaky_sha, clean_sha)                   # <remote_sha>..<local_sha> holds the key
    assert bad.returncode != 0 and "push BLOCKED" in bad.stderr
    assert fake_key() not in bad.stdout + bad.stderr
    assert push(leaky_sha, "0" * 40).returncode != 0   # new branch: everything not on a remote yet
    assert push(clean_sha, "0" * 40).returncode == 0   # new branch, clean history
    assert push(clean_sha, clean_sha).returncode == 0  # empty range
    assert push("0" * 40, clean_sha).returncode == 0   # deleting a ref scans nothing


@needs_gitleaks
def test_a_real_git_push_to_a_local_remote_is_stopped_by_the_hook(tmp_path, env):
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], env=env, check=True)
    repo = make_repo(tmp_path / "work", "r", env)
    git(repo, "remote", "add", "origin", str(remote), env=env)
    assert lg(env, "--install", tmp_path / "work").returncode == 0
    assert commit(repo, "a.txt", "clean\n", env).returncode == 0
    assert git(repo, "push", "-q", "origin", "main", env=env, check=False).returncode == 0   # first push = new branch
    assert commit(repo, "leak.txt", f"token = {fake_key()}\n", env, "--no-verify").returncode == 0
    stopped = git(repo, "push", "origin", "main", env=env, check=False)
    assert stopped.returncode != 0 and "push BLOCKED" in stopped.stderr
    assert git(remote, "rev-parse", "main", env=env).stdout == git(repo, "rev-parse", "HEAD~1", env=env).stdout  # remote untouched
    new_branch = git(repo, "push", "origin", "main:fresh", env=env, check=False)               # new remote branch: scans unpushed
    assert new_branch.returncode != 0


# ---------------------------------------------------------------------------- the rest of the contract

def test_check_reports_each_repo_and_exits_1_until_every_repo_has_both_guards(tmp_path, stub_env):
    make_repo(tmp_path, "one", stub_env)
    make_repo(tmp_path, "two", stub_env)
    before = lg(stub_env, "--check", tmp_path)
    assert before.returncode == 1
    lines = [l for l in before.stdout.splitlines() if not l.startswith("#")]
    assert len(lines) == 2 and all("pre-commit=no\tpre-push=no\tgitleaks=yes" in l for l in lines)
    assert lg(stub_env, "--install", tmp_path).returncode == 0
    after = lg(stub_env, "--check", tmp_path)
    assert after.returncode == 0
    assert after.stdout.count("pre-commit=yes\tpre-push=yes\tgitleaks=yes") == 2
    assert "repos=2 without-guard=0" in after.stdout


def test_check_is_read_only(tmp_path, stub_env):
    repo = make_repo(tmp_path, "r", stub_env)
    before = snapshot(hooks(repo))
    lg(stub_env, "--check", tmp_path)
    lg(stub_env, "--install", "--dry-run", tmp_path)
    assert snapshot(hooks(repo)) == before


def test_dry_run_says_what_it_would_do(tmp_path, stub_env):
    make_repo(tmp_path, "r", stub_env)
    result = lg(stub_env, "--install", "--dry-run", tmp_path)
    assert result.returncode == 0
    assert "pre-commit=would-be-installed" in result.stdout and "dry-run" in result.stdout


def test_hostile_directory_names_and_skipped_directories(tmp_path, stub_env):
    odd = make_repo(tmp_path, "my repo (ไทย) #1", stub_env)
    make_repo(tmp_path, "node_modules/dep", stub_env)
    make_repo(tmp_path, "proj/.venv/lib", stub_env)
    make_repo(tmp_path, "worktrees/old", stub_env)
    result = lg(stub_env, "--install", tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.stdout.count("pre-commit=installed") == 1
    assert (hooks(odd) / "pre-push").exists()
    assert not (hooks(tmp_path / "node_modules" / "dep") / "pre-push").exists()
    assert lg(stub_env, "--check", tmp_path).returncode == 0


def test_a_symlink_hub_finds_the_repo_and_a_symlink_loop_is_not_followed(tmp_path, stub_env):
    real = make_repo(tmp_path / "elsewhere", "real", stub_env)
    hub = tmp_path / "hub"
    hub.mkdir()
    (hub / "link").symlink_to(real)            # hub/link -> a repo outside the root: one repo, found
    (hub / "up").symlink_to(tmp_path)          # a link back to a parent (like wine's z: -> /): never walked
    result = lg(stub_env, "--check", hub)
    assert [l.split("\t")[0] for l in result.stdout.splitlines() if not l.startswith("#")] == [str(real.resolve())]
    assert lg(stub_env, "--install", hub).returncode == 0 and (hooks(real) / "pre-push").exists()
    assert lg(stub_env, "--check", hub, real.parent).stdout.count(str(real.resolve())) == 1  # de-duplicated


@pytest.mark.parametrize("which", ["hooks", "git-dir"])
def test_a_dir_other_accounts_can_write_is_skipped_and_left_untouched(tmp_path, stub_env, which):
    """The installer may run as root over a repo another account can write to: a planted symlink at a
    temp name would make root write or chmod whatever it points at. Such a repo is skipped, not written."""
    repo = make_repo(tmp_path, "r", stub_env)
    victim = tmp_path / "victim.txt"
    victim.write_text("not a hook\n")
    victim.chmod(0o600)
    (hooks(repo) / "pre-push.new.1234").symlink_to(victim)        # the attack: a planted link
    before = snapshot(hooks(repo))
    loose = hooks(repo) if which == "hooks" else repo / ".git"
    loose.chmod(0o777)
    result = lg(stub_env, "--install", tmp_path)
    assert result.returncode == 1, result.stdout
    assert "pre-commit=skipped-not-owned\tpre-push=skipped-not-owned" in result.stdout
    assert "skipped-not-owned=1" in result.stdout
    assert victim.read_text() == "not a hook\n" and stat.S_IMODE(victim.stat().st_mode) == 0o600
    assert not (hooks(repo) / "pre-push").exists() and not (hooks(repo) / "pre-commit").exists()
    assert {k: v[0] for k, v in snapshot(hooks(repo)).items()} == {k: v[0] for k, v in before.items()}  # nothing added or rewritten
    checked = lg(stub_env, "--check", tmp_path)
    assert checked.returncode == 1 and "\tskipped-not-owned" in checked.stdout   # --check says the same word
    loose.chmod(0o755)
    assert lg(stub_env, "--install", tmp_path).returncode == 0                  # fixed perms: installs normally


needs_root_and_nobody = pytest.mark.skipif(
    os.geteuid() != 0 or not any(u.pw_name == "nobody" for u in pwd.getpwall()),
    reason="needs root (to chown) and a 'nobody' account",
)


@needs_root_and_nobody
def test_a_repo_owned_by_another_existing_account_is_skipped(tmp_path, stub_env):
    repo = make_repo(tmp_path, "r", stub_env)
    nobody = pwd.getpwnam("nobody").pw_uid
    for p in (repo / ".git", hooks(repo)):
        os.chown(p, nobody, -1)                                    # 0755, so only the owner test can catch it
    before = snapshot(hooks(repo))
    result = lg(stub_env, "--install", tmp_path)
    assert result.returncode == 1 and "pre-push=skipped-not-owned" in result.stdout
    assert snapshot(hooks(repo)) == before


@needs_root_and_nobody
def test_an_owner_uid_with_no_account_counts_as_safe(tmp_path, stub_env):
    """The Mac's uid 501 on Contabo: no account can log in as it, so nobody else can write there."""
    repo = make_repo(tmp_path, "r", stub_env)
    uid = 59999
    assert all(u.pw_uid != uid for u in pwd.getpwall())
    for p in (repo / ".git", hooks(repo)):
        os.chown(p, uid, -1)
    # git refuses a repo owned by another uid unless told otherwise; Contabo's global config says safe.directory=*
    trusting = {**stub_env, "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "safe.directory", "GIT_CONFIG_VALUE_0": "*"}
    result = lg(trusting, "--install", tmp_path)
    assert result.returncode == 0, result.stdout
    assert "pre-push=installed" in result.stdout and (hooks(repo) / "pre-push").exists()


def test_a_linked_worktree_is_not_a_repo_of_its_own(tmp_path, stub_env):
    repo = make_repo(tmp_path, "main-repo", stub_env)
    assert commit(repo, "a.txt", "x\n", stub_env).returncode == 0
    git(repo, "worktree", "add", "-q", str(tmp_path / "linked"), "-b", "side", env=stub_env)
    result = lg(stub_env, "--check", tmp_path)
    assert [l.split("\t")[0] for l in result.stdout.splitlines() if not l.startswith("#")] == [str(repo.resolve())]


def test_core_hooks_path_is_respected(tmp_path, stub_env):
    repo = make_repo(tmp_path, "r", stub_env)
    git(repo, "config", "core.hooksPath", ".custom-hooks", env=stub_env)
    result = lg(stub_env, "--install", tmp_path)
    assert result.returncode == 0 and "hooksPath=custom" in result.stdout
    assert (repo / ".custom-hooks" / "pre-commit").exists() and (repo / ".custom-hooks" / "pre-push").exists()
    assert not (hooks(repo) / "pre-push").exists()
    assert lg(stub_env, "--check", tmp_path).returncode == 0


def test_a_pre_commit_that_already_runs_gitleaks_is_left_alone(tmp_path, stub_env):
    repo = make_repo(tmp_path, "r", stub_env)
    guarded = "#!/bin/sh\ngitleaks protect --staged --redact --no-banner || exit 1\nexit 0\n"
    (hooks(repo) / "pre-commit").write_text(guarded)
    (hooks(repo) / "pre-commit").chmod(0o755)
    result = lg(stub_env, "--install", tmp_path)
    assert "pre-commit=kept-already-guarded" in result.stdout and "pre-push=installed" in result.stdout
    assert (hooks(repo) / "pre-commit").read_text() == guarded
    assert not (hooks(repo) / "pre-commit.local").exists()


def test_a_commented_out_gitleaks_line_is_not_a_guard(tmp_path, stub_env):
    repo = make_repo(tmp_path, "r", stub_env)
    (hooks(repo) / "pre-commit").write_text("#!/bin/sh\n# gitleaks protect --staged\nexit 0\n")
    (hooks(repo) / "pre-commit").chmod(0o755)
    assert lg(stub_env, "--check", tmp_path).stdout.count("pre-commit=no") == 1


def test_a_hook_without_the_exec_bit_is_not_a_guard(tmp_path, stub_env):
    repo = make_repo(tmp_path, "r", stub_env)
    assert lg(stub_env, "--install", tmp_path).returncode == 0
    mode = (hooks(repo) / "pre-push").stat().st_mode
    (hooks(repo) / "pre-push").chmod(mode & ~(stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))
    result = lg(stub_env, "--check", tmp_path)
    assert result.returncode == 1 and "pre-push=no" in result.stdout


def test_refuses_to_overwrite_an_existing_local_hook(tmp_path, stub_env):
    repo = make_repo(tmp_path, "r", stub_env)
    for name in ("pre-push", "pre-push.local"):
        (hooks(repo) / name).write_text(f"#!/bin/sh\n# {name}\nexit 0\n")
    result = lg(stub_env, "--install", tmp_path)
    assert result.returncode == 1 and "ERROR(pre-push.local-exists)" in result.stdout
    assert "# pre-push.local" in (hooks(repo) / "pre-push.local").read_text()
    assert "# pre-push\n" in (hooks(repo) / "pre-push").read_text()  # neither file was touched


def test_install_git_hooks_keeps_working_after_leak_guards(tmp_path, stub_env):
    """scripts/install-git-hooks.sh must append its stanzas to pre-commit.local, not after our wrapper's exit."""
    repo = make_repo(tmp_path, "r", stub_env)
    assert lg(stub_env, "--install", tmp_path).returncode == 0
    wrapper = (hooks(repo) / "pre-commit").read_bytes()
    done = subprocess.run(["sh", str(INSTALL_GIT_HOOKS)], cwd=repo, env=stub_env, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    assert (hooks(repo) / "pre-commit").read_bytes() == wrapper
    assert "BEGIN media-guard" in (hooks(repo) / "pre-commit.local").read_text()
    assert lg(stub_env, "--install", tmp_path).stdout.count("pre-commit=unchanged") == 1


def test_missing_gitleaks_is_loud(tmp_path, env):
    bare = "/usr/bin:/bin"
    if shutil.which("gitleaks", path=bare):
        pytest.skip("gitleaks lives in /usr/bin or /bin here; cannot simulate a missing one")
    make_repo(tmp_path, "r", env)
    e = {**env, "PATH": bare}
    result = lg(e, "--install", tmp_path)
    assert result.returncode == 2 and "gitleaks is NOT on PATH" in result.stderr
    assert (tmp_path / "r" / ".git" / "hooks" / "pre-push").exists()  # hooks are still written
    assert lg({**e, "ALLOW_NO_GITLEAKS": "1"}, "--check", tmp_path).returncode == 0
    commit_out = commit(tmp_path / "r", "a.txt", "x\n", e)
    assert commit_out.returncode == 0 and "secret guard SKIPPED" in commit_out.stderr


def test_usage_errors(tmp_path, stub_env):
    assert lg(stub_env).returncode == 64
    assert lg(stub_env, "--check").returncode == 64                       # no default root
    assert lg(stub_env, "--check", tmp_path / "nope").returncode == 64
    assert lg(stub_env, "--dry-run", "--check", tmp_path).returncode == 64
