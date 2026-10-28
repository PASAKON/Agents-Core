"""tools/secret_inventory.py — names-only credential inventory (HQSecurity M0, task-0a7c9dcc).

Every value below is a made-up fixture string. The one rule these tests guard above all: no value
(nor any slice of one) ever reaches the scanner's output or the report."""
from __future__ import annotations

import json
import os
import subprocess

import pytest

from tools import secret_inventory as si

# Fixture values: random-looking but fake. None of them contains the words the placeholder filter
# drops, so the scanner treats them as real credentials.
V_OR = "qz7Lm2Pv9Xc4Tn8Rw1Ks6Hd3Jf5Gb0Ya"          # strong, shared between two files
V_TG = "551122:QpWoEiRuTyAlSkDjFhGzXmCnVb12"        # strong
V_PW = "hunter2hunter"                               # weak (short + a password name)
V_PAT = "sbp_" + "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
V_DB = "redis://svc:Zx9Qw8Er7Ty6Ui5Op4@cache.internal:6379/0"
ALL_VALUES = (V_OR, V_TG, V_PW, V_PAT, V_DB, "Zx9Qw8Er7Ty6Ui5Op4")


def _tree(tmp_path):
    proj = tmp_path / "MoonieXHQ" / "Projects" / "MoonieX" / "ClaudeFlow"
    proj.mkdir(parents=True)
    (proj / ".env").write_text(
        "# comment\n"
        f"OPENROUTER_API_KEY={V_OR}\n"
        f"TELEGRAM_BOT_TOKEN='{V_TG}'\n"
        "PORT=3000\n"
        "TOKEN_TTL=86400\n"
        "FAL_KEY=your-fal-key-here\n"
        "SECRETARY_HOST=127.0.0.1:8080\n"
        f"DB_PASSWORD={V_PW}\n"
        f"DATABASE_URL={V_DB}\n")
    other = tmp_path / "MoonieXHQ" / "Projects" / "MoonieX" / "Option"
    other.mkdir(parents=True)
    (other / "prod.env").write_text(f"export OPENROUTER_API_KEY=\"{V_OR}\"\n")
    claude = other / ".claude"
    claude.mkdir()
    (claude / "settings.local.json").write_text(json.dumps(
        {"permissions": {"allow": [f"Bash(SUPABASE_ACCESS_TOKEN={V_PAT} npx supabase db push)"]}}, indent=2))
    arch = tmp_path / "MoonieXHQ" / "Archive" / "mooniex-vps" / "_env-bundle"
    arch.mkdir(parents=True)
    (arch / "claudeflow.env").write_text(f"OPENROUTER_API_KEY={V_OR}\n")
    (tmp_path / "MoonieXHQ" / "Projects" / "MoonieX" / "ClaudeFlow" / "server.key").write_text(
        "-----BEGIN PRIVATE KEY-----\nMIIEfakefakefake\n-----END PRIVATE KEY-----\n")
    (tmp_path / "MoonieXHQ" / "Projects" / "MoonieX" / "ClaudeFlow" / "cert.pem").write_text(
        "-----BEGIN CERTIFICATE-----\nMIIEnotsecret\n-----END CERTIFICATE-----\n")
    nm = proj / "node_modules" / "pkg"
    nm.mkdir(parents=True)
    (nm / ".env").write_text(f"OPENROUTER_API_KEY={V_OR}\n")
    return tmp_path / "MoonieXHQ"


def _assert_no_value(text: str) -> None:
    for v in ALL_VALUES:
        assert v not in text
        assert v[:8] not in text, "a value prefix leaked"


