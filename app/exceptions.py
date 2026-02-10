"""
Custom exceptions for the authentication service.

Provides domain-specific exceptions with consistent error handling.
"""

from typing import Any, Optional


class AuthServiceException(Exception):
    """Base exception for all auth service errors."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Any = None,
        status_code: int = 400
    ):
        self.message = message
        self.error_code = error_code or "AUTH_ERROR"
        self.details = details
        self.status_code = status_code
        super().__init__(self.message)


class TokenValidationError(AuthServiceException):
    """Raised when JWT token validation fails."""
    
    def __init__(self, message: str = "Invalid or expired token", details: Any = None):
        super().__init__(
            message=message,
            error_code="TOKEN_INVALID",
            details=details,
            status_code=401
        )


class TokenExpiredError(AuthServiceException):
    """Raised when JWT token has expired."""
    
    def __init__(self, message: str = "Token has expired", details: Any = None):
        super().__init__(
            message=message,
            error_code="TOKEN_EXPIRED",
            details=details,
            status_code=401
        )


class InsufficientPermissionsError(AuthServiceException):
    """Raised when user lacks required role or scope."""
    
    def __init__(self, required: str, message: str = None, details: Any = None):
        super().__init__(
            message=message or f"Required permission: {required}",
            error_code="INSUFFICIENT_PERMISSIONS",
            details=details or {"required": required},
            status_code=403
        )


class KeycloakConnectionError(AuthServiceException):
    """Raised when connection to Keycloak fails."""
    
    def __init__(self, message: str = "Failed to connect to Keycloak", details: Any = None):
        super().__init__(
            message=message,
            error_code="KEYCLOAK_CONNECTION_ERROR",
            details=details,
            status_code=503
        )


class JWKSFetchError(AuthServiceException):
    """Raised when JWKS fetching fails."""
    
    def __init__(self, message: str = "Failed to fetch JWKS", details: Any = None):
        super().__init__(
            message=message,
            error_code="JWKS_FETCH_ERROR",
            details=details,
            status_code=503
        )


class UserNotFoundError(AuthServiceException):
    """Raised when user is not found in Keycloak."""
    
    def __init__(self, user_id: str = None, message: str = None):
        super().__init__(
            message=message or f"User not found: {user_id}",
            error_code="USER_NOT_FOUND",
            details={"user_id": user_id} if user_id else None,
            status_code=404
        )


class RefreshTokenError(AuthServiceException):
    """Raised when token refresh fails."""
    
    def __init__(self, message: str = "Token refresh failed", details: Any = None):
        super().__init__(
            message=message,
            error_code="REFRESH_TOKEN_ERROR",
            details=details,
            status_code=401
        )
