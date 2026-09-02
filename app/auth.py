from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from time import monotonic

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
import jwt
from jwt.exceptions import InvalidTokenError

password_hasher = PasswordHasher()


class AuthenticationError(ValueError):
    pass


class LoginRateLimiter:
    def __init__(self, attempts: int, window_seconds: int) -> None:
        self.attempts = attempts
        self.window_seconds = window_seconds
        self.failures: dict[str, deque[float]] = defaultdict(deque)

    def is_allowed(self, client_key: str, now: float | None = None) -> bool:
        now = monotonic() if now is None else now
        failures = self.failures[client_key]
        while failures and now - failures[0] >= self.window_seconds:
            failures.popleft()
        return len(failures) < self.attempts

    def record_failure(self, client_key: str, now: float | None = None) -> None:
        now = monotonic() if now is None else now
        self.is_allowed(client_key, now)
        self.failures[client_key].append(now)

    def record_success(self, client_key: str) -> None:
        self.failures.pop(client_key, None)


def validate_jwt_secret(secret: str) -> None:
    if len(secret.encode("utf-8")) < 32:
        raise ValueError("JWT secret must contain at least 32 bytes")


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerifyMismatchError):
        return False


def create_access_token(user_id: int, username: str, role: str, secret: str, expires_minutes: int) -> str:
    validate_jwt_secret(secret)
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(user_id),
            "username": username,
            "role": role,
            "iat": now,
            "exp": now + timedelta(minutes=expires_minutes),
        },
        secret,
        algorithm="HS256",
    )


def decode_access_token(token: str, secret: str) -> dict[str, str]:
    validate_jwt_secret(secret)
    try:
        claims = jwt.decode(token, secret, algorithms=["HS256"])
    except InvalidTokenError as error:
        raise AuthenticationError("Invalid or expired access token") from error
    if not isinstance(claims.get("sub"), str) or not isinstance(claims.get("role"), str):
        raise AuthenticationError("Invalid access token claims")
    return claims