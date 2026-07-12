from datetime import datetime
from typing import Annotated, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    model_validator,
)


def validate_bcrypt_password(value: str) -> str:
    if len(value.encode("utf-8")) > 72:
        raise ValueError("Password must not exceed 72 bytes")
    return value

Username = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=2, max_length=30),
]
UserEmail = Annotated[EmailStr, Field(max_length=320)]
Password = Annotated[str, Field(min_length=6), AfterValidator(validate_bcrypt_password)]


class UserCreate(BaseModel):
    username: Username
    email: UserEmail
    password: Password
    confirm_password: Password

    @model_validator(mode="after")
    def validate_passwords_match(self) -> Self:
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class UserRead(BaseModel):
    id: int
    username: str
    email: EmailStr
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    username: Username | None = None
    email: UserEmail | None = None
    password: Password | None = None
    is_active: bool | None = None
