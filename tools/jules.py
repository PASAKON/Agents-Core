#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

BASE_URL = "https://jules.googleapis.com/v1alpha"
ROOT = Path(__file__).resolve().parent.parent
ALLOWLIST = ROOT / "config" / "jules.yaml"


def check_allowlist(repo: str, path: Path | None = None) -> str | None:
    """Refusal reason, or None when `repo` may be dispatched to (config/jules.yaml).

    The Jules GitHub app can SEE every repo; it may only be dispatched to a repo
    listed under `repos`, and never to one under `never` (CEO 2026-09-23).
    """
    import yaml
    path = path or ALLOWLIST            # read at call time so tests can point it elsewhere
    full = repo if "/" in repo else f"PASAKON/{repo}"
    cfg = yaml.safe_load(path.read_text()) or {}
    if full in (cfg.get("never") or []):
        return f"{full} is on the never-dispatch list in {path.name}"
    if full not in [r.get("repo") for r in (cfg.get("repos") or [])]:
        return f"{full} is not in {path.name} — add it there (a one-line PR) before dispatching"
    return None


# Activity keys that are metadata, not the activity's kind.
_META = {"name", "id", "createTime", "originator", "artifacts", "description"}

def get_api_key():
    env_file = os.environ.get("JULES_ENV_FILE", os.path.expanduser("~/.config/mooniex/jules.env"))
    try:
        with open(env_file, "r") as f:
            for line in f:
                if line.startswith("JULES_API_KEY="):
                    return line.strip().split("=", 1)[1]
    except FileNotFoundError:
        pass
    print("Error: JULES_API_KEY not found in " + env_file, file=sys.stderr)
    sys.exit(1)

def make_request(method, endpoint, data=None):
    url = f"{BASE_URL}{endpoint}"
    headers = {
        "X-Goog-Api-Key": get_api_key(),
        "Content-Type": "application/json"
    }
    
    req_data = None
    if data is not None:
        req_data = json.dumps(data).encode("utf-8")
        
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            if response.status in (200, 201):
                res_body = response.read().decode("utf-8")
                if res_body:
                    return json.loads(res_body)
                return None
            else:
                print(f"Error: HTTP {response.status}", file=sys.stderr)
                sys.exit(1)
    except urllib.error.HTTPError as e:
        print(f"Error: HTTP {e.code} - {e.read().decode('utf-8')}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: {e.reason}", file=sys.stderr)
        sys.exit(1)

def make_paginated_request(endpoint):
    results = []
    page_token = None
    
    while True:
        url = endpoint
        if page_token:
            if "?" in url:
                url += f"&pageToken={page_token}"
            else:
                url += f"?pageToken={page_token}"
                
        res = make_request("GET", url)
        if not res:
            break
            
        yield res
        
        page_token = res.get("nextPageToken")
        if not page_token:
            break

