from datetime import datetime

from pydantic import BaseModel, Field
from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.common.orm import Base, UTCDateTime


class Login(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=1024)


class CurrentUser(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    username: str
    email: str = ""


class SessionResponse(BaseModel):
    username: str
    csrf_token: str


class RecoveryStatus(BaseModel):
    enabled: bool


class ForgotPassword(BaseModel):
    identifier: str = Field(min_length=1, max_length=254)


class ResetToken(BaseModel):
    token: str = Field(min_length=64, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")


class NewPassword(ResetToken):
    password: str = Field(min_length=12, max_length=1024)


class ValidTokenResponse(BaseModel):
    valid: bool = True


class UserOrm(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    email: Mapped[str] = mapped_column(String(254), default="", server_default="")
    __table_args__ = (
        Index("users_email_unique", email.collate("NOCASE"), unique=True, sqlite_where=email != ""),
    )


class SessionOrm(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    expires_at: Mapped[int]


class LoginAttemptOrm(Base):
    __tablename__ = "login_attempts"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    attempts: Mapped[int]
    reset_at: Mapped[int]


class PasswordResetOrm(Base):
    __tablename__ = "password_resets"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[int]
    created_at: Mapped[int]