def test_scan_finds_names_and_hashes_never_values(tmp_path):
    root = _tree(tmp_path)
    out = si.scan([str(root)], "testhost")
    dump = json.dumps(out)
    _assert_no_value(dump)
    names = {(os.path.basename(f["path"]), r["name"]) for f in out["files"] for r in f["rows"]}
    assert (".env", "OPENROUTER_API_KEY") in names
    assert (".env", "TELEGRAM_BOT_TOKEN") in names
    assert (".env", "DB_PASSWORD") in names
    assert (".env", "DATABASE_URL") in names          # a URL with a password in it
    assert ("prod.env", "OPENROUTER_API_KEY") in names
    assert ("settings.local.json", "SUPABASE_ACCESS_TOKEN(inline)") in names
    # the same token on the same line is one row, not one per pattern that saw it
    assert ("settings.local.json", "SUPABASE_PAT(inline)") not in names
    assert ("server.key", "server.key") in names
    assert not any(n == "cert.pem" for n, _ in names)    # a public certificate is not a credential
    assert not any(n in ("PORT", "TOKEN_TTL", "FAL_KEY", "SECRETARY_HOST") for _, n in names)  # FAL_KEY is a placeholder
    assert not any("node_modules" in f["path"] for f in out["files"])
    row = next(r for f in out["files"] if f["path"].endswith("ClaudeFlow/.env")
               for r in f["rows"] if r["name"] == "OPENROUTER_API_KEY")
    assert row["hash12"] == si.hash12(V_OR) and len(row["hash12"]) == 12 and row["line"] == 2


def test_denied_paths_are_never_opened(tmp_path, monkeypatch):
    opened = []
    real_open = open

    def spy(path, *a, **k):
        opened.append(str(path))
        return real_open(path, *a, **k)

    real_os_open = os.open

    def os_spy(path, *a, **k):
        opened.append(str(path))
        return real_os_open(path, *a, **k)

    monkeypatch.setattr("builtins.open", spy)
    monkeypatch.setattr(si.os, "open", os_spy)
    monkeypatch.setattr(si, "DENY_POSIX", si.DENY_POSIX + (str(tmp_path / "etc-infisical"),))
    deny = tmp_path / "etc-infisical"
    deny.mkdir()
    (deny / "contabo.env").write_text("INFISICAL_UNIVERSAL_AUTH_CLIENT_" + "SECRET=" + "Q9" * 10 + "\n")
    out = si.scan([str(tmp_path)], "h")
    assert out["files"] == []
    assert not any("etc-infisical" in p for p in opened)
    for real in ("/etc/infisical/contabo.env", "/proc/1/environ", "/run/sompong-coo/org-db.url"):
        assert si.denied(real)


def _deny_dir(tmp_path, monkeypatch):
    deny = tmp_path / "etc-infisical"
    deny.mkdir()
    (deny / "contabo.env").write_text("INFISICAL_UNIVERSAL_AUTH_CLIENT_" + "SECRET=" + "Q9" * 10 + "\n")
    monkeypatch.setattr(si, "DENY_POSIX", si.DENY_POSIX + (str(deny),))
    return deny


def test_symlinked_file_into_a_denied_dir_is_not_read(tmp_path, monkeypatch):
    deny = _deny_dir(tmp_path, monkeypatch)
    home = tmp_path / "home" / "secretary"
    home.mkdir(parents=True)
    (home / ".env").symlink_to(deny / "contabo.env")          # planted by the account that owns home
    assert si.scan([str(home)], "h")["files"] == []
    assert si.scan_file(str(home / ".env"), ".env", "text") == []   # O_NOFOLLOW, even past the walk


def test_parent_dir_swapped_for_a_symlink_is_caught_after_open(tmp_path, monkeypatch):
    deny = _deny_dir(tmp_path, monkeypatch)
    (tmp_path / "proj").symlink_to(deny)                       # the swap a race would make after the walk
    assert si.scan_file(str(tmp_path / "proj" / "contabo.env"), "contabo.env", "text") == []


def test_fifo_named_like_a_key_file_does_not_hang_the_scan(tmp_path):
    os.mkfifo(tmp_path / ".env")
    assert si.scan([str(tmp_path)], "h")["files"] == []


def test_report_files_are_private(tmp_path):
    md = tmp_path / "out" / "inv.md"
    md.parent.mkdir()
    md.write_text("old\n")
    os.chmod(md, 0o644)
    si._write_private(str(md), "new\n")
    assert md.read_text() == "new\n" and (md.stat().st_mode & 0o777) == 0o600
    (tmp_path / "out" / "inv.json").symlink_to(tmp_path / "elsewhere.json")
    with pytest.raises(OSError):
        si._write_private(str(tmp_path / "out" / "inv.json"), "{}\n")
    assert not (tmp_path / "elsewhere.json").exists()


def test_symlinked_copy_counted_once(tmp_path):
    root = _tree(tmp_path)
    (tmp_path / "compat").symlink_to(root / "Projects" / "MoonieX" / "ClaudeFlow")
    out = si.scan([str(root), str(tmp_path / "compat")], "h")
    envs = [f for f in out["files"] if os.path.basename(f["path"]) == ".env"]
    assert len(envs) == 1


