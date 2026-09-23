import argparse
import json
import os
import sys
import time
from pathlib import Path

# Adjust path to import tools.storage_policy if run as script
try:
    import tools.storage_policy as sp
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import tools.storage_policy as sp

def get_blocks(st):
    return getattr(st, 'st_blocks', 0) * 512

def scan(roots, policy, home=None, size_never=False, now=None):
    if home is None:
        home = Path.home()
    if now is None:
        now = time.time()

    seen_inodes = set()
    errors = [0]

    tiers_total = {"HOT": 0, "REBUILD": 0, "COLD": 0, "NEVER": 0 if size_never else None, "UNCLASSIFIED": 0}
    top_entries = {"HOT": [], "REBUILD": [], "COLD": [], "NEVER": [], "UNCLASSIFIED": []}

    hot_by_top = {}
    unclass_by_top = {}

    def size_tree(path_str):
        total = 0
        dirs = [path_str]
        while dirs:
            d = dirs.pop()
            try:
                with os.scandir(d) as it:
                    for entry in it:
                        try:
                            if entry.is_symlink():
                                continue
                            st = entry.stat(follow_symlinks=False)
                            key = (st.st_dev, st.st_ino)
                            if key not in seen_inodes:
                                seen_inodes.add(key)
                                total += get_blocks(st)
                                if entry.is_dir(follow_symlinks=False):
                                    dirs.append(entry.path)
                        except (PermissionError, FileNotFoundError, OSError):
                            errors[0] += 1
            except (PermissionError, FileNotFoundError, OSError):
                errors[0] += 1
        return total

    def process_entry(entry_path, is_dir, st, top_level_path):
        age_days = None
        if not is_dir:
            age_days = (now - st.st_mtime) / (24 * 3600)

        tier = sp.classify(entry_path, policy, home=home, age_days=age_days)
        if not tier:
            tier = "UNCLASSIFIED"

        key = (st.st_dev, st.st_ino)
        already_seen = key in seen_inodes
        if not already_seen:
            seen_inodes.add(key)

        entry_size = 0 if already_seen else get_blocks(st)

        if is_dir:
            if tier in ("REBUILD", "COLD", "NEVER"):
                tree_size = 0
                if tier == "NEVER" and not size_never:
                    pass
                else:
                    tree_size = size_tree(entry_path)

                total_size = entry_size + tree_size
                if tier != "NEVER" or size_never:
                    tiers_total[tier] += total_size
                top_entries[tier].append({"path": entry_path, "bytes": total_size if (tier != "NEVER" or size_never) else None})
            else:
                if tier != "NEVER" or size_never:
                    tiers_total[tier] += entry_size

                if top_level_path:
                    if tier == "HOT":
                        hot_by_top[top_level_path] = hot_by_top.get(top_level_path, 0) + entry_size
                    else:
                        unclass_by_top[top_level_path] = unclass_by_top.get(top_level_path, 0) + entry_size

                try:
                    with os.scandir(entry_path) as it:
                        for child in it:
                            try:
                                if child.is_symlink():
                                    continue
                                child_st = child.stat(follow_symlinks=False)
                                child_top = top_level_path if top_level_path else child.path
                                process_entry(child.path, child.is_dir(follow_symlinks=False), child_st, child_top)
                            except (PermissionError, FileNotFoundError, OSError):
                                errors[0] += 1
                except (PermissionError, FileNotFoundError, OSError):
                    errors[0] += 1
        else:
            if tier != "NEVER" or size_never:
                tiers_total[tier] += entry_size

            if tier in ("REBUILD", "COLD", "NEVER"):
                top_entries[tier].append({"path": entry_path, "bytes": entry_size if (tier != "NEVER" or size_never) else None})
            else:
                if top_level_path:
                    if tier == "HOT":
                        hot_by_top[top_level_path] = hot_by_top.get(top_level_path, 0) + entry_size
                    else:
                        unclass_by_top[top_level_path] = unclass_by_top.get(top_level_path, 0) + entry_size

    start_t = time.time()

    roots = [str(r) for r in roots]

    for root in roots:
        try:
            root_st = os.stat(root, follow_symlinks=False)
        except (PermissionError, FileNotFoundError, OSError):
            errors[0] += 1
            continue

        if os.path.islink(root):
            continue

        if os.path.isdir(root):
            tier = sp.classify(root, policy, home=home, age_days=None) or "UNCLASSIFIED"
            if tier in ("REBUILD", "COLD", "NEVER"):
                process_entry(root, True, root_st, root)
                continue

            root_key = (root_st.st_dev, root_st.st_ino)
            if root_key not in seen_inodes:
                seen_inodes.add(root_key)
                root_size = get_blocks(root_st)
                if tier != "NEVER" or size_never:
                    tiers_total[tier] += root_size

            try:
                with os.scandir(root) as it:
                    for child in it:
                        try:
                            if child.is_symlink():
                                continue
                            child_st = child.stat(follow_symlinks=False)
                            process_entry(child.path, child.is_dir(follow_symlinks=False), child_st, child.path)
                        except (PermissionError, FileNotFoundError, OSError):
                            errors[0] += 1
            except (PermissionError, FileNotFoundError, OSError):
                errors[0] += 1
        else:
            process_entry(root, False, root_st, root)

    for p, b in hot_by_top.items():
        if b > 0:
            top_entries["HOT"].append({"path": p, "bytes": b})

    for p, b in unclass_by_top.items():
        if b > 0:
            top_entries["UNCLASSIFIED"].append({"path": p, "bytes": b})

    for tier in top_entries:
        if tier == "NEVER" and not size_never:
            top_entries[tier].sort(key=lambda x: x["path"])
        else:
            top_entries[tier].sort(key=lambda x: x["bytes"], reverse=True)
        top_entries[tier] = top_entries[tier][:10]

    elapsed = time.time() - start_t

    return {
        "roots": roots,
        "tiers": tiers_total,
        "top": top_entries,
        "errors": errors[0],
        "elapsed_s": elapsed
    }

def main():
    parser = argparse.ArgumentParser(description="Scan storage and classify by tier.")
    parser.add_argument("--root", action="append", help="Root directories to scan (default: home)")
    parser.add_argument("--size-never", action="store_true", help="Size NEVER directories (slow)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    default_policy = str(Path(__file__).resolve().parent.parent / "config" / "storage-policy.yaml")
    parser.add_argument("--policy", default=default_policy, help="Path to storage-policy.yaml")

    args = parser.parse_args()

    try:
        policy = sp.load(args.policy)
    except sp.PolicyError as e:
        print(f"Policy error: {e}", file=sys.stderr)
        sys.exit(1)

    roots = args.root if args.root else [str(Path.home())]

    result = scan(roots, policy, size_never=args.size_never)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Scan complete in {result['elapsed_s']:.1f}s. Errors: {result['errors']}\n")

        for tier in ["HOT", "REBUILD", "COLD", "NEVER", "UNCLASSIFIED"]:
            total = result["tiers"][tier]

            if total is None:
                print(f"--- {tier}: null ---")
            else:
                gb = total / (1024 ** 3)
                print(f"--- {tier}: {gb:.1f} GB ---")

            for entry in result["top"][tier]:
                if entry["bytes"] is None:
                    print(f"  - {entry['path']}")
                else:
                    egb = entry["bytes"] / (1024 ** 3)
                    print(f"  {egb:5.1f} GB  {entry['path']}")
            print()

if __name__ == "__main__":
    main()
