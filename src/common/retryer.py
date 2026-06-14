# common/retryer.py -- PAT rotation with per-exception retry logic.
# Import as: from common.retryer import retry_with_pat_rotation

from __future__ import annotations

from typing import Callable, TypeVar

from common.http_client import (
    AccountSuspendedError,
    BadCredentialsError,
    MaxRetriesError,
    NoTokensError,
    RateLimitError,
)
from common.secrets import get_pats

T = TypeVar("T")

# Module-global rotation index so warm Lambda containers keep progressing
# through the PAT list rather than always starting from index 0.
_rotation_index: int = 0


def retry_with_pat_rotation(fn: Callable[[str], T]) -> T:
    """Call ``fn(token)`` for each available PAT, rotating on transient errors.

    The function iterates through all PATs returned by ``get_pats()``, starting
    at a module-global ``_rotation_index`` that persists across warm invocations.
    After exhausting all tokens from that offset (wrapping around the list once),
    it raises ``MaxRetriesError``.

    Retryable errors (advance to next PAT):
        - ``RateLimitError``
        - ``BadCredentialsError``
        - ``AccountSuspendedError``

    Non-retryable errors re-raise immediately without trying further tokens.

    Raises:
        NoTokensError: ``get_pats()`` returned an empty list.
        MaxRetriesError: All available PATs have been exhausted.
        Any non-retryable exception raised by ``fn``.
    """
    global _rotation_index  # noqa: PLW0603

    tokens = get_pats()
    if not tokens:
        raise NoTokensError("No GitHub PATs are configured.")

    n = len(tokens)
    start = _rotation_index % n

    for attempt in range(n):
        index = (start + attempt) % n
        token = tokens[index]

        try:
            result: T = fn(token)
            # Advance global index past this successful token so the next
            # caller starts from a fresh token (distributes load).
            _rotation_index = (index + 1) % n
            return result
        except (RateLimitError, BadCredentialsError, AccountSuspendedError):
            # Retryable: move to the next token.
            continue
        # Any other exception propagates immediately.

    raise MaxRetriesError(
        f"All {n} GitHub PAT(s) exhausted due to rate-limit or auth errors."
    )
