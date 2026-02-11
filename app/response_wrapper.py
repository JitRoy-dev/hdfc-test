"""
Response wrapper for consistent API responses across all endpoints.

Provides standardized success and error response formats with metadata including TTL.
"""

from typing import Any, Optional, Dict
from datetime import datetime, timedelta
from fastapi import status
from fastapi.responses import JSONResponse


class APIResponse:
    """
    Standardized API response wrapper with TTL support.
    
    All API responses follow this structure:
    {
        "success": true/false,
        "data": {...},           # Present on success
        "error": {...},          # Present on failure
        "metadata": {
            "timestamp": "ISO-8601",
            "version": "1.0",
            "ttl": {
                "value": 300,
                "unit": "seconds",
                "expires_at": "ISO-8601"
            }
        }
    }
    """
    
    @staticmethod
    def success(
        data: Any = None,
        message: str = "Success",
        status_code: int = status.HTTP_200_OK,
        metadata: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None
    ) -> JSONResponse:
        """
        Create a successful response with optional TTL.
        
        Args:
            data: Response payload
            message: Success message
            status_code: HTTP status code (default: 200)
            metadata: Additional metadata
            ttl: Time-to-live in seconds (optional)
            
        Returns:
            JSONResponse with standardized success format including TTL
        """
        base_metadata = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": "1.0",
        }
        
        # Add TTL information if provided
        if ttl is not None:
            expires_at = datetime.utcnow() + timedelta(seconds=ttl)
            base_metadata["ttl"] = {
                "value": ttl,
                "unit": "seconds",
                "expires_at": expires_at.isoformat() + "Z",
                "human_readable": f"{ttl // 60} minutes" if ttl >= 60 else f"{ttl} seconds"
            }
        
        # Merge with additional metadata
        if metadata:
            base_metadata.update(metadata)
        
        response_data = {
            "success": True,
            "message": message,
            "data": data,
            "metadata": base_metadata
        }
        
        return JSONResponse(
            content=response_data,
            status_code=status_code
        )
    
    @staticmethod
    def error(
        message: str,
        error_code: Optional[str] = None,
        details: Any = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        metadata: Optional[Dict[str, Any]] = None
    ) -> JSONResponse:
        """
        Create an error response.
        
        Args:
            message: Error message
            error_code: Application-specific error code
            details: Additional error details
            status_code: HTTP status code (default: 400)
            metadata: Additional metadata
            
        Returns:
            JSONResponse with standardized error format
        """
        response_data = {
            "success": False,
            "error": {
                "message": message,
                "code": error_code or f"ERR_{status_code}",
                "details": details
            },
            "metadata": {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "version": "1.0",
                **(metadata or {})
            }
        }
        
        return JSONResponse(
            content=response_data,
            status_code=status_code
        )
    
    @staticmethod
    def unauthorized(
        message: str = "Authentication required",
        details: Any = None
    ) -> JSONResponse:
        """Shorthand for 401 Unauthorized response."""
        return APIResponse.error(
            message=message,
            error_code="UNAUTHORIZED",
            details=details,
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    @staticmethod
    def forbidden(
        message: str = "Access forbidden",
        details: Any = None
    ) -> JSONResponse:
        """Shorthand for 403 Forbidden response."""
        return APIResponse.error(
            message=message,
            error_code="FORBIDDEN",
            details=details,
            status_code=status.HTTP_403_FORBIDDEN
        )
    
    @staticmethod
    def not_found(
        message: str = "Resource not found",
        details: Any = None
    ) -> JSONResponse:
        """Shorthand for 404 Not Found response."""
        return APIResponse.error(
            message=message,
            error_code="NOT_FOUND",
            details=details,
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    @staticmethod
    def server_error(
        message: str = "Internal server error",
        details: Any = None
    ) -> JSONResponse:
        """Shorthand for 500 Internal Server Error response."""
        return APIResponse.error(
            message=message,
            error_code="INTERNAL_ERROR",
            details=details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def wrap_response(
    data: Any, 
    message: str = "Success",
    ttl: Optional[int] = None
) -> Dict[str, Any]:
    """
    Simple dict wrapper for responses with optional TTL (when not using JSONResponse directly).
    
    Args:
        data: Response payload
        message: Success message
        ttl: Time-to-live in seconds (optional)
    
    Usage:
        return wrap_response({"user": user_data}, "User fetched successfully", ttl=300)
    """
    base_metadata = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "1.0"
    }
    
    # Add TTL information if provided
    if ttl is not None:
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        base_metadata["ttl"] = {
            "value": ttl,
            "unit": "seconds",
            "expires_at": expires_at.isoformat() + "Z",
            "human_readable": f"{ttl // 60} minutes" if ttl >= 60 else f"{ttl} seconds"
        }
    
    return {
        "success": True,
        "message": message,
        "data": data,
        "metadata": base_metadata
    }
