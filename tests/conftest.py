"""Parametrize the specification's single backend boundary without editing it."""
from pathlib import Path
import sys

import pytest

TESTS_DIR = Path(__file__).resolve().parent
ROOT = TESTS_DIR.parent
for _p in (str(TESTS_DIR), str(ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def pytest_generate_tests(metafunc):
    if metafunc.module.__name__.split(".")[-1] == "test_lease_scenarios" and "backend" in metafunc.fixturenames:
        from lease_model import LeaseModel
        from lease_adapter import LeaseAdapter
        # Direct parametrization replaces only the backend fixture. The copied
        # specification and reference model stay byte-for-byte unchanged.
        metafunc.parametrize("backend", [LeaseModel, LeaseAdapter], ids=["reference", "lib.lease"])
