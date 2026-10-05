from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator

from shopmind_api.schemas.customer import CustomerCreate


class RegisterRequest(CustomerCreate):
    password: SecretStr = Field(min_length=8, max_length=1024)

    @field_validator("password", mode="before")
    @classmethod
    def preserve_password(cls, value: object) -> object:
        # CustomerCreate strips strings; passwords must keep their exact whitespace.
        return SecretStr(value) if isinstance(value, str) else value


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=254)
    password: SecretStr = Field(min_length=1, max_length=1024)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
