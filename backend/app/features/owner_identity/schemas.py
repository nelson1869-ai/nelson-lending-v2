"""Public request and response contracts for Owner authentication."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class OwnerSchema(BaseModel):
    """Base schema using mobile-friendly camelCase JSON aliases."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class LoginRequest(OwnerSchema):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1)


class RefreshRequest(OwnerSchema):
    refresh_token: str = Field(min_length=1)


class TokenPairResponse(OwnerSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    access_token_expires_at: datetime


class OwnerMeResponse(OwnerSchema):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    id: UUID
    username: str
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None
