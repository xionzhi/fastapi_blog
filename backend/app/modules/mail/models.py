"""Administrator mail status contract; SMTP secrets are never returned."""

from pydantic import BaseModel


class MailStatus(BaseModel):
    enabled: bool
    email: str
