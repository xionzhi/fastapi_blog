"""Administrator mail status contract; SMTP secrets are never returned."""

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from app.modules.mail.validation import validate_email_address


class MailStatus(BaseModel):
    enabled: bool
    email: str


class RecoveryEmailInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=1, max_length=254)
    previous_email: str = Field(max_length=254)
    current_password: SecretStr = Field(min_length=1, max_length=1024)
    _email = field_validator("email")(validate_email_address)
