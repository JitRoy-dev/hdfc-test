# AS-03 Backend - API Contracts

## Overview

This document defines all API endpoints, request/response formats, authentication requirements, and error handling for the AS-03 authentication backend service.

**Base URL**: `http://localhost:8000` (development) or `https://your-domain.com` (production)

**API Version**: 1.0

**Last Updated**: February 10, 2026

---

## Table of Contents

1. [Authentication](#authentication)
2. [Public Endpoints](#public-endpoints)
3. [Protected Endpoints](#protected-endpoints)
4. [Admin Endpoints](#admin-endpoints)
5. [Error Responses](#error-responses)
6. [Response Formats](#response-formats)
7. [Status Codes](#status-codes)

---

## Authentication

### Authentication Methods

The API supports two authentication methods:

#### 1. Session Cookies (Browser)
- Used for browser-based login flows
- Automatically managed by the browser
- Set after successful OAuth login

#### 2. Bearer Tokens (API)
- Used for API-to-API communication
- Include in `Authorization` header
- Format: `Authorization: Bearer <access_token>`

### Getting an Access Token

```bash
# Client Credentials Grant (Service-to-Service)
curl -X POST "http://localhost:8080/realms/demo/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=fastapi-app" \
  -d "client_secret=your-client-secret"

# Response
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cC...",
  "expires_in": 900,
  "refresh_expires_in": 0,
  "token_type": "Bearer",
  "not-before-policy": 0,
  "scope": "profile email"
}
```

---

## Public Endpoints

### 1. Homepage

**Endpoint**: `GET /`

**Description**: Landing page showing login link or user info

**Authentication**: Optional (session cookie)

**Request**:
```http
GET / HTTP/1.1
Host: localhost:8000
```

**Response (Not Authenticated)**:
```html
<a href="/login">Login with Keycloak</a>
```

**Response (Authenticated)**:
```html
<h1>Welcome, john.smith</h1>
<p>Roles: ['manager', 'user']</p>
<ul>
    <li><a href="/manager">Manager Dashboard</a></li>
    <li><a href="/logout">Logout</a></li>
</ul>
```

**Status Codes**:
- `200 OK` - Success

---

### 2. Login

**Endpoint**: `GET /login`

**Description**: Initiates OAuth login flow, redirects to Keycloak

**Authentication**: None

**Request**:
```http
GET /login HTTP/1.1
Host: localhost:8000
```

**Response**:
```http
HTTP/1.1 307 Temporary Redirect
Location: http://localhost:8080/realms/demo/protocol/openid-connect/auth?...
```

**Status Codes**:
- `307 Temporary Redirect` - Redirects to Keycloak login page

**Flow**:
1. User clicks login
2. Redirected to Keycloak
3. User authenticates
4. Redirected back to `/callback`
5. Session cookie set
6. Redirected to homepage

---

### 3. OAuth Callback

**Endpoint**: `GET /callback`

**Description**: OAuth callback handler (internal use)

**Authentication**: None (handled by OAuth flow)

**Request**:
```http
GET /callback?code=abc123&state=xyz789 HTTP/1.1
Host: localhost:8000
```

**Response (Success)**:
```http
HTTP/1.1 307 Temporary Redirect
Location: /
Set-Cookie: session=...; HttpOnly; Path=/
```

**Response (Error)**:
```html
Auth failed: <error_message>
```

**Status Codes**:
- `307 Temporary Redirect` - Success, redirects to homepage
- `400 Bad Request` - Authentication failed

---

### 4. Logout

**Endpoint**: `GET /logout`

**Description**: Clears session and redirects to Keycloak logout

**Authentication**: Optional (session cookie)

**Request**:
```http
GET /logout HTTP/1.1
Host: localhost:8000
Cookie: session=...
```

**Response**:
```http
HTTP/1.1 307 Temporary Redirect
Location: http://localhost:8080/realms/demo/protocol/openid-connect/logout?...
```

**Status Codes**:
- `307 Temporary Redirect` - Redirects to Keycloak logout

**Flow**:
1. User clicks logout
2. Session cleared
3. Redirected to Keycloak logout
4. Keycloak clears its session
5. Redirected back to homepage

---

### 5. Health Check

**Endpoint**: `GET /health`

**Description**: Health check for monitoring and readiness probes

**Authentication**: None

**Request**:
```http
GET /health HTTP/1.1
Host: localhost:8000
```

**Response**:
```json
{
  "status": "ok"
}
```

**Status Codes**:
- `200 OK` - Service is healthy

**Usage**:
```yaml
# Kubernetes readiness probe
readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
```

---

## Protected Endpoints

These endpoints require authentication (session cookie or bearer token).

### 6. Get Current User

**Endpoint**: `GET /me`

**Description**: Get authenticated user's profile information

**Authentication**: Required (session or bearer token)

**Request**:
```http
GET /me HTTP/1.1
Host: localhost:8000
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cC...
```

**Response**:
```json
{
  "success": true,
  "message": "User information retrieved successfully",
  "data": {
    "sub": "550e8400-e29b-41d4-a716-446655440000",
    "email": "john.smith@example.com",
    "preferred_username": "john.smith",
    "name": "John Smith",
    "roles": ["manager", "user"],
    "groups": ["sales-team", "backend-squad"]
  },
  "metadata": {
    "timestamp": "2026-02-10T10:30:00Z",
    "version": "1.0",
    "ttl": {
      "value": 300,
      "unit": "seconds",
      "expires_at": "2026-02-10T10:35:00Z",
      "human_readable": "5 minutes"
    }
  }
}
```

**Response Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Always true for successful responses |
| `message` | string | Success message |
| `data` | object | User information object |
| `data.sub` | string | Unique user ID from Keycloak |
| `data.email` | string | User's email address |
| `data.preferred_username` | string | Username/login name |
| `data.name` | string | Full name (optional) |
| `data.roles` | array | List of realm roles |
| `data.groups` | array | List of groups user belongs to |
| `metadata` | object | Response metadata |
| `metadata.timestamp` | string | ISO-8601 timestamp |
| `metadata.version` | string | API version |
| `metadata.ttl` | object | Cache TTL information |

**Status Codes**:
- `200 OK` - Success
- `401 Unauthorized` - Not authenticated

**Example (cURL)**:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/me
```

**Frontend Usage**:
```javascript
// Fetch current user on app load
async function loadCurrentUser() {
  const response = await fetch('/me', {
    credentials: 'include',  // Include session cookie
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('access_token')}`
    }
  });
  
  if (response.ok) {
    const user = await response.json();
    console.log('Current user:', user);
    return user;
  }
}
```

---

### 7. Token Refresh

**Endpoint**: `POST /refresh`

**Description**: Refresh an expired access token using a refresh token

**Authentication**: None (refresh token in body)

**Request**:
```http
POST /refresh HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cC..."
}
```

**Request Body**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `refresh_token` | string | Yes | Refresh token from login |

**Response (Success)**:
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cC...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cC...",
  "expires_in": 900,
  "token_type": "Bearer"
}
```

**Response Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `access_token` | string | New short-lived access token |
| `refresh_token` | string | New or same refresh token |
| `expires_in` | integer | Token lifetime in seconds |
| `token_type` | string | Always "Bearer" |

**Status Codes**:
- `200 OK` - Token refreshed successfully
- `400 Bad Request` - Missing refresh_token
- `401 Unauthorized` - Invalid or expired refresh_token
- `500 Internal Server Error` - Token refresh failed

**Example (cURL)**:
```bash
curl -X POST http://localhost:8000/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cC..."}'
```

**Frontend Usage**:
```javascript
async function refreshAccessToken() {
  const response = await fetch('/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      refresh_token: localStorage.getItem('refresh_token')
    })
  });
  
  if (response.ok) {
    const data = await response.json();
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    return data.access_token;
  }
  
  // Refresh failed, redirect to login
  window.location.href = '/login';
}
```

---

### 8. Manager Dashboard

**Endpoint**: `GET /manager`

**Description**: Manager dashboard (HTML page)

**Authentication**: Required (session or bearer token)

**Required Role**: `manager`

**Request**:
```http
GET /manager HTTP/1.1
Host: localhost:8000
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cC...
```

**Response**:
```html
<h1>Manager Dashboard</h1>
<p>Welcome, Admin!</p>
```

**Status Codes**:
- `200 OK` - Success
- `401 Unauthorized` - Not authenticated
- `403 Forbidden` - Missing 'manager' role

---

### 9. CEO Dashboard

**Endpoint**: `GET /ceo`

**Description**: CEO dashboard with teams and employees data

**Authentication**: Required (session or bearer token)

**Required Role**: `ceo`

**Request**:
```http
GET /ceo HTTP/1.1
Host: localhost:8000
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cC...
```

**Response**:
```json
{
  "ceo": {
    "username": "john.ceo",
    "email": "john.ceo@example.com",
    "name": "John CEO"
  },
  "teams": [
    {
      "id": "team-uuid-1",
      "name": "Engineering",
      "path": "/Engineering",
      "subGroupCount": 2,
      "members": [
        {
          "id": "user-uuid-1",
          "username": "alice.dev",
          "email": "alice@example.com",
          "firstName": "Alice",
          "lastName": "Developer"
        }
      ],
      "subGroups": [
        {
          "id": "subteam-uuid-1",
          "name": "Backend",
          "path": "/Engineering/Backend",
          "subGroupCount": 0,
          "members": [...],
          "subGroups": []
        }
      ]
    }
  ],
  "totalTeams": 3,
  "totalEmployees": 25
}
```

**Response Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `ceo` | object | Current CEO's information |
| `ceo.username` | string | CEO's username |
| `ceo.email` | string | CEO's email |
| `ceo.name` | string | CEO's full name |
| `teams` | array | List of top-level teams |
| `teams[].id` | string | Team/group UUID |
| `teams[].name` | string | Team name |
| `teams[].path` | string | Full group path |
| `teams[].subGroupCount` | integer | Number of subgroups |
| `teams[].members` | array | Direct members of this team |
| `teams[].subGroups` | array | Nested subgroups (recursive) |
| `totalTeams` | integer | Total number of top-level teams |
| `totalEmployees` | integer | Total number of employees across all teams |

**Status Codes**:
- `200 OK` - Success
- `401 Unauthorized` - Not authenticated
- `403 Forbidden` - Missing 'ceo' role
- `500 Internal Server Error` - Failed to fetch teams data

**Example (cURL)**:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/ceo
```

---

### 10. API Data (Example Protected Endpoint)

**Endpoint**: `GET /api/data`

**Description**: Example protected API endpoint

**Authentication**: Required (session or bearer token)

**Required Role**: `manager`

**Request**:
```http
GET /api/data HTTP/1.1
Host: localhost:8000
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cC...
```

**Response**:
```json
{
  "data": "sensitive-data",
  "user": "john.smith"
}
```

**Status Codes**:
- `200 OK` - Success
- `401 Unauthorized` - Not authenticated
- `403 Forbidden` - Missing 'manager' role

---

## Admin Endpoints

These endpoints require the `admin` role.

### 11. Get Cache Info

**Endpoint**: `GET /cache/info`

**Description**: Get cache statistics for monitoring

**Authentication**: Required (bearer token)

**Required Role**: `admin`

**Request**:
```http
GET /cache/info HTTP/1.1
Host: localhost:8000
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cC...
```

**Response**:
```json
{
  "success": true,
  "message": "Cache information retrieved successfully",
  "data": {
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
      "jwks_ttl_human": "10 minutes",
      "admin_token_ttl": 300,
      "admin_token_ttl_human": "5 minutes",
      "user_info_ttl": 300,
      "user_info_ttl_human": "5 minutes",
      "group_ttl": 600,
      "group_ttl_human": "10 minutes"
    }
  },
  "metadata": {
    "timestamp": "2026-02-10T10:30:00Z",
    "version": "1.0",
    "ttl": {
      "value": 60,
      "unit": "seconds",
      "expires_at": "2026-02-10T10:31:00Z",
      "human_readable": "60 seconds"
    }
  }
}
```

**Response Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `jwt_cache` | object | JWKS cache statistics |
| `jwt_cache.maxsize` | integer | Maximum cache entries |
| `jwt_cache.ttl` | integer | Time-to-live in seconds |
| `jwt_cache.current_size` | integer | Current number of entries |
| `jwt_cache.keys` | array | List of cache keys |
| `admin_cache` | object | Admin token cache statistics |
| `cache_ttl_config` | object | Configured TTL values |

**Status Codes**:
- `200 OK` - Success
- `401 Unauthorized` - Not authenticated
- `403 Forbidden` - Missing 'admin' role

**Example (cURL)**:
```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/cache/info
```

**Use Cases**:
- Monitoring cache performance
- Debugging authentication issues
- Verifying cache configuration
- Performance tuning

---

### 12. Clear Caches

**Endpoint**: `POST /cache/clear`

**Description**: Clear all caches (JWKS, admin token)

**Authentication**: Required (bearer token)

**Required Role**: `admin`

**Request**:
```http
POST /cache/clear HTTP/1.1
Host: localhost:8000
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cC...
```

**Response**:
```json
{
  "success": true,
  "message": "Caches cleared successfully",
  "data": {
    "message": "All caches cleared successfully",
    "cleared": ["jwks_cache", "admin_token_cache"],
    "cache_ttl": {
      "jwks": "600s (10min)",
      "admin_token": "300s (5min)"
    }
  },
  "metadata": {
    "timestamp": "2026-02-10T10:30:00Z",
    "version": "1.0"
  }
}
```

**Response Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `message` | string | Success message |
| `cleared` | array | List of cleared caches |

**Status Codes**:
- `200 OK` - Caches cleared successfully
- `401 Unauthorized` - Not authenticated
- `403 Forbidden` - Missing 'admin' role

**Example (cURL)**:
```bash
curl -X POST \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/cache/clear
```

**Use Cases**:
- After Keycloak key rotation
- After configuration changes
- Testing authentication flows
- Forcing fresh data fetch

---

## Error Responses

### Standard Error Format

All error responses follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Errors

#### 401 Unauthorized

**Cause**: Missing or invalid authentication

**Response**:
```json
{
  "detail": "Not authenticated"
}
```

**Example**:
```bash
# Missing Authorization header
curl http://localhost:8000/me
# Response: 401 Unauthorized
```

---

#### 403 Forbidden

**Cause**: Insufficient permissions (missing required role)

**Response**:
```json
{
  "detail": "Forbidden: 'admin' role required"
}
```

**Example**:
```bash
# User has 'manager' role but endpoint requires 'admin'
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/cache/info
# Response: 403 Forbidden
```

---

#### 400 Bad Request

**Cause**: Invalid request (missing required fields, malformed data)

**Response**:
```json
{
  "detail": "refresh_token required in request body"
}
```

**Example**:
```bash
# Missing refresh_token field
curl -X POST http://localhost:8000/refresh \
  -H "Content-Type: application/json" \
  -d '{}'
# Response: 400 Bad Request
```

---

#### 500 Internal Server Error

**Cause**: Server-side error (Keycloak connection failure, unexpected error)

**Response**:
```json
{
  "detail": "Failed to fetch teams data: Connection timeout"
}
```

**Example**:
```bash
# Keycloak server is down
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/ceo
# Response: 500 Internal Server Error
```

---

## Response Formats

### Standardized API Response Wrapper

Most API endpoints (except HTML and redirect responses) use a standardized response wrapper format:

**Success Response**:
```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": {
    // Actual response data here
  },
  "metadata": {
    "timestamp": "2026-02-10T10:30:00Z",
    "version": "1.0",
    "ttl": {
      "value": 300,
      "unit": "seconds",
      "expires_at": "2026-02-10T10:35:00Z",
      "human_readable": "5 minutes"
    }
  }
}
```

**Response Wrapper Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Always `true` for successful responses |
| `message` | string | Human-readable success message |
| `data` | object/array | Actual response payload |
| `metadata` | object | Response metadata |
| `metadata.timestamp` | string | ISO-8601 timestamp when response was generated |
| `metadata.version` | string | API version (currently "1.0") |
| `metadata.ttl` | object | Cache TTL information (optional) |
| `metadata.ttl.value` | integer | TTL value in seconds |
| `metadata.ttl.unit` | string | Always "seconds" |
| `metadata.ttl.expires_at` | string | ISO-8601 timestamp when data expires |
| `metadata.ttl.human_readable` | string | Human-readable TTL (e.g., "5 minutes") |

**Endpoints Using Wrapper**:
- `GET /me` - User information
- `GET /cache/info` - Cache statistics
- `POST /cache/clear` - Cache clear confirmation

**Endpoints NOT Using Wrapper**:
- `GET /` - HTML homepage
- `GET /login` - Redirect to Keycloak
- `GET /callback` - OAuth callback redirect
- `GET /logout` - Redirect to Keycloak logout
- `GET /manager` - HTML dashboard
- `GET /ceo` - Direct JSON response (no wrapper)
- `GET /api/data` - Direct JSON response (no wrapper)
- `GET /health` - Simple status object
- `POST /refresh` - Direct token response from Keycloak

### JSON Response

Most API endpoints return JSON:

```json
{
  "field1": "value1",
  "field2": 123,
  "field3": ["array", "values"],
  "field4": {
    "nested": "object"
  }
}
```

### HTML Response

Some endpoints return HTML (homepage, dashboards):

```html
<h1>Welcome, john.smith</h1>
<p>Roles: ['manager', 'user']</p>
```

### Redirect Response

Login/logout endpoints return redirects:

```http
HTTP/1.1 307 Temporary Redirect
Location: http://localhost:8080/realms/demo/protocol/openid-connect/auth?...
```

---

## Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| `200 OK` | Success | Request completed successfully |
| `307 Temporary Redirect` | Redirect | OAuth flow, login/logout redirects |
| `400 Bad Request` | Invalid request | Missing fields, malformed data |
| `401 Unauthorized` | Not authenticated | Missing or invalid token/session |
| `403 Forbidden` | Insufficient permissions | Missing required role |
| `500 Internal Server Error` | Server error | Keycloak connection failure, unexpected error |

---

## Authentication Flow Examples

### Browser Login Flow

```
1. User visits homepage
   GET / → 200 OK (shows login link)

2. User clicks login
   GET /login → 307 Redirect (to Keycloak)

3. User authenticates at Keycloak
   (Keycloak handles authentication)

4. Keycloak redirects back
   GET /callback?code=abc123 → 307 Redirect (to homepage)
   Set-Cookie: session=...; HttpOnly

5. User accesses protected page
   GET /manager → 200 OK (with session cookie)
```

### API Token Flow

```
1. Service gets token from Keycloak
   POST http://localhost:8080/realms/demo/protocol/openid-connect/token
   → 200 OK (returns access_token)

2. Service calls protected API
   GET /api/data
   Authorization: Bearer <access_token>
   → 200 OK (returns data)

3. Token expires, service refreshes
   POST /refresh
   Body: {"refresh_token": "..."}
   → 200 OK (returns new access_token)

4. Service continues with new token
   GET /api/data
   Authorization: Bearer <new_access_token>
   → 200 OK (returns data)
```

---

## Rate Limiting

**Current Status**: Not implemented

**Recommendation**: Implement rate limiting for production:
- `/login`: 5 requests per minute per IP
- `/refresh`: 10 requests per minute per user
- `/cache/clear`: 1 request per minute per admin

---

## CORS Configuration

### Development

All origins allowed:
```python
allow_origins = ["*"]
```

### Production

Specific origins only:
```python
allow_origins = [
    "https://app.example.com",
    "https://admin.example.com"
]
```

**Allowed Methods**: `GET`, `POST`, `OPTIONS`

**Allowed Headers**: `Authorization`, `Content-Type`

**Credentials**: Allowed (cookies, auth headers)

---

## Versioning

**Current Version**: 1.0

**Versioning Strategy**: URL-based (future)

**Example**:
```
/v1/me
/v2/me
```

**Backward Compatibility**: All v1 endpoints will be supported for at least 6 months after v2 release.

---

## Testing

### Example Test Suite

```bash
# Health check
curl http://localhost:8000/health

# Get token
TOKEN=$(curl -s -X POST \
  http://localhost:8080/realms/demo/protocol/openid-connect/token \
  -d "client_id=fastapi-app" \
  -d "client_secret=your-secret" \
  -d "grant_type=client_credentials" | jq -r '.access_token')

# Test /me endpoint
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/me

# Test /api/data endpoint
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/data

# Test cache info (requires admin role)
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/cache/info
```

---

## Postman Collection

### Import Collection

```json
{
  "info": {
    "name": "AS-03 Backend API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Health Check",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "{{base_url}}/health",
          "host": ["{{base_url}}"],
          "path": ["health"]
        }
      }
    },
    {
      "name": "Get Current User",
      "request": {
        "method": "GET",
        "header": [
          {
            "key": "Authorization",
            "value": "Bearer {{access_token}}"
          }
        ],
        "url": {
          "raw": "{{base_url}}/me",
          "host": ["{{base_url}}"],
          "path": ["me"]
        }
      }
    }
  ],
  "variable": [
    {
      "key": "base_url",
      "value": "http://localhost:8000"
    },
    {
      "key": "access_token",
      "value": ""
    }
  ]
}
```

---

## OpenAPI Specification

### Generate OpenAPI Docs

FastAPI automatically generates OpenAPI documentation:

**Swagger UI**: `http://localhost:8000/docs`

**ReDoc**: `http://localhost:8000/redoc`

**OpenAPI JSON**: `http://localhost:8000/openapi.json`

---

## Support

For API questions or issues:
1. Check this API contracts document
2. Review OpenAPI docs at `/docs`
3. Check logs for detailed error messages
4. Contact development team

---

## Changelog

### Version 1.0 (February 10, 2026)
- Initial API release
- All endpoints documented
- Authentication flows defined
- Error handling standardized

---

**Document Version**: 1.0  
**Last Updated**: February 10, 2026  
**Maintained By**: AS-03 Backend Team
