# common/secrets.py -- GitHub PAT resolution with module-global cache.
# Import as: from common.secrets import get_pats, _reset_cache

from __future__ import annotations

import os
from typing import Any

import config

# Module-global cache; None means "not yet resolved".
_cached_pats: list[str] | None = None


def get_pats() -> list[str]:
    """Return the list of GitHub PATs, cached after the first call.

    Resolution order
    ----------------
    1. If the env var named by ``config.SSM_PAT_PARAM_ENV`` is set, fetch that
       SSM SecureString via boto3 and split on commas and newlines.
    2. Else collect ``PAT_1``, ``PAT_2``, ... ``PAT_n`` (in order) until the
       first missing index.
    3. Else if ``GH_TOKEN`` is set, return ``[GH_TOKEN]``.
    4. Else return ``[]``.

    The boto3 call is wrapped so that local development without AWS credentials
    falls through to the env-var paths gracefully.
    """
    global _cached_pats  # noqa: PLW0603

    if _cached_pats is not None:
        return _cached_pats

    pats: list[str] = []

    # --- Path 1: SSM Parameter Store ---
    ssm_param_name: str | None = os.environ.get(config.SSM_PAT_PARAM_ENV)
    if ssm_param_name:
        pats = _fetch_from_ssm(ssm_param_name)
        if pats:
            _cached_pats = pats
            return _cached_pats

    # --- Path 2: Numbered env vars PAT_1 ... PAT_n ---
    numbered: list[str] = []
    i = 1
    while True:
        val = os.environ.get(f"PAT_{i}")
        if not val:
            break
        numbered.append(val.strip())
        i += 1

    if numbered:
        _cached_pats = numbered
        return _cached_pats

    # --- Path 3: GH_TOKEN fallback ---
    gh_token: str | None = os.environ.get("GH_TOKEN")
    if gh_token:
        _cached_pats = [gh_token.strip()]
        return _cached_pats

    # --- Path 4: nothing configured ---
    _cached_pats = []
    return _cached_pats


def _fetch_from_ssm(param_name: str) -> list[str]:
    """Fetch a SecureString from SSM Parameter Store and split on comma/newline.

    Returns an empty list if boto3 is unavailable or the call fails, so that
    local development without AWS credentials falls through to env-var paths.
    """
    try:
        import boto3  # type: ignore[import-untyped]
    except ImportError:
        return []

    try:
        ssm: Any = boto3.client("ssm", region_name=os.environ.get("AWS_REGION", "us-east-1"))
        response: dict[str, Any] = ssm.get_parameter(
            Name=param_name,
            WithDecryption=True,
        )
        raw_value: str = response["Parameter"]["Value"]
    except Exception:  # noqa: BLE001 -- intentionally broad; local dev resilience
        return []

    # Split on commas and/or newlines; strip whitespace; drop empty entries.
    import re
    tokens = [t.strip() for t in re.split(r"[,\n]+", raw_value) if t.strip()]
    return tokens


def _reset_cache() -> None:
    """Clear the module-global PAT cache (for use in tests)."""
    global _cached_pats  # noqa: PLW0603
    _cached_pats = None
