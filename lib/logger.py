"""Per-agent file logger. Each task gets own log file + a _latest symlink."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "state" / "logs"


def get_logger(role: str, task_id: str | None = None, stdout: bool = True) -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{role}_{task_id}" if task_id else role
    log_path = LOG_DIR / f"{name}.log"

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    logger.propagate = False

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(logging.Formatter(
        "[%(asctime)s] %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    ))
    logger.addHandler(fh)

    if stdout:
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(logging.Formatter(f"[{name}] %(message)s"))
        logger.addHandler(sh)

    # update _latest symlink for tmux watch
    latest = LOG_DIR / f"{role}_latest.log"
    try:
        if latest.is_symlink() or latest.exists():
            latest.unlink()
        latest.symlink_to(log_path.name)
    except OSError:
        pass

    return logger
