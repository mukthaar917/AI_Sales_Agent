from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.services.gmail.oauth import (
    GmailOAuthError,
    GmailOAuthService,
)


@pytest.fixture
def oauth_service(monkeypatch: pytest.MonkeyPatch) -> GmailOAuthService:
    monkeypatch.setattr(
        "app.services.gmail.oauth.settings.google_client_id",
        "test-client-id",
    )
    monkeypatch.setattr(
        "app.services.gmail.oauth.settings.google_client_secret",
        "test-client-secret",
    )
    monkeypatch.setattr(
        "app.services.gmail.oauth.settings.google_redirect_uri",
        "http://localhost:8000/api/v1/gmail/oauth/callback",
    )
    monkeypatch.setattr(
        "app.services.gmail.oauth.settings.gmail_scopes",
        "https://www.googleapis.com/auth/gmail.readonly",
    )

    return GmailOAuthService()


@pytest.fixture
def mock_credentials() -> MagicMock:
    credentials = MagicMock()
    credentials.token = "test-access-token"
    credentials.refresh_token = "test-refresh-token"
    credentials.expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    credentials.scopes = [
        "https://www.googleapis.com/auth/gmail.readonly",
    ]
    return credentials


def test_build_authorization_url_returns_url_and_state(
    oauth_service: GmailOAuthService,
) -> None:
    mock_flow = MagicMock()
    mock_flow.authorization_url.return_value = (
        "https://accounts.google.com/o/oauth2/auth?state=test-state",
        "test-state",
    )

    with patch(
        "app.services.gmail.oauth.Flow.from_client_config",
        return_value=mock_flow,
    ) as mock_from_client_config:
        authorization_url, state = oauth_service.build_authorization_url()

    assert authorization_url.startswith("https://accounts.google.com/")
    assert state == "test-state"

    mock_from_client_config.assert_called_once()

    mock_flow.authorization_url.assert_called_once_with(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )


def test_build_authorization_url_wraps_google_error(
    oauth_service: GmailOAuthService,
) -> None:
    with patch(
        "app.services.gmail.oauth.Flow.from_client_config",
        side_effect=RuntimeError("Google authorization failed"),
    ):
        with pytest.raises(GmailOAuthError) as exc_info:
            oauth_service.build_authorization_url()

    assert "authorization" in str(exc_info.value).lower()
    assert "Google authorization failed" not in str(exc_info.value)


def test_exchange_code_for_tokens_returns_normalized_data(
    oauth_service: GmailOAuthService,
    mock_credentials: MagicMock,
) -> None:
    mock_flow = MagicMock()
    mock_flow.credentials = mock_credentials

    with patch(
        "app.services.gmail.oauth.Flow.from_client_config",
        return_value=mock_flow,
    ):
        result = oauth_service.exchange_code_for_tokens(
            code="test-authorization-code",
        )

    mock_flow.fetch_token.assert_called_once_with(
        code="test-authorization-code",
    )

    assert result["access_token"] == "test-access-token"
    assert result["refresh_token"] == "test-refresh-token"
    assert result["token_expiry"] == mock_credentials.expiry
    assert result["scopes"] == [
        "https://www.googleapis.com/auth/gmail.readonly",
    ]


def test_exchange_code_for_tokens_allows_missing_refresh_token(
    oauth_service: GmailOAuthService,
    mock_credentials: MagicMock,
) -> None:
    mock_credentials.refresh_token = None

    mock_flow = MagicMock()
    mock_flow.credentials = mock_credentials

    with patch(
        "app.services.gmail.oauth.Flow.from_client_config",
        return_value=mock_flow,
    ):
        result = oauth_service.exchange_code_for_tokens(
            code="test-authorization-code",
        )

    assert result["access_token"] == "test-access-token"
    assert result["refresh_token"] is None


@pytest.mark.parametrize(
    "invalid_code",
    [
        "",
        "   ",
    ],
)
def test_exchange_code_rejects_empty_code(
    oauth_service: GmailOAuthService,
    invalid_code: str,
) -> None:
    with pytest.raises(ValueError):
        oauth_service.exchange_code_for_tokens(invalid_code)


def test_exchange_code_wraps_google_error_without_exposing_code(
    oauth_service: GmailOAuthService,
) -> None:
    authorization_code = "secret-authorization-code"

    mock_flow = MagicMock()
    mock_flow.fetch_token.side_effect = RuntimeError(
        f"Failed for code {authorization_code}",
    )

    with patch(
        "app.services.gmail.oauth.Flow.from_client_config",
        return_value=mock_flow,
    ):
        with pytest.raises(GmailOAuthError) as exc_info:
            oauth_service.exchange_code_for_tokens(
                code=authorization_code,
            )

    assert authorization_code not in str(exc_info.value)
    assert "token" in str(exc_info.value).lower()


