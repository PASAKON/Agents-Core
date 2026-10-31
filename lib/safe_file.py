"""Open files in shared, group-writable folders (state/, state/locks/) without following a planted link.

Root runs the readers, and another account can plant a symlink, a FIFO or a hard link in those folders. Every open
goes through the folder's own fd (O_DIRECTORY|O_NOFOLLOW), opens the name O_NOFOLLOW|O_NONBLOCK and keeps the
fd only when fstat says it is a regular file, so nothing follows a link and nothing blocks on a FIFO.
"""
from __future__ import annotations

import os
import stat
from pathlib import Path

LIMIT = 64 * 1024
_SAFE = getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_CLOEXEC", 0)


class Unsafe(OSError):
    """The name is not a plain regular file (a link, a FIFO, a folder, a second hard link)."""


def _open(path: Path, flags: int, *, mode: int = 0o644, single_link: bool = False) -> int:
    dfd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | _SAFE)
    try:
        fd = os.open(path.name, flags | _SAFE, mode, dir_fd=dfd)
    finally:
        os.close(dfd)
    st = os.fstat(fd)
    if not stat.S_ISREG(st.st_mode) or (single_link and st.st_nlink != 1):
        os.close(fd)
        raise Unsafe(f"not a plain file: {path.name}")
    return fd


def read_text(path: Path, limit: int = LIMIT) -> str:
    """The file's text, at most `limit` bytes. FileNotFoundError when missing, Unsafe/OSError when refused."""
    fd = _open(Path(path), os.O_RDONLY)
    try:
        data = os.read(fd, limit + 1)
    finally:
        os.close(fd)
    if len(data) > limit:
        raise Unsafe(f"too large: {Path(path).name}")
    return data.decode("utf-8")


def open_append(path: Path):
    """A binary append handle on a file this process may create; a planted link, FIFO or second link is refused."""
    fd = _open(Path(path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, mode=0o600, single_link=True)
    return os.fdopen(fd, "ab")


def write_text_atomic(path: Path, text: str, *, mode: int = 0o600) -> None:
    """Replace `path` with `text` so a reader sees the old file or the new one, never half of it.

    The text goes to a fresh temp file in the same folder (O_EXCL|O_NOFOLLOW, opened through the folder's fd), is
    fsync'd, and then renamed over the name with the folder's fd on both sides, so nothing is looked up by path
    after the folder is open. If something sits at the name, the rename replaces that entry; it is never followed
    and what it pointed to is not written. On any failure the temp file is removed and the old file is untouched.
    """
    path = Path(path)
    dfd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | _SAFE)
    tmp = f".{path.name}.{os.getpid()}.{os.urandom(4).hex()}.tmp"
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | _SAFE, mode, dir_fd=dfd)
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(text.encode("utf-8"))
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, path.name, src_dir_fd=dfd, dst_dir_fd=dfd)
        except BaseException:
            try:
                os.unlink(tmp, dir_fd=dfd)
            except FileNotFoundError:
                pass
            raise
        os.fsync(dfd)
    finally:
        os.close(dfd)
