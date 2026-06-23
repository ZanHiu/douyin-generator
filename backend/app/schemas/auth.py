from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)


class AuthUserResponse(BaseModel):
    id: str
    email: str
    is_admin: bool


class AuthSessionResponse(BaseModel):
    user: AuthUserResponse
