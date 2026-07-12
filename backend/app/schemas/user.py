from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

Username = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=2, max_length=30),
]
UserEmail = Annotated[EmailStr, Field(max_length=320)]
Password = Annotated[str, Field(min_length=6, max_length=128)]


class UserCreate(BaseModel):
    username: Username
    email: UserEmail
    password: Password


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