def _report(tmp_path):
    disk = si.scan([str(_tree(tmp_path))], "contabo")
    inf = {"source": "infisical", "identity": "contabo", "scanned_at": "t", "errors": [],
           "projects": [{"project": "MoonieX-ClaudeFlow", "env": "prod", "secrets": [
               {"name": "OPENROUTER_API_KEY", "path": "/", "hash12": si.hash12(V_OR), "weak": False,
                "tags": [], "scope": "ro", "expires": "2027-01-01", "updated_at": "2026-10-26T01:00:00Z"},
               {"name": "TELEGRAM_BOT_TOKEN", "path": "/", "hash12": si.hash12("a-newer-rotated-value-xyz"),
                "weak": False, "tags": [], "updated_at": "2026-10-20T00:00:00Z"},
               {"name": "RESEND_API_KEY", "path": "/", "hash12": si.hash12("only-in-the-vault-123456"),
                "weak": False, "tags": [], "updated_at": "2026-10-01T00:00:00Z"}]}]}
    gh = {"source": "github", "owner": "PASAKON", "scanned_at": "t", "repos": [
        {"repo": "Agents-Core", "visibility": "PUBLIC", "archived": False,
         "secrets": [{"name": "ANTHROPIC_API_KEY", "updated_at": "2026-09-01T00:00:00Z"}],
         "deploy_keys": [{"title": "winbox", "read_only": True, "created_at": "2026-09-30T00:00:00Z"}],
         "security_and_analysis": {"secret_scanning": {"status": "enabled"},
                                   "secret_scanning_push_protection": {"status": "disabled"}}}]}
    return si.build_report([disk, inf, gh], {"MoonieX-ClaudeFlow": "active"})


def test_report_status_rules(tmp_path):
    md, js = _report(tmp_path)
    by = {}
    for r in js["rows"]:
        by.setdefault((r["name"], r["where"].split(":")[0]), []).append(r)
    st = lambda name, host: sorted(r["status"] for r in by[(name, host)])  # noqa: E731
    # the same value in Infisical: both (two live disk copies + the vault row); the Archive copy: dead
    assert st("OPENROUTER_API_KEY", "contabo") == ["both", "both", "dead"]
    assert st("OPENROUTER_API_KEY", "infisical") == ["both"]
    assert st("TELEGRAM_BOT_TOKEN", "contabo") == ["dead"]          # name in Infisical, other value
    assert st("RESEND_API_KEY", "infisical") == ["infisical-only"]
    assert st("DB_PASSWORD", "contabo") == ["disk-only"]
    assert st("ANTHROPIC_API_KEY", "github") == ["github"]
    assert js["summary"]["contabo (Archive)"] == {"dead": 1}
    assert "| Agents-Core | " in md and "| disabled |" in md
    assert "## Archive copies" in md
    assert "### MoonieX-ClaudeFlow  ·  hq.yaml: active" in md


def test_report_never_holds_a_value_and_withholds_weak_hashes(tmp_path):
    md, js = _report(tmp_path)
    dump = md + json.dumps(js)
    _assert_no_value(dump)
    assert si.hash12(V_PW) not in dump                    # weak: a word-list attacker gets no oracle
    pw = next(r for r in js["rows"] if r["name"] == "DB_PASSWORD")
    assert pw["hash"].startswith("withheld=w")
    assert si.hash12(V_OR) in dump                        # strong: the hash stays for dedup
    assert "hash12" not in json.dumps(js["rows"])         # the raw hash field never leaves build_report


