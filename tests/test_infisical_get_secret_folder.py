"""`_get_secret`: a missing secret is None, a missing FOLDER is an error.

`capture_key.mjs --new-only` asks `last4` whether the target is free before it clicks Create at the
provider. A folder that does not exist read as "free" on 2026-10-13 (task-b1b251f0): OpenRouter minted
a key, `put` answered "Folder ... not found", and the key sat unsaved at the provider.
"""
from __future__ import annotations

import pytest

from tools import infisical_setup


class _Org:
    def __init__(self, message):
        self.message = message

    def get(self, route, **query):
        raise infisical_setup.ApiError(self.message)


def test_missing_secret_is_none():
    org = _Org("Secret with name 'X' not found: GET /api/v3/secrets/raw/X -> HTTP 404")
    assert infisical_setup._get_secret(org, "pid", "prod", "X", "/spend-guard") is None


def test_missing_folder_raises():
    org = _Org("Folder with path '/spend-guard' in environment with slug 'prod' not found "
               "(reqId r): GET /api/v3/secrets/raw/X -> HTTP 404")
    with pytest.raises(infisical_setup.ApiError):
        infisical_setup._get_secret(org, "pid", "prod", "X", "/spend-guard")
