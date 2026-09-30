"""Process liveness that means the same thing on every OS the org runs on.

`os.kill(pid, 0)` is the POSIX "does this pid exist" probe: signal 0 delivers
nothing. On Windows the same call is not a probe at all. Python maps signal 0
to CTRL_C_EVENT there, so `os.kill(pid, 0)` sends Ctrl-C to that pid's console
process group (and any other signal number terminates the process). A liveness
check that interrupts what it checks is worse than none, so every caller goes
through `pid_alive` and no code outside this module probes with `os.kill`.

POSIX: `os.kill(pid, 0)`.
Windows: `OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION)` then
`GetExitCodeProcess() == STILL_ACTIVE`, through ctypes (no new dependency).
"""
from __future__ import annotations

import os
import sys
from functools import lru_cache

_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
# GetExitCodeProcess reports 259 while a process runs. A process that itself
# exits with code 259 reads as alive; the same ambiguity every Windows liveness
# probe of this kind has, and no worker of ours exits with 259.
_STILL_ACTIVE = 259
_ERROR_ACCESS_DENIED = 5
_MAX_WIN_PID = 0xFFFFFFFF  # a Windows pid is a DWORD


def pid_alive(pid: int, *, denied_is_alive: bool = True) -> bool:
    """True when a process with this pid exists.

    `pid <= 0`, a non-int and a bool are False: 0 and negatives name process
    groups to `os.kill`, never one process, and `True` is not pid 1.

    `denied_is_alive` decides the one case the OS answers "exists, but you may
    not touch it" (POSIX EPERM, Windows ERROR_ACCESS_DENIED). A liveness answer
    wants True (the pid is taken); a reaper that must never signal a stranger
    passes False.
    """
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        return False
    if sys.platform == "win32":
        return _win_pid_alive(pid, denied_is_alive)
    return _posix_pid_alive(pid, denied_is_alive)


def _posix_pid_alive(pid: int, denied_is_alive: bool) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return denied_is_alive
    except (OSError, OverflowError):  # OverflowError: pid wider than pid_t
        return False
    return True


@lru_cache(maxsize=1)
def _kernel32():
    """kernel32 with the signatures this module calls. Windows only.

    Handles are declared c_void_p: the default c_int return truncates a 64-bit
    HANDLE. Split out so tests can hand `_win_pid_alive` a fake on any OS."""
    import ctypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    k32.OpenProcess.restype = ctypes.c_void_p
    k32.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
    k32.GetExitCodeProcess.restype = ctypes.c_int
    k32.CloseHandle.argtypes = [ctypes.c_void_p]
    k32.CloseHandle.restype = ctypes.c_int
    return k32


def _last_error() -> int:
    import ctypes

    return ctypes.get_last_error()  # Windows only: pairs with use_last_error


def _win_pid_alive(pid: int, denied_is_alive: bool) -> bool:
    import ctypes

    if pid > _MAX_WIN_PID:
        return False  # ctypes truncates to a DWORD: 2**32 + 4242 would open pid 4242
    k32 = _kernel32()
    handle = k32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        # ERROR_INVALID_PARAMETER (87) is "no such pid"; ACCESS_DENIED means it
        # exists and is not ours to open (an elevated or another-user process).
        return denied_is_alive if _last_error() == _ERROR_ACCESS_DENIED else False
    try:
        code = ctypes.c_uint32()
        if not k32.GetExitCodeProcess(handle, ctypes.byref(code)):
            return False
        return code.value == _STILL_ACTIVE
    finally:
        k32.CloseHandle(handle)
