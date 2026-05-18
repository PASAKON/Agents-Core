"""Textual TUI dashboard for org status. Run: python dashboard.py"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, RichLog, Static

from lib import db
from lib.config import projects

LOG_DIR = Path(__file__).resolve().parent / "state" / "logs"

STATUS_STYLES = {
    "pending": "yellow",
    "in_progress": "cyan",
    "review": "magenta",
    "done": "green",
    "failed": "red",
    "cancelled": "dim",
}


class TaskTable(DataTable):
    def on_mount(self):
        self.cursor_type = "row"
        self.add_columns("id", "project", "role", "status", "iter", "title")
        self.refresh_data()

    def refresh_data(self):
        self.clear()
        for t in db.list_tasks(limit=30):
            style = STATUS_STYLES.get(t["status"], "white")
            self.add_row(
                t["id"],
                t["project"][:20],
                t["role"],
                f"[{style}]{t['status']}[/{style}]",
                str(t["iteration"]),
                t["title"][:60],
            )


class StatsPanel(Static):
    def refresh_data(self):
        s = db.stats()
        line = " | ".join(f"[bold]{k}[/bold]:{v}" for k, v in sorted(s.items()))
        projs = " | ".join(p["key"] for p in projects().values())
        self.update(f"[b]Tasks[/b] → {line or 'none yet'}\n[b]Projects[/b] → {projs}")


class LogTail(RichLog):
    """Tails one or more log files."""
    def __init__(self, paths: list[Path], **kw):
        super().__init__(highlight=True, markup=True, **kw)
        self.paths = paths
        self._positions: dict[Path, int] = {}

    def poll(self):
        for p in self.paths:
            real = p.resolve() if p.is_symlink() else p
            if not real.exists():
                continue
            pos = self._positions.get(p, 0)
            try:
                size = real.stat().st_size
                if size < pos:
                    pos = 0  # log rotated
                with real.open("r", encoding="utf-8", errors="replace") as f:
                    f.seek(pos)
                    new = f.read()
                    self._positions[p] = f.tell()
                for line in new.splitlines():
                    self.write(line)
            except OSError:
                continue


class OrgDashboard(App):
    CSS = """
    Screen { layout: vertical; }
    #top { height: 4; }
    #middle { height: 1fr; }
    #bottom { height: 1fr; }
    DataTable { height: 1fr; }
    RichLog { border: round $accent; height: 1fr; }
    StatsPanel { padding: 0 1; background: $boost; }
    """
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield StatsPanel(id="top")
        with Horizontal(id="middle"):
            yield TaskTable(id="tasks")
        with Horizontal(id="bottom"):
            yield LogTail(
                [LOG_DIR / "cto.log"],
                id="cto_log", classes="log",
            )
            yield LogTail(
                sorted(LOG_DIR.glob("*_latest.log")),
                id="dev_log", classes="log",
            )
        yield Footer()

    def on_mount(self):
        self.set_interval(2.0, self.tick)
        self.tick()

    def tick(self):
        self.query_one(StatsPanel).refresh_data()
        self.query_one(TaskTable).refresh_data()
        for w in self.query(LogTail):
            # rescan glob in case new logs appeared
            if w.id == "dev_log":
                w.paths = sorted(LOG_DIR.glob("*_latest.log"))
            w.poll()

    def action_refresh(self):
        self.tick()


if __name__ == "__main__":
    OrgDashboard().run()
