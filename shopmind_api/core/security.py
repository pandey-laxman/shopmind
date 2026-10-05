from datetime import UTC, datetime, timedelta
import logging

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
import jwt

from shopmind_api.core.config import settings


password_hasher = PasswordHasher()
_dummy_hash = password_hasher.hash("ShopMind timing equalization, not an account")
JWT_ISSUER = "shopmind"
JWT_AUDIENCE = "shopmind-api"


def signing_secret() -> str:
    if settings.JWT_SECRET is None or len(settings.JWT_SECRET.get_secret_value()) < 32:
        raise RuntimeError("JWT_SECRET must be configured with at least 32 characters")
    return settings.JWT_SECRET.get_secret_value()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    try:
        valid = password_hasher.verify(password_hash or _dummy_hash, password)
        return valid and password_hash is not None
    except VerifyMismatchError:
        return False
    except (InvalidHashError, VerificationError):
        # Corrupted stored hashes are operational errors, not valid credentials.
        logging.getLogger(__name__).error("password_hash_verification_error")
        return False


def create_access_token(customer_id: int) -> tuple[str, int]:
    now = datetime.now(UTC)
    expires_in = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    token = jwt.encode(
        {
            "sub": str(customer_id),
            "iat": now,
            "exp": now + timedelta(seconds=expires_in),
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
        },
        signing_secret(),
        algorithm="HS256",
    )
    return token, expires_in


def decode_customer_id(token: str) -> int:
    claims = jwt.decode(
        token,
        signing_secret(),
        algorithms=["HS256"],
        issuer=JWT_ISSUER,
        audience=JWT_AUDIENCE,
        options={"require": ["sub", "iat", "exp", "iss", "aud"]},
    )
    subject = claims["sub"]
    if (
        not isinstance(subject, str)
        or not 1 <= len(subject) <= 10
        or not subject.isascii()
        or not subject.isdigit()
    ):
        raise jwt.InvalidTokenError("Invalid subject")
    customer_id = int(subject)
    if not 1 <= customer_id <= 2147483647:
        raise jwt.InvalidTokenError("Invalid subject")
    return customer_id
