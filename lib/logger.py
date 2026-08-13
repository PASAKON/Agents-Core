"""Per-agent file logger. Each task gets own log file + a _latest symlink."""
from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Overridable so a service running under its own account can log outside the
# checkout. state/ also holds tasks.db and the rest of the org's runtime data,
# so granting a service user write access to it just to open a log file would
# be far too broad. Unset ⇒ unchanged behaviour.
LOG_DIR = Path(os.environ.get("ORG_LOG_DIR") or ROOT / "state" / "logs")

LOG_MAX_BYTES = 10 * 1024 * 1024
LOG_BACKUP_COUNT = 5


class _LazyRotatingFileHandler(RotatingFileHandler):
    """RotatingFileHandler(delay=True) alone still updated the `_latest`
    symlink and created LOG_DIR eagerly at construction time — i.e. on every
    get_logger() call, whether or not anything was ever logged. That is what
    let `import runners.cto` (module-level `get_logger("cto")`) write
    state/logs/cto.log merely by being collected (GH #57). Piggyback both
    side effects on _open(), the stdlib's own lazy-open hook, so everything
    that touches disk happens together, only on the first real log call."""

    def __init__(self, *args, latest_path: Path, **kwargs):
        super().__init__(*args, **kwargs)
        self._latest_path = latest_path

    def _open(self):
        path = Path(self.baseFilename)
        path.parent.mkdir(parents=True, exist_ok=True)
        stream = super()._open()
        try:
            if self._latest_path.is_symlink() or self._latest_path.exists():
                self._latest_path.unlink()
            self._latest_path.symlink_to(path.name)
        except OSError:
            pass
        return stream


def get_logger(role: str, task_id: str | None = None, stdout: bool = True) -> logging.Logger:
    name = f"{role}_{task_id}" if task_id else role
    log_path = LOG_DIR / f"{name}.log"

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    logger.propagate = False

    fh = _LazyRotatingFileHandler(
        log_path, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8", delay=True, latest_path=LOG_DIR / f"{role}_latest.log",
    )
    fh.setFormatter(logging.Formatter(
        "[%(asctime)s] %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    ))
    logger.addHandler(fh)

    if stdout:
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(logging.Formatter(f"[{name}] %(message)s"))
        logger.addHandler(sh)

    return logger
