import importlib.util

def get_hook_module():
    spec = importlib.util.spec_from_file_location("hook_self_repo_guard", "scripts/hook-self-repo-guard.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def test_bash_targets_flags():
    mod = get_hook_module()

    assert mod.bash_targets("rm -f state/tasks.db") == ["state/tasks.db"]
    assert mod.bash_targets("rm -f lib/db.py") == ["lib/db.py"]

    assert mod.bash_targets("touch state/tasks.db") == ["state/tasks.db"]
    assert mod.bash_targets("touch lib/x.py") == ["lib/x.py"]

    assert mod.bash_targets("cp -f src.txt lib/x.py") == ["src.txt", "lib/x.py"]

    assert mod.bash_targets("sed -i -f script.sed lib/x.py") == ["lib/x.py"]

    assert mod.bash_targets("truncate -s 0 state/tasks.db") == ["state/tasks.db"]