def main():
    parser = argparse.ArgumentParser(description="Jules API CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create subcommand
    create_parser = subparsers.add_parser("create", help="Create a new session")
    create_parser.add_argument("--repo", required=True, help="Repository name")
    create_parser.add_argument("--title", required=True, help="Title of the PR")
    create_parser.add_argument("--brief", required=True, help="Path to the brief file")
    create_parser.add_argument("--branch", default="main", help="Target branch (default: main)")

    # status subcommand
    status_parser = subparsers.add_parser("status", help="Get status of a session")
    status_parser.add_argument("id", help="Session ID")

    # diff subcommand
    diff_parser = subparsers.add_parser("diff", help="Get the last git patch of a session")
    diff_parser.add_argument("id", help="Session ID")
    diff_parser.add_argument("--out", help="Output file for the patch")

    # report subcommand
    report_parser = subparsers.add_parser("report", help="Report activities of a session")
    report_parser.add_argument("id", help="Session ID")

    # gate subcommand
    gate_parser = subparsers.add_parser("gate", help="Gate a session based on diff allowed globs")
    gate_parser.add_argument("id", help="Session ID")
    gate_parser.add_argument("--allow", action="append", default=[], help="Allowed file glob (can be specified multiple times)")
    gate_parser.add_argument("--max-bytes", type=int, default=65536, help="Maximum patch size in bytes (default: 65536)")

    args = parser.parse_args()

    # Placeholders for subcommands
    if args.command == "create":
        try:
            with open(args.brief, "r") as f:
                brief_content = f.read()
        except FileNotFoundError:
            print(f"Error: brief file {args.brief} not found", file=sys.stderr)
            sys.exit(1)
            
        refusal = check_allowlist(args.repo)
        if refusal:
            print(f"Refused: {refusal}", file=sys.stderr)
            sys.exit(2)
        # Field names are the API's (Session schema in the v1alpha discovery doc):
        # the brief goes in `prompt`, the branch under githubRepoContext.
        data = {
            "prompt": brief_content,
            "title": args.title,
            "sourceContext": {
                "source": f"sources/github/PASAKON/{args.repo.split('/')[-1]}",
                "githubRepoContext": {"startingBranch": args.branch},
            },
            "automationMode": "AUTO_CREATE_PR",
            "requirePlanApproval": False,
        }
        
        
        res = make_request("POST", "/sessions", data=data)
        if res and "name" in res:
            session_id = res["name"].split("/")[-1]
            print(session_id)
        else:
            print(res)

    elif args.command == "status":
        res = make_request("GET", f"/sessions/{args.id}")
        state = res.get("state", "UNKNOWN")
        print(f"State: {state}")
        
        outputs = res.get("outputs", [])
        if outputs:
            for out in outputs:
                if "pullRequest" in out and "url" in out["pullRequest"]:
                    print(f"PR URL: {out['pullRequest']['url']}")
    elif args.command == "diff":
        last_patch = None
        for page in make_paginated_request(f"/sessions/{args.id}/activities"):
            activities = page.get("activities", [])
            for activity in activities:
                artifacts = activity.get("artifacts", [])
                for artifact in artifacts:
                    change_set = artifact.get("changeSet")
                    if change_set and "gitPatch" in change_set and "unidiffPatch" in change_set["gitPatch"]:
                        last_patch = change_set["gitPatch"]["unidiffPatch"]
        
        if last_patch:
            if args.out:
                with open(args.out, "w") as f:
                    f.write(last_patch)
            else:
                print(last_patch)
        else:
            print("No patch found", file=sys.stderr)
            sys.exit(1)

    elif args.command == "report":
        for page in make_paginated_request(f"/sessions/{args.id}/activities"):
            activities = page.get("activities", [])
            for activity in activities:
                # Real shape: one key names the kind, e.g. {"agentMessaged": {"agentMessage": "..."}},
                # {"progressUpdated": {"title": ..., "description": ...}}, {"sessionFailed": {"reason": ...}}.
                create_time = activity.get("createTime", "")
                kinds = [k for k in activity if k not in _META]
                kind = kinds[0] if kinds else ""
                body = activity.get(kind) if kind else None
                text = ""
                if isinstance(body, dict):
                    for field in ("agentMessage", "userMessage", "title", "reason", "description"):
                        if isinstance(body.get(field), str) and body[field]:
                            text = body[field]
                            break
                print(f"{create_time} {kind} {text}".rstrip())
    elif args.command == "gate":
        last_patch = None
        for page in make_paginated_request(f"/sessions/{args.id}/activities"):
            activities = page.get("activities", [])
            for activity in activities:
                artifacts = activity.get("artifacts", [])
                for artifact in artifacts:
                    change_set = artifact.get("changeSet")
                    if change_set and "gitPatch" in change_set and "unidiffPatch" in change_set["gitPatch"]:
                        last_patch = change_set["gitPatch"]["unidiffPatch"]
        
        if not last_patch:
            # Nothing changed, all good
            sys.exit(0)
            
        patch_bytes = len(last_patch.encode("utf-8"))
        if patch_bytes > args.max_bytes:
            print(f"Violation: Patch size {patch_bytes} exceeds max {args.max_bytes} bytes", file=sys.stderr)
            sys.exit(1)
            
        # Extract files from patch
        files_modified = set()
        for line in last_patch.splitlines():
            if line.startswith("+++ b/"):
                files_modified.add(line[6:])
            elif line.startswith("--- a/"):
                files_modified.add(line[6:])
                
        import fnmatch
        
        forbidden_patterns = [
            "*.log", 
            "patch_*", 
            "test_*.js", 
            "package.json", 
            "package-lock.json", 
            "*.lock", 
            "requirements*.txt"
        ]
        
        violations = []
        for file in files_modified:
            if file == "/dev/null":
                continue
                
            allowed = False
            for glob_pattern in args.allow:
                if fnmatch.fnmatchcase(file, glob_pattern):
                    allowed = True
                    break
            
            if not allowed:
                violations.append(f"Violation: File {file} not explicitly allowed")
                continue
                
            # Check forbidden
            is_forbidden = False
            
            # check patterns that apply anywhere
            for fp in ["*.log", "package.json", "package-lock.json", "*.lock", "requirements*.txt"]:
                if fnmatch.fnmatchcase(file, fp) or fnmatch.fnmatchcase(file, "*/" + fp):
                    is_forbidden = True
                    break
                    
            # check patterns that apply at repo root
            if not is_forbidden:
                for fp in ["patch_*", "test_*.js"]:
                    if fnmatch.fnmatchcase(file, fp) and "/" not in file:
                        is_forbidden = True
                        break
                        
            if is_forbidden and file not in args.allow:
                violations.append(f"Violation: File {file} matches forbidden pattern but is not explicitly allowed")
                
        if violations:
            for v in violations:
                print(v, file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()