def test_refresh_access_token_returns_new_token_data(
    oauth_service: GmailOAuthService,
) -> None:
    refreshed_expiry = datetime.now(timezone.utc) + timedelta(hours=1)

    mock_credentials = MagicMock()
    mock_credentials.token = "new-access-token"
    mock_credentials.refresh_token = "stored-refresh-token"
    mock_credentials.expiry = refreshed_expiry
    mock_credentials.scopes = [
        "https://www.googleapis.com/auth/gmail.readonly",
    ]

    with (
        patch(
            "app.services.gmail.oauth.Credentials",
            return_value=mock_credentials,
        ) as mock_credentials_class,
        patch(
            "app.services.gmail.oauth.Request",
        ) as mock_request_class,
    ):
        result = oauth_service.refresh_access_token(
            refresh_token="stored-refresh-token",
        )

    mock_credentials_class.assert_called_once()
    mock_credentials.refresh.assert_called_once_with(
        mock_request_class.return_value,
    )

    assert result["access_token"] == "new-access-token"
    assert result["refresh_token"] == "stored-refresh-token"
    assert result["token_expiry"] == refreshed_expiry
    assert result["scopes"] == [
        "https://www.googleapis.com/auth/gmail.readonly",
    ]


@pytest.mark.parametrize(
    "invalid_refresh_token",
    [
        "",
        "   ",
    ],
)
def test_refresh_access_token_rejects_empty_refresh_token(
    oauth_service: GmailOAuthService,
    invalid_refresh_token: str,
) -> None:
    with pytest.raises(ValueError):
        oauth_service.refresh_access_token(invalid_refresh_token)


def test_refresh_access_token_wraps_google_error_and_hides_secret(
    oauth_service: GmailOAuthService,
) -> None:
    refresh_token = "secret-refresh-token"

    mock_credentials = MagicMock()
    mock_credentials.refresh.side_effect = RuntimeError(
        f"Could not refresh {refresh_token}",
    )

    with (
        patch(
            "app.services.gmail.oauth.Credentials",
            return_value=mock_credentials,
        ),
        patch(
            "app.services.gmail.oauth.Request",
        ),
    ):
        with pytest.raises(GmailOAuthError) as exc_info:
            oauth_service.refresh_access_token(refresh_token)

    assert refresh_token not in str(exc_info.value)
    assert "refresh" in str(exc_info.value).lower()


def test_fetch_gmail_profile_returns_normalized_profile(
    oauth_service: GmailOAuthService,
) -> None:
    mock_request = MagicMock()
    mock_request.execute.return_value = {
        "emailAddress": "sales@example.com",
        "messagesTotal": 42,
        "threadsTotal": 18,
        "historyId": "123456789",
    }

    mock_users = MagicMock()
    mock_users.getProfile.return_value = mock_request

    mock_gmail_service = MagicMock()
    mock_gmail_service.users.return_value = mock_users

    with (
        patch(
            "app.services.gmail.oauth.Credentials",
        ) as mock_credentials_class,
        patch(
            "app.services.gmail.oauth.build",
            return_value=mock_gmail_service,
        ) as mock_build,
    ):
        result = oauth_service.fetch_gmail_profile(
            access_token="test-access-token",
        )

    mock_credentials_class.assert_called_once()
    mock_build.assert_called_once_with(
        "gmail",
        "v1",
        credentials=mock_credentials_class.return_value,
        cache_discovery=False,
    )

    mock_users.getProfile.assert_called_once_with(userId="me")
    mock_request.execute.assert_called_once_with()

    assert result == {
        "email_address": "sales@example.com",
        "messages_total": 42,
        "threads_total": 18,
        "history_id": "123456789",
    }


@pytest.mark.parametrize(
    "invalid_access_token",
    [
        "",
        "   ",
    ],
)
def test_fetch_gmail_profile_rejects_empty_access_token(
    oauth_service: GmailOAuthService,
    invalid_access_token: str,
) -> None:
    with pytest.raises(ValueError):
        oauth_service.fetch_gmail_profile(invalid_access_token)


def test_fetch_gmail_profile_rejects_missing_email_address(
    oauth_service: GmailOAuthService,
) -> None:
    mock_request = MagicMock()
    mock_request.execute.return_value = {
        "messagesTotal": 42,
        "threadsTotal": 18,
        "historyId": "123456789",
    }

    mock_users = MagicMock()
    mock_users.getProfile.return_value = mock_request

    mock_gmail_service = MagicMock()
    mock_gmail_service.users.return_value = mock_users

    with (
        patch("app.services.gmail.oauth.Credentials"),
        patch(
            "app.services.gmail.oauth.build",
            return_value=mock_gmail_service,
        ),
    ):
        with pytest.raises(GmailOAuthError) as exc_info:
            oauth_service.fetch_gmail_profile(
                access_token="test-access-token",
            )

    assert "email" in str(exc_info.value).lower()


def test_fetch_gmail_profile_wraps_google_error_and_hides_token(
    oauth_service: GmailOAuthService,
) -> None:
    access_token = "secret-access-token"

    mock_request = MagicMock()
    mock_request.execute.side_effect = RuntimeError(
        f"Request failed with {access_token}",
    )

    mock_users = MagicMock()
    mock_users.getProfile.return_value = mock_request

    mock_gmail_service = MagicMock()
    mock_gmail_service.users.return_value = mock_users

    with (
        patch("app.services.gmail.oauth.Credentials"),
        patch(
            "app.services.gmail.oauth.build",
            return_value=mock_gmail_service,
        ),
    ):
        with pytest.raises(GmailOAuthError) as exc_info:
            oauth_service.fetch_gmail_profile(access_token)

    assert access_token not in str(exc_info.value)
    assert "profile" in str(exc_info.value).lower()