import pytest

from app.auth import AuthenticationError, LoginRateLimiter, create_access_token, decode_access_token, hash_password, verify_password

TEST_SECRET = "test-jwt-secret-with-at-least-32-bytes"


def test_argon2_password_hash_verifies_only_correct_password() -> None:
    password_hash = hash_password("correct-horse-battery-staple")

    assert verify_password(password_hash, "correct-horse-battery-staple") is True
    assert verify_password(password_hash, "wrong-password") is False


def test_access_token_round_trip_and_invalid_signature() -> None:
    token = create_access_token(7, "admin", "administrator", TEST_SECRET, 30)

    assert decode_access_token(token, TEST_SECRET)["sub"] == "7"
    with pytest.raises(AuthenticationError):
        decode_access_token(token, "another-test-jwt-secret-with-at-least-32-bytes")


def test_access_token_requires_a_secure_secret() -> None:
    with pytest.raises(ValueError):
        create_access_token(7, "admin", "administrator", "too-short", 30)


def test_rate_limiter_blocks_after_configured_number_of_failures() -> None:
    limiter = LoginRateLimiter(attempts=2, window_seconds=60)

    limiter.record_failure("127.0.0.1", now=100)
    limiter.record_failure("127.0.0.1", now=101)

    assert limiter.is_allowed("127.0.0.1", now=102) is False
    assert limiter.is_allowed("127.0.0.1", now=161) is True