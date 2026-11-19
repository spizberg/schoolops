"""Unit tests for password hashing and the in-process rate limiter."""

from schoolops.core.rate_limit import LoginRateLimiter
from schoolops.core.security import hash_password, verify_password


def test_passwords_are_argon2id_hashes_and_verify() -> None:
    password_hash = hash_password("a-long-test-password")

    assert password_hash.startswith("$argon2")
    assert password_hash != "a-long-test-password"
    assert verify_password("a-long-test-password", password_hash) is True
    assert verify_password("wrong", password_hash) is False


def test_malformed_hash_fails_closed() -> None:
    assert verify_password("anything", "not-a-hash") is False


def test_rate_limiter_blocks_after_the_configured_threshold() -> None:
    limiter = LoginRateLimiter(max_attempts=2, window_seconds=60)
    key = "127.0.0.1:test@example.com"

    assert limiter.retry_after(key, now=0) is None
    limiter.record_failure(key, now=1)
    assert limiter.retry_after(key, now=1) is None
    limiter.record_failure(key, now=2)

    assert limiter.retry_after(key, now=2) == 59
    assert limiter.retry_after(key, now=62) is None


def test_rate_limiter_resets_a_key() -> None:
    limiter = LoginRateLimiter(max_attempts=1, window_seconds=60)
    limiter.record_failure("key", now=0)
    assert limiter.retry_after("key", now=0) is not None

    limiter.reset("key")

    assert limiter.retry_after("key", now=0) is None
