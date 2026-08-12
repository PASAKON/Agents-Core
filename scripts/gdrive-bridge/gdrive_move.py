#!/usr/bin/env python3
"""CLI client for the MoonieX Google Drive filing bridge (Apps Script web app).

Config: ~/.config/mooniex/gdrive-bridge.json = {"url": "<web app /exec URL>", "token": "<secret>"}

Usage:
  gdrive_move.py move <fileId> <newParentId>
  gdrive_move.py rename <fileId> <newName>
  gdrive_move.py trash <fileId>
  gdrive_move.py untrash <fileId>
  gdrive_move.py create_folder <name> [parentId]
  gdrive_move.py list <folderId>
  gdrive_move.py create_file <name> <parentId> [content]
  gdrive_move.py create_doc <name> <parentId>
  gdrive_move.py read_file <fileId>
  gdrive_move.py append_log <fileId> <line> [line ...]
"""
import json
import os
import sys
import urllib.request

CONFIG_PATH = os.path.expanduser("~/.config/mooniex/gdrive-bridge.json")


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def call(action, **params):
    cfg = load_config()
    payload = {"token": cfg["token"], "action": action, **params}
    req = urllib.request.Request(
        cfg["url"],
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read())


def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    action = sys.argv[1]
    args = sys.argv[2:]

    if action == "move":
        file_id, new_parent_id = args
        result = call("move", fileId=file_id, newParentId=new_parent_id)
    elif action == "rename":
        file_id, new_name = args
        result = call("rename", fileId=file_id, newName=new_name)
    elif action == "trash":
        (file_id,) = args
        result = call("trash", fileId=file_id)
    elif action == "untrash":
        (file_id,) = args
        result = call("untrash", fileId=file_id)
    elif action == "create_folder":
        name = args[0]
        parent_id = args[1] if len(args) > 1 else None
        result = call("create_folder", name=name, parentId=parent_id)
    elif action == "list":
        (folder_id,) = args
        result = call("list", folderId=folder_id)
    elif action == "create_file":
        name, parent_id = args[0], args[1]
        content = args[2] if len(args) > 2 else ""
        result = call("create_file", name=name, parentId=parent_id, content=content)
    elif action == "create_doc":
        name, parent_id = args[0], args[1]
        content = args[2] if len(args) > 2 else ""
        result = call("create_doc", name=name, parentId=parent_id, content=content)
    elif action == "read_file":
        (file_id,) = args
        result = call("read_file", fileId=file_id)
    elif action == "append_log":
        file_id, lines = args[0], args[1:]
        if not lines:
            print("append_log needs at least one line", file=sys.stderr)
            sys.exit(1)
        result = call("append_log", fileId=file_id, lines=list(lines))
    else:
        print(f"unknown action: {action}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
