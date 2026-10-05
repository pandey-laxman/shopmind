import pytest
from pydantic import SecretStr

from shopmind_api.core.config import settings


@pytest.fixture(autouse=True)
def test_signing_secret(monkeypatch):
    monkeypatch.setattr(
        settings, "JWT_SECRET", SecretStr("test-only-signing-secret-not-for-production")
    )