def test_provider_and_consumer_mapping():
    assert si.provider_of("OPENROUTER_API_KEY") == "openrouter"
    assert si.provider_of("SUPABASE_ACCESS_TOKEN(inline)") == "supabase"
    assert si.provider_of("ORG_DB_URL") == "postgres"
    assert si.consumer_of("contabo", "/opt/MoonieXHQ/Projects/MoonieX/ClaudeFlow/.env") == "MoonieX-ClaudeFlow"
    assert si.consumer_of("contabo", "/opt/MoonieXHQ/Agents/Core/mcp/.env") == "Agents-Core"
    assert si.consumer_of("contabo", "/etc/mooniex/secretary-secrets.env") == "etc-mooniex:secretary"
    assert si.consumer_of("winbox", r"C:\Users\passg\MoonieXHQ\Projects\MoonieX\Option\.env") == "MoonieX-Option"
    assert si.consumer_of("contabo", "/root/.config/gh/hosts.yml") == "profile:.config/gh(root)"
    assert si.consumer_of("contabo", "/home/secretary/.secretary.env.bak-zai") == "home:secretary"
    assert si.consumer_of("winbox", r"C:\Users\passg\mooniex\repo\MoonieX-Agents\.codex\config.toml") == "MoonieX-Agents"
    assert si.consumer_of("winbox", r"C:\Users\passg\cookierun-bot\.env") == "cookierun-bot"


def test_infisical_collector_hashes_and_drops_values():
    class _Org:
        def projects(self):
            return {"agents-core": {"id": "p1", "name": "Agents-Core"}}

        def environments(self, pid):
            return {"prod": "e1"}

        def get(self, route, **q):
            assert q["recursive"] == "true"
            return {"secrets": [{"secretKey": "ORG_DB_URL", "secretValue": V_DB, "secretPath": "/",
                                 "secretComment": "hub dsn", "tags": [{"slug": "leaked"}],
                                 "secretMetadata": [{"key": "expires", "value": "2027-10-26"}],
                                 "createdAt": "2026-10-02T00:00:00Z", "updatedAt": "2026-10-27T01:05:00Z"}]}

        def send(self, *a, **k):
            raise AssertionError("the inventory must never write to Infisical")

    out = si.infisical(org=_Org())
    _assert_no_value(json.dumps(out))
    s = out["projects"][0]["secrets"][0]
    assert s["hash12"] == si.hash12(V_DB) and s["tags"] == ["leaked"] and s["expires"] == "2027-10-26"
    assert s["updated_at"] == "2026-10-27T01:05:00Z" and s["comment"] is True


def test_github_collector_uses_names_only():
    calls = []

    def run(argv):
        calls.append(argv)
        joined = " ".join(argv)
        if argv[1] == "repo":
            stdout = json.dumps([{"name": "Agents-Core", "visibility": "PUBLIC", "isArchived": False,
                                  "isFork": False}])
        elif "actions/secrets" in joined:
            stdout = '{"name":"ANTHROPIC_API_KEY","created_at":"a","updated_at":"b"}\n'
        elif joined.endswith("/keys --paginate --jq .[] | {id, title, read_only, created_at, last_used}"):
            stdout = '{"id":1,"title":"winbox","read_only":true,"created_at":"c","last_used":null}\n'
        else:
            stdout = '{"secret_scanning":{"status":"enabled"}}'
        return subprocess.CompletedProcess(argv, 0, stdout, "")

    out = si.github("PASAKON", run=run, workers=1)
    repo = out["repos"][0]
    assert repo["secrets"][0]["name"] == "ANTHROPIC_API_KEY"
    assert repo["deploy_keys"][0]["title"] == "winbox"
    assert all(a[0] == "gh" and a[1] in ("repo", "api") for a in calls)
    assert not any(m in " ".join(a) for a in calls for m in ("-X", "--method", "DELETE", "PUT", "POST"))


def test_parse_text_formats():
    rows = si.parse_text('stripe:\n  secret_key: "' + V_TG + '"\n  publishable: pk\n', "config.yaml")
    assert [(r["name"], r["line"]) for r in rows] == [("secret_key", 2)]
    rows = si.parse_text(f'[db]\npassword = "{V_OR}"\nport = 5432\n', "config.toml")
    assert [r["name"] for r in rows] == ["password"]
    rows = si.parse_text(f'{{"env": {{"GITHUB_TOKEN": "{V_OR}", "MAX_TOKENS": "4096"}}}}', "settings.json")
    assert [r["name"] for r in rows] == ["GITHUB_TOKEN"]
    assert si.parse_text("API_KEY=${API_KEY}\nSECRET=changeme\nTOKEN=<token>\n", ".env") == []


@pytest.mark.parametrize("name,value,weak", [("DB_PASSWORD", V_OR, True), ("API_KEY", "short-value", True),
                                             ("OPENROUTER_API_KEY", V_OR, False)])
def test_weak_rule(name, value, weak):
    assert si.is_weak(name, value) is weak
