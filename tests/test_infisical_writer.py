"""Writer defaults and local refusal; all credential/network operations are fake."""
import io
import pytest
from tools import infisical_setup as tool


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(tool, "call", lambda *a, **k: pytest.fail("network call"))
    monkeypatch.setattr(tool, "read_cred", lambda *a: pytest.fail("credential read"))


def test_put_defaults_to_writer(monkeypatch):
    seen = []
    monkeypatch.setattr(tool, "Org", lambda identity: seen.append(identity))
    monkeypatch.setattr(tool, "cmd_put", lambda *a, **k: None)
    tool.main(["put", "Agents-Core", "prod", "TEST_API_KEY", "--stdin"])
    assert seen == [tool.WRITER]


@pytest.mark.parametrize("project", ["Org-Infra", "Org-Node", "Unlisted", "org-infra", "org-node"])
def test_put_refused_before_network(monkeypatch, project):
    monkeypatch.setattr(tool, "Org", lambda *a: pytest.fail("Org constructed"))
    with pytest.raises(SystemExit, match="refuses project"):
        tool.main(["put", project, "prod", "TEST_API_KEY", "--stdin", "--as", tool.WRITER])


@pytest.mark.parametrize("ttl", [86400, 86401, 0])
def test_save_writer(monkeypatch, ttl):
    saved = []
    monkeypatch.setattr(tool, "require_root", lambda: None)
    monkeypatch.setattr(tool.sys, "stdin", io.StringIO("fake-id\nfake-secret\n"))
    monkeypatch.setattr(tool, "login", lambda *a: ("fake", {}, ttl))
    monkeypatch.setattr(tool, "write_cred", lambda *a, **k: saved.append(a) or "fake-path")
    if ttl == 86400:
        tool.main(["save", tool.WRITER, "--stdin"])
        assert saved == [(tool.WRITER, "fake-id", "fake-secret")]
    else:
        with pytest.raises(SystemExit, match="TTL"):
            tool.main(["save", tool.WRITER, "--stdin"])
        assert saved == []


@pytest.mark.parametrize("source", ["projects: [Org-Infra]", "projects: [Org-Node]", "projects: [A, A]", "projects: []"])
def test_bad_manifest(monkeypatch, tmp_path, source):
    path = tmp_path / "writer.yaml"
    path.write_text(source)
    monkeypatch.setattr(tool, "WRITER_MANIFEST", str(path))
    with pytest.raises(SystemExit, match="manifest"):
        tool.writer_projects()


def test_missing_manifest(monkeypatch, tmp_path):
    monkeypatch.setattr(tool, "WRITER_MANIFEST", str(tmp_path / "absent.yaml"))
    with pytest.raises(SystemExit, match="manifest missing"):
        tool.writer_projects()


def test_missing_credentials_names_the_identity(monkeypatch):
    def no_cred(identity):
        raise FileNotFoundError(2, "No such file", f"/creds/{identity}.env")
    monkeypatch.setattr(tool, "Org", no_cred)
    with pytest.raises(SystemExit, match="save keyfetch-writer"):
        tool.main(["put", "Agents-Core", "prod", "TEST_API_KEY", "--stdin"])


def test_bedrock_allowed_without_static_project_table(monkeypatch):
    monkeypatch.setattr(tool, "PROJECTS", type(tool.PROJECTS)())
    tool.guard_writer_project("MoonieX-Bedrock")
