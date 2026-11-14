"""Lease fixture swap: reference inputs remain byte-for-byte unchanged."""


def pytest_generate_tests(metafunc):
    if metafunc.module.__name__.endswith("test_lease_scenarios") and "backend" in metafunc.fixturenames:
        from lease_model import LeaseModel
        from lease_backend import LeaseBackend
        metafunc.parametrize("backend", [LeaseModel, LeaseBackend], ids=["reference", "lib.lease"])
