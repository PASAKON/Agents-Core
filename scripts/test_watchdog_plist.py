import plistlib
import os

def test_watchdog_plist_environment_variables():
    plist_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "scripts",
        "com.mooniex.agents-watchdog.plist"
    )
    with open(plist_path, "rb") as f:
        # Expat XML parser fails on "--" inside comments. 
        # So we do a quick replace before parsing.
        content = f.read()
        fixed_content = content.replace(b"--loop", b"&#x2D;&#x2D;loop")
        data = plistlib.loads(fixed_content)

    assert "EnvironmentVariables" in data
    env_vars = data["EnvironmentVariables"]

    assert "PATH" in env_vars
    path_val = env_vars["PATH"]
    assert path_val.startswith("/opt/homebrew/bin:/usr/local/bin:")
    assert "/usr/bin:/bin" in path_val

    assert "ORG_WATCHDOG_BRANCH_POLL" in env_vars
    assert env_vars["ORG_WATCHDOG_BRANCH_POLL"] == "0"
