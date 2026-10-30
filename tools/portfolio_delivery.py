"""Live mailbox routing shared by the portfolio collector and watch."""
import re
from pathlib import Path

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
        sid = (ROOT / "state" / "locks" / f"{lane}-active").read_text().strip()
    except OSError:
        sid = ""
    box = sid if sid.startswith(f"{lane}-") else f"{lane}-{sid}"
    if box in live:
        return box
    return next(iter(sorted(b for b in live if b.startswith(f"{lane}-"))), None)


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
