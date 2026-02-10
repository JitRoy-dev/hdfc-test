# AS-03 Backend Architecture

## Overview

This document describes the architecture, design patterns, and key components of the AS-03 authentication backend service.

---

## Table of Contents

1. [Project Structure](#project-structure)
2. [Response Wrappers](#response-wrappers)
3. [Exception Handling](#exception-handling)
4. [Caching Strategy](#caching-strategy)
5. [Authentication Flow](#authentication-flow)
6. [Configuration Management](#configuration-management)

---

## Project Structure

```
AS-03-Backend/
├── app/
│   ├── __init__.py              # Package initialization
│   ├── main.py                  # FastAPI app, middleware, CORS
│   ├── config.py                # Settings, env vars, TTL config
│   ├── auth.py                  # OAuth, RBAC, auth dependencies
│   ├── jwt_utils.py             # JWT validation, JWKS caching
│   ├── keycloak_admin.py        # Keycloak Admin API client
│   ├── routes.py                # All API endpoints
│   ├── exceptions.py            # Custom exception classes
│   └── response_wrapper.py      # Standardized API responses
├── tests/
│   └── test_jwks_cache.py       # Unit tests
├── .env.example                 # Environment template
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Container image
├── README.md                    # User documentation
└── ARCHITECTURE.md              # This file
```

---

## Response Wrappers

### Purpose

Provide consistent API response format across all endpoints for better client integration and error handling.

### Location

`app/response_wrapper.py`

### Standard Response Format

#### Success Response

```json
{
  "success": true,
  "message": "Success",
  "data": {
    "user": {...}
  },
  "metadata": {
    "timestamp": "2024-02-10T10:30:00Z",
    "version": "1.0"
  }
}
```

#### Error Response

```json
{
  "success": false,
  "error": {
    "message": "Authentication required",
    "code": "UNAUTHORIZED",
    "details": {...}
  },
  "metadata": {
    "timestamp": "2024-02-10T10:30:00Z",
    "version": "1.0"
  }
}
```

### Usage Examples

#### Using APIResponse Class

```python
from app.response_wrapper import APIResponse

# Success response
@router.get("/users")
async def get_users():
    users = fetch_users()
    return APIResponse.success(
        data={"users": users},
        message="Users fetched successfully"
    )

# Error response
@router.get("/protected")
async def protected_route():
    if not authenticated:
        return APIResponse.unauthorized(
            message="Please log in to access this resource"
        )
```

#### Using wrap_response Helper

```python
from app.response_wrapper import wrap_response

@router.get("/data")
async def get_data():
    data = fetch_data()
    return wrap_response(data, "Data fetched successfully")
```

### Available Response Methods

| Method | Status Code | Use Case |
|--------|-------------|----------|
| `success()` | 200 | Successful operation |
| `error()` | 400 | Generic error |
| `unauthorized()` | 401 | Authentication required |
| `forbidden()` | 403 | Insufficient permissions |
| `not_found()` | 404 | Resource not found |
| `server_error()` | 500 | Internal server error |

---

## Exception Handling

### Purpose

Provide domain-specific exceptions with consistent error codes and messages.

### Location

`app/exceptions.py`

### Exception Hierarchy

```
AuthServiceException (base)
├── TokenValidationError
├── TokenExpiredError
├── InsufficientPermissionsError
├── KeycloakConnectionError
├── JWKSFetchError
├── UserNotFoundError
└── RefreshTokenError
```

### Custom Exception Classes

#### TokenValidationError

Raised when JWT token validation fails.

```python
from app.exceptions import TokenValidationError

raise TokenValidationError(
    message="Invalid token signature",
    details={"token_type": "access_token"}
)
```

#### InsufficientPermissionsError

Raised when user lacks required role or scope.

```python
from app.exceptions import InsufficientPermissionsError

raise InsufficientPermissionsError(
    required="admin",
    message="Admin role required for this operation"
)
```

#### KeycloakConnectionError

Raised when connection to Keycloak fails.

```python
from app.exceptions import KeycloakConnectionError

raise KeycloakConnectionError(
    message="Keycloak server unreachable",
    details={"url": keycloak_url}
)
```

### Exception Attributes

All exceptions inherit from `AuthServiceException` and include:

- `message`: Human-readable error message
- `error_code`: Machine-readable error code (e.g., "TOKEN_INVALID")
- `details`: Additional context (dict or any JSON-serializable data)
- `status_code`: HTTP status code (default: 400)

### Usage in Code

```python
from app.exceptions import TokenValidationError, InsufficientPermissionsError

async def validate_token(token: str):
    try:
        claims = jwt.decode(token)
        return claims
    except JWTError as e:
        raise TokenValidationError(
            message="Token validation failed",
            details={"error": str(e)}
        )

def check_permissions(user: dict, required_role: str):
    if required_role not in user.get("roles", []):
        raise InsufficientPermissionsError(
            required=required_role,
            details={"user_roles": user.get("roles")}
        )
```

---

## Caching Strategy

### Purpose

Minimize network calls to Keycloak and improve response times by caching frequently accessed data.

### Cache Types

#### 1. JWKS Cache (JWT Validation)

**Purpose**: Cache Keycloak's public keys used for JWT signature verification.

**Configuration**:
```python
JWKS_CACHE_TTL=600        # 10 minutes
JWKS_CACHE_MAXSIZE=2      # Only need current JWKS
```

**Why 10 minutes?**
- JWKS keys rarely change (only during key rotation)
- Keycloak rotates keys infrequently (days/weeks)
- 10 minutes balances freshness vs performance

**Location**: `app/jwt_utils.py`

```python
from cachetools import TTLCache

_jwks_cache = TTLCache(
    maxsize=settings.JWKS_CACHE_MAXSIZE,
    ttl=settings.JWKS_CACHE_TTL
)
```

#### 2. Admin Token Cache

**Purpose**: Cache admin access tokens for Keycloak Admin API calls.

**Configuration**:
```python
ADMIN_TOKEN_CACHE_TTL=300     # 5 minutes
ADMIN_TOKEN_CACHE_MAXSIZE=1   # Only one admin token
```

**Why 5 minutes?**
- Admin tokens expire quickly (typically 5-15 minutes)
- Caching reduces token endpoint calls
- Short TTL ensures fresh tokens

**Location**: `app/keycloak_admin.py`

```python
_token_cache = TTLCache(
    maxsize=settings.ADMIN_TOKEN_CACHE_MAXSIZE,
    ttl=settings.ADMIN_TOKEN_CACHE_TTL
)
```

#### 3. User Info Cache (Future)

**Purpose**: Cache user profile data (email, name, roles).

**Configuration**:
```python
USER_INFO_CACHE_TTL=300       # 5 minutes
USER_INFO_CACHE_MAXSIZE=100   # Cache 100 users
```

**Why 5 minutes?**
- User info can change (role assignments, email updates)
- Moderate TTL balances freshness vs performance
- 100 users covers typical active user count

#### 4. Group Cache (Future)

**Purpose**: Cache Keycloak group hierarchy and members.

**Configuration**:
```python
GROUP_CACHE_TTL=600           # 10 minutes
GROUP_CACHE_MAXSIZE=50        # Cache 50 groups
```

**Why 10 minutes?**
- Group structure changes infrequently
- Group membership updates are not time-critical
- Longer TTL reduces load on Keycloak Admin API

### Cache Management Endpoints

#### Get Cache Info

```bash
GET /cache/info
Authorization: Bearer <admin-token>
```

**Response**:
```json
{
  "jwt_cache": {
    "maxsize": 2,
    "ttl": 600,
    "current_size": 1,
    "keys": ["jwks"]
  },
  "admin_cache": {
    "maxsize": 1,
    "ttl": 300,
    "current_size": 1,
    "keys": ["admin_token"]
  },
  "cache_ttl_config": {
    "jwks_ttl": 600,
    "admin_token_ttl": 300,
    "user_info_ttl": 300,
    "group_ttl": 600
  }
}
```

#### Clear All Caches

```bash
POST /cache/clear
Authorization: Bearer <admin-token>
```

**Response**:
```json
{
  "message": "All caches cleared successfully",
  "cleared": ["jwks_cache", "admin_token_cache"]
}
```

### Cache Tuning Guidelines

#### High-Traffic Scenarios

Increase TTL to reduce Keycloak load:
```bash
JWKS_CACHE_TTL=1800           # 30 minutes
ADMIN_TOKEN_CACHE_TTL=600     # 10 minutes
```

#### Real-Time Requirements

Decrease TTL for fresher data:
```bash
JWKS_CACHE_TTL=300            # 5 minutes
ADMIN_TOKEN_CACHE_TTL=120     # 2 minutes
```

#### Development/Testing

Disable caching for immediate updates:
```bash
JWKS_CACHE_TTL=0              # No caching
ADMIN_TOKEN_CACHE_TTL=0       # No caching
```

### Cache Invalidation

Caches are automatically invalidated when:
- TTL expires (time-based)
- Cache is manually cleared via `/cache/clear` endpoint
- Service restarts

Manual cache clearing is useful for:
- Testing configuration changes
- Forcing fresh data after Keycloak updates
- Debugging authentication issues

---

## Authentication Flow

### 1. Browser Login (OIDC Authorization Code Flow)

```
User → /login → Keycloak Login Page → User Authenticates
→ Keycloak Callback → /callback → Token Exchange
→ Session Cookie Set → User Logged In
```

**Implementation**: `app/routes.py` (`/login`, `/callback`)

### 2. API Authentication (Bearer Token)

```
Client → Get Token from Keycloak → Call API with Bearer Token
→ JWT Validation (JWKS Cache) → Extract Claims → Authorize
```

**Implementation**: `app/auth.py` (`get_user_from_bearer`)

### 3. Composite Authentication

Endpoints accept both session cookies and bearer tokens:

```python
@router.get("/api/data")
async def api_data(user: dict = Depends(require_auth_bearer)):
    # Works with both session and bearer token
    return {"data": "sensitive-data"}
```

**Implementation**: `app/auth.py` (`require_auth_bearer`)

---

## Configuration Management

### Environment Variables

All configuration is loaded from environment variables or `.env` file.

**Location**: `app/config.py`

### Configuration Categories

#### 1. Application Settings

```bash
ENV=dev                           # dev or prod
SESSION_SECRET_KEY=secret-key     # Session encryption key
```

#### 2. Keycloak Settings

```bash
KEYCLOAK_SERVER_URL=http://localhost:8080
KEYCLOAK_REALM=demo
KEYCLOAK_CLIENT_ID=fastapi-app
KEYCLOAK_CLIENT_SECRET=secret
```

#### 3. Cache TTL Settings

```bash
JWKS_CACHE_TTL=600
ADMIN_TOKEN_CACHE_TTL=300
USER_INFO_CACHE_TTL=300
GROUP_CACHE_TTL=600
```

### Settings Validation

Pydantic validates settings on startup:

```python
class Settings(BaseSettings):
    @field_validator("SESSION_SECRET_KEY", mode='before')
    def ensure_session_secret(cls, v, info: ValidationInfo):
        env = info.data.get("ENV", "dev")
        if env == "prod" and not v:
            raise ValueError("SESSION_SECRET_KEY required in prod")
        return v or "dev-secret-change-me"
```

### Accessing Settings

```python
from app.config import settings

print(settings.KEYCLOAK_SERVER_URL)
print(settings.JWKS_CACHE_TTL)
```

---

## Best Practices

### 1. Response Wrappers

✅ **DO**: Use `APIResponse` for all API endpoints
```python
return APIResponse.success(data=result)
```

❌ **DON'T**: Return raw dicts
```python
return {"data": result}  # Inconsistent format
```

### 2. Exception Handling

✅ **DO**: Raise domain-specific exceptions
```python
raise TokenValidationError("Invalid token")
```

❌ **DON'T**: Raise generic exceptions
```python
raise Exception("Token error")  # No context
```

### 3. Caching

✅ **DO**: Use configurable TTL from settings
```python
TTLCache(maxsize=settings.CACHE_MAXSIZE, ttl=settings.CACHE_TTL)
```

❌ **DON'T**: Hardcode cache values
```python
TTLCache(maxsize=10, ttl=600)  # Not configurable
```

### 4. Logging

✅ **DO**: Log with context
```python
logger.warning(f"Token validation failed for user {username}: {error}")
```

❌ **DON'T**: Log without context
```python
logger.warning("Token failed")  # No details
```

---

## Performance Considerations

### Cache Hit Rates

Monitor cache effectiveness:
- JWKS cache: Should have >95% hit rate
- Admin token cache: Should have >90% hit rate

### Response Times

Target response times:
- JWT validation (cached): <10ms
- JWT validation (uncached): <100ms
- Admin API calls (cached): <50ms
- Admin API calls (uncached): <500ms

### Scaling

For horizontal scaling:
- Use stateless bearer tokens (no session state)
- Or use shared session store (Redis)
- Cache is per-instance (not shared)

---

## Security Considerations

### 1. Token Validation

- Always validate JWT signature using JWKS
- Check expiration (exp claim)
- Verify issuer (iss claim)
- Validate audience (aud claim) when applicable

### 2. Cache Security

- JWKS cache contains public keys only (safe to cache)
- Admin token cache contains sensitive tokens (secure storage)
- Clear caches on security incidents

### 3. Error Messages

- Don't leak sensitive info in error messages
- Use generic messages for auth failures
- Log detailed errors server-side only

---

## Monitoring and Debugging

### Health Check

```bash
GET /health
```

Returns `{"status": "ok"}` when service is running.

### Cache Monitoring

```bash
GET /cache/info
```

Returns cache statistics for debugging.

### Log Levels

```python
# Development
logging.basicConfig(level=logging.DEBUG)

# Production
logging.basicConfig(level=logging.INFO)
```

---

## Future Enhancements

1. **User Info Caching**: Cache user profile data
2. **Group Caching**: Cache Keycloak group hierarchy
3. **Rate Limiting**: Protect against abuse
4. **Metrics**: Prometheus metrics for monitoring
5. **Distributed Caching**: Redis for shared cache across instances
6. **Circuit Breaker**: Fail gracefully when Keycloak is down

---

## Summary

The AS-03 backend is architected for:

- **Consistency**: Standardized responses and exceptions
- **Performance**: Multi-level caching with configurable TTL
- **Security**: Robust JWT validation and RBAC
- **Maintainability**: Clear separation of concerns
- **Observability**: Comprehensive logging and monitoring

All components are designed to be production-ready, scalable, and easy to maintain.
