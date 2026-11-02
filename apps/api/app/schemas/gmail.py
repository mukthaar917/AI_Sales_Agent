"""Schemas for Gmail OAuth and connection endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class GmailAuthorizationResponse(BaseModel):
    """Response containing the Google OAuth authorization URL."""

    authorization_url: str


class GmailConnectionResponse(BaseModel):
    """Safe Gmail connection information returned by the API."""

    connected: bool
    email_address: str | None = None
    scopes: list[str] = Field(default_factory=list)
    token_expiry: datetime | None = None
    history_id: str | None = None


class GmailDisconnectResponse(BaseModel):
    """Response returned after disconnecting Gmail."""

    connected: bool = False