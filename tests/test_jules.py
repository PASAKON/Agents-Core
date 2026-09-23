import json
import os
import sys
import tempfile
import urllib.request
import pytest
from unittest.mock import patch, MagicMock

# Import the module under test
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
import tools.jules as jules

@pytest.fixture
def mock_urlopen():
    with patch("urllib.request.urlopen") as mock:
        yield mock

@pytest.fixture
def temp_env_file():
    fd, path = tempfile.mkstemp()
    with os.fdopen(fd, 'w') as f:
        f.write("JULES_API_KEY=testkey123\n")
    yield path
    os.remove(path)

@pytest.fixture
def mock_args(monkeypatch, temp_env_file):
    monkeypatch.setenv("JULES_ENV_FILE", temp_env_file)
    
def test_create(mock_urlopen, mock_args, tmp_path, capsys, monkeypatch):
    brief_file = tmp_path / "brief.txt"
    brief_file.write_text("Hello Brief")
    
    # Mock the API response
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps({"name": "sessions/sess123"}).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_resp
    
    # Run main
    monkeypatch.setattr("sys.argv", ["jules.py", "create", "--repo", "myrepo", "--title", "mytitle", "--brief", str(brief_file)])
    jules.main()
    
    # Check stdout
    captured = capsys.readouterr()
    assert "sess123" in captured.out
    
    # Verify request
    req = mock_urlopen.call_args[0][0]
    assert req.method == "POST"
    assert req.full_url == "https://jules.googleapis.com/v1alpha/sessions"
    assert req.headers["X-goog-api-key"] == "testkey123"
    
    body = json.loads(req.data.decode("utf-8"))
    assert body["sourceContext"]["source"] == "sources/github/PASAKON/myrepo"
    assert body["title"] == "mytitle"
    assert body["brief"] == "Hello Brief"

def test_status(mock_urlopen, mock_args, capsys, monkeypatch):
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps({
        "state": "COMPLETED",
        "outputs": [
            {"pullRequest": {"url": "https://github.com/PR/1"}}
        ]
    }).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_resp
    
    monkeypatch.setattr("sys.argv", ["jules.py", "status", "sess123"])
    jules.main()
    
    captured = capsys.readouterr()
    assert "State: COMPLETED" in captured.out
    assert "PR URL: https://github.com/PR/1" in captured.out
    
def test_diff_and_report(mock_urlopen, mock_args, capsys, monkeypatch):
    mock_resp = MagicMock()
    mock_resp.status = 200
    # Provide a single page of activities
    mock_resp.read.return_value = json.dumps({
        "activities": [
            {
                "createTime": "2023-01-01",
                "kind": "TEST",
                "message": {"text": "hello"},
                "artifacts": [
                    {"changeSet": {"gitPatch": {"unidiffPatch": "patch1"}}}
                ]
            },
            {
                "createTime": "2023-01-02",
                "kind": "TEST2",
                "message": {"text": "world"},
                "artifacts": [
                    {"changeSet": {"gitPatch": {"unidiffPatch": "patch2"}}}
                ]
            }
        ]
    }).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_resp
    
    monkeypatch.setattr("sys.argv", ["jules.py", "diff", "sess123"])
    jules.main()
    captured = capsys.readouterr()
    assert "patch2\n" in captured.out
    assert "patch1" not in captured.out
    
    # Test report
    mock_resp.read.return_value = json.dumps({
        "activities": [
            {
                "createTime": "2023-01-01",
                "kind": "TEST",
                "message": {"text": "hello"}
            }
        ]
    }).encode("utf-8")
    monkeypatch.setattr("sys.argv", ["jules.py", "report", "sess123"])
    jules.main()
    captured = capsys.readouterr()
    assert "2023-01-01 TEST hello\n" in captured.out

def test_gate_success(mock_urlopen, mock_args, capsys, monkeypatch):
    patch_content = "+++ b/src/app.py\n--- a/src/app.py\n+print('hello')"
    
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps({
        "activities": [
            {
                "artifacts": [
                    {"changeSet": {"gitPatch": {"unidiffPatch": patch_content}}}
                ]
            }
        ]
    }).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_resp
    
    monkeypatch.setattr("sys.argv", ["jules.py", "gate", "sess123", "--allow", "src/*.py"])
    jules.main()
    # Should exit 0
    
def test_gate_fail_forbidden(mock_urlopen, mock_args, capsys, monkeypatch):
    patch_content = "+++ b/package.json\n--- a/package.json"
    
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps({
        "activities": [
            {
                "artifacts": [
                    {"changeSet": {"gitPatch": {"unidiffPatch": patch_content}}}
                ]
            }
        ]
    }).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_resp
    
    monkeypatch.setattr("sys.argv", ["jules.py", "gate", "sess123", "--allow", "*.json"])
    with pytest.raises(SystemExit) as e:
        jules.main()
    assert e.value.code == 1
    
    captured = capsys.readouterr()
    assert "Violation" in captured.err

def test_gate_fail_max_bytes(mock_urlopen, mock_args, capsys, monkeypatch):
    patch_content = "+++ b/src/app.py\n" + ("x" * 100)
    
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps({
        "activities": [
            {
                "artifacts": [
                    {"changeSet": {"gitPatch": {"unidiffPatch": patch_content}}}
                ]
            }
        ]
    }).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_resp
    
    monkeypatch.setattr("sys.argv", ["jules.py", "gate", "sess123", "--allow", "src/*.py", "--max-bytes", "50"])
    with pytest.raises(SystemExit) as e:
        jules.main()
    assert e.value.code == 1
