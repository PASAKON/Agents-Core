"""Live mailbox routing shared by the portfolio collector and watch."""
import os
import re
from pathlib import Path

from lib import safe_file

ROOT = Path(__file__).resolve().parent.parent
BOX = re.compile(r"([a-z_]{2,20})-([A-Za-z0-9][A-Za-z0-9-]{0,63})")


def _lanes() -> tuple[str, ...]:
    from lib.roles import c_level_roles
    return tuple(c_level_roles())


def live_boxes() -> set[str]:
    from lib import db, portfolio
    with db.get_conn() as conn:
        if isinstance(conn, db._SnapshotConnection):
            raise RuntimeError("stale hub")
        rows = portfolio._live_by_sid(conn).values()
        return {f"{r['role']}-{r['sid']}" for r in rows
                if not r["stale"] and r.get("status") in ("running", "idle")
                and r["role"] in ("project_head", *_lanes())
                and BOX.fullmatch(f"{r['role']}-{r['sid']}")}


def lane_box(lane: str, live: set[str]) -> str | None:
    if lane not in _lanes():
        return None
    try:
        sid = safe_file.read_text(ROOT / "state" / "locks" / f"{lane}-active").strip()
    except OSError:
        sid = ""
    box = sid if sid.startswith(f"{lane}-") else f"{lane}-{sid}"
    if box in live:
        return box
    lane_live = sorted(b for b in live if b.startswith(f"{lane}-"))
    # The hub can list the lane's session under another id than its box (live 31 Oct: CTO Main's pointer and tmux
    # session say "fresh", the hub row says f69c4825, and a letter to cto-f69c4825 is never read). The lane's own
    # pointer wins while the lane is live and that box's inbox is a real folder.
    if lane_live and sid and BOX.fullmatch(box) and _inbox_dir(box):
        return box
    return next(iter(lane_live), None)


def _inbox_dir(box: str) -> bool:
    import stat
    from lib import mailbox
    try:
        return stat.S_ISDIR(os.lstat(Path(mailbox.INBOX_ROOT) / box).st_mode)
    except OSError:
        return False


def target(project: dict, live: set[str]) -> tuple[str | None, str]:
    from lib import portfolio
    try:
        box = "project_head-" + portfolio.ph_sid(project.get("ph_session"))
    except portfolio.PortfolioError:
        box = ""
    if box in live:
        return box, "ph"
    box = lane_box(project.get("lane"), live)
    return box, "lead" if box else "none"


def watch_box(box: str, lane: str | None = None) -> str | None:
    """Retain a live owner; otherwise follow its lane's current live pointer."""
    try:
        live = live_boxes()
    except Exception:  # no hub (tests, an outage): keep the owner box, as before the fallback existed
        return box
    if box in live:
        return box
    return lane_box(lane or box.partition("-")[0], live)
