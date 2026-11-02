from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


class EncryptionConfigurationError(RuntimeError):
    """Raised when token encryption is not configured correctly."""


class SecretDecryptionError(ValueError):
    """Raised when an encrypted value cannot be decrypted."""


def _get_fernet() -> Fernet:
    key = settings.token_encryption_key.strip()

    if not key:
        raise EncryptionConfigurationError(
            "TOKEN_ENCRYPTION_KEY is not configured."
        )

    try:
        return Fernet(key.encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise EncryptionConfigurationError(
            "TOKEN_ENCRYPTION_KEY is not a valid Fernet key."
        ) from exc


def encrypt_secret(value: str) -> str:
    if not value:
        raise ValueError("Secret value cannot be empty.")

    return _get_fernet().encrypt(
        value.encode("utf-8")
    ).decode("utf-8")


def decrypt_secret(value: str) -> str:
    if not value:
        raise ValueError("Encrypted value cannot be empty.")

    try:
        return _get_fernet().decrypt(
            value.encode("utf-8")
        ).decode("utf-8")
    except InvalidToken as exc:
        raise SecretDecryptionError(
            "Encrypted value could not be decrypted."
        ) from exc