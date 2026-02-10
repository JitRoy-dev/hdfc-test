"""
JWT token validation utilities with JWKS caching.

Provides secure JWT validation using Keycloak's public keys (JWKS).
Implements TTL-based caching to minimize network calls to Keycloak.
"""

from typing import Dict, Any
import logging
import httpx
from jose import jwt, JWTError
from cachetools import TTLCache
from .config import settings
from .exceptions import TokenValidationError, JWKSFetchError

logger = logging.getLogger("jwt_utils")

# Cache JWKS with configurable TTL
# JWKS (JSON Web Key Set) contains public keys used to verify JWT signatures
# Keys rarely change, so caching reduces load on Keycloak
_jwks_cache = TTLCache(
    maxsize=settings.JWKS_CACHE_MAXSIZE,
    ttl=settings.JWKS_CACHE_TTL
)

async def _fetch_jwks() -> Dict[str, Any]:
    """
    Fetch JWKS (JSON Web Key Set) from Keycloak with caching.
    
    JWKS contains public keys used to verify JWT signatures.
    Cached for JWKS_CACHE_TTL seconds (default: 10 minutes).
    
    Returns:
        Dict containing JWKS keys
        
    Raises:
        JWKSFetchError: If fetching JWKS fails
    """
    key = "jwks"
    
    # Return from cache if available
    if key in _jwks_cache:
        logger.debug("JWKS cache hit")
        return _jwks_cache[key]
    
    # Fetch from Keycloak
    url = f"{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/certs"
    
    try:
        logger.info(f"Fetching JWKS from Keycloak: {url}")
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url)
            r.raise_for_status()
            jwks = r.json()
            
            # Cache for future requests
            _jwks_cache[key] = jwks
            logger.info(f"JWKS cached successfully (TTL: {settings.JWKS_CACHE_TTL}s)")
            
            return jwks
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch JWKS: {e}")
        raise JWKSFetchError(f"Failed to fetch JWKS from Keycloak: {str(e)}") from e
    except Exception as e:
        logger.exception("Unexpected error fetching JWKS")
        raise JWKSFetchError(f"Unexpected error fetching JWKS: {str(e)}") from e

async def validate_bearer_token(token: str, audience: str = None) -> Dict[str, Any]:
    """
    Validate an RS256 JWT using Keycloak JWKS.
    
    Performs comprehensive validation:
    - Signature verification using Keycloak's public key
    - Expiration check (exp claim)
    - Issuer verification (iss claim)
    - Audience verification (aud claim, if provided)
    
    Args:
        token: JWT token string
        audience: Expected audience (optional)
        
    Returns:
        Dict containing JWT claims (sub, email, roles, etc.)
        
    Raises:
        TokenValidationError: If token is invalid or expired
        JWKSFetchError: If JWKS fetching fails
    """
    try:
        # Fetch JWKS (cached)
        jwks = await _fetch_jwks()
        
        # Configure validation options
        options = {
            "verify_aud": bool(audience),  # Only verify audience if provided
            "verify_exp": True,  # Always verify expiration
            "verify_iss": True,  # Always verify issuer
        }
        
        # Decode and validate JWT
        claims = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],  # Keycloak uses RS256 (RSA + SHA256)
            audience=audience,
            issuer=f"{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}",
            options=options,
        )
        
        logger.debug(f"Token validated successfully for user: {claims.get('preferred_username')}")
        return claims
        
    except JWTError as e:
        logger.warning(f"JWT validation error: {e}")
        raise TokenValidationError(f"Invalid or expired token: {str(e)}") from e
    except JWKSFetchError:
        # Re-raise JWKS errors as-is
        raise
    except Exception as e:
        logger.exception("Unexpected error validating token")
        raise TokenValidationError(f"Token validation failed: {str(e)}") from e


def clear_jwks_cache() -> None:
    """
    Clear the JWKS cache.
    
    Useful for testing or when Keycloak keys are rotated.
    Next token validation will fetch fresh JWKS from Keycloak.
    """
    _jwks_cache.clear()
    logger.info("JWKS cache cleared")


def get_cache_info() -> Dict[str, Any]:
    """
    Get JWKS cache statistics.
    
    Returns:
        Dict with cache size, TTL, and current entries
    """
    return {
        "maxsize": _jwks_cache.maxsize,
        "ttl": _jwks_cache.ttl,
        "current_size": len(_jwks_cache),
        "keys": list(_jwks_cache.keys())
    }
