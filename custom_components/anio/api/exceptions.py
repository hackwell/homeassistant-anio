"""Exceptions for the ANIO API client."""

from __future__ import annotations


class AnioApiError(Exception):
    """Base exception for ANIO API errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        """Initialize the exception.

        Args:
            message: Error message.
            status_code: HTTP status code if available.
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class AnioAuthError(AnioApiError):
    """Exception for authentication errors."""

    def __init__(self, message: str = "Authentication failed") -> None:
        """Initialize the exception.

        Args:
            message: Error message.
        """
        super().__init__(message, status_code=401)


class AnioOtpRequiredError(AnioAuthError):
    """Exception when OTP/2FA code is required."""

    def __init__(self, message: str = "OTP code required") -> None:
        """Initialize the exception.

        Args:
            message: Error message.
        """
        super().__init__(message)


class AnioRateLimitError(AnioApiError):
    """Exception for rate limiting (429 responses)."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int | None = None,
    ) -> None:
        """Initialize the exception.

        Args:
            message: Error message.
            retry_after: Seconds to wait before retrying.
        """
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class AnioConnectionError(AnioApiError):
    """Exception for connection errors."""

    def __init__(self, message: str = "Connection failed") -> None:
        """Initialize the exception.

        Args:
            message: Error message.
        """
        super().__init__(message)


class AnioDeviceNotFoundError(AnioApiError):
    """Exception when a device is not found."""

    def __init__(self, device_id: str) -> None:
        """Initialize the exception.

        Args:
            device_id: The device ID that was not found.
        """
        super().__init__(f"Device not found: {device_id}", status_code=404)
        self.device_id = device_id


class AnioMessageTooLongError(AnioApiError):
    """Exception when a message exceeds the maximum length."""

    def __init__(self, length: int, max_length: int) -> None:
        """Initialize the exception.

        Args:
            length: The actual message length.
            max_length: The maximum allowed length.
        """
        super().__init__(
            f"Message too long: {length} characters (max {max_length})",
            status_code=400,
        )
        self.length = length
        self.max_length = max_length
