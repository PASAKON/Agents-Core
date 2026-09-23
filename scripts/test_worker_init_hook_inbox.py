import json
from pathlib import Path
from runners import worker_init

def test_foreign_worktree_hook_inbox(tmp_path):
    worktree = str(tmp_path)
    role = "developer"
    worker_init._write_dev_settings(worktree, role)
    
    settings_file = tmp_path / ".claude" / "settings.local.json"
    assert settings_file.exists()
    
    with open(settings_file, "r") as f:
        cfg = json.load(f)
        
    hooks = cfg.get("hooks", {})
    assert "UserPromptSubmit" in hooks
    
    ups_hooks = hooks["UserPromptSubmit"]
    
    found = False
    expected_script = str(worker_init.ROOT / "scripts" / "hook-inbox.py")
    
    for h in ups_hooks:
        if "hooks" in h:
            for subh in h["hooks"]:
                if subh.get("type") == "command" and expected_script in subh.get("command", ""):
                    found = True
        elif h.get("type") == "command" and expected_script in h.get("command", ""):
            found = True
            
    assert found, "hook-inbox.py UserPromptSubmit hook is missing or does not use absolute path"
