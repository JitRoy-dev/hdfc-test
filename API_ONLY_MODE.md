# API-Only Mode

## Overview

The application is now separated into two distinct route modules:

1. **API Routes** (`app/routes.py`) - RESTful JSON API endpoints
2. **Web UI Routes** (`app/web_routes.py`) - HTML pages and browser OAuth flow

By default, both are enabled. If you only need the API (no web interface), you can disable the web routes.

---

## File Structure

```
app/
├── routes.py          # API endpoints (JSON responses)
├── web_routes.py      # Web UI endpoints (HTML/redirects)
└── main.py            # FastAPI app with both routers
```

---

## API Routes (routes.py)

**Purpose**: RESTful API for programmatic access

**Endpoints**:
- `GET /health` - Health check
- `GET /me` - Get current user info
- `POST /refresh` - Refresh access token
- `GET /ceo` - CEO dashboard data (JSON)
- `GET /api/data` - Example protected API
- `GET /cache/info` - Cache statistics (admin)
- `POST /cache/clear` - Clear caches (admin)

**Authentication**: Bearer token in `Authorization` header or session cookie

**Response Format**: JSON (most use standardized wrapper)

**Use Case**: 
- Frontend applications (React, Vue, Angular)
- Mobile apps
- Service-to-service communication
- API integrations

---

## Web UI Routes (web_routes.py)

**Purpose**: Browser-based login and HTML dashboards

**Endpoints**:
- `GET /` - Homepage (HTML)
- `GET /login` - Redirect to Keycloak login
- `GET /callback` - OAuth callback handler
- `GET /logout` - Logout and redirect
- `GET /manager` - Manager dashboard (HTML)

**Authentication**: Session cookies (httpOnly)

**Response Format**: HTML or redirects

**Use Case**:
- Browser-based login flow
- Quick testing/debugging
- Admin dashboards
- Internal tools

---

## Disabling Web UI Routes

If you only need the API (no HTML pages), comment out the web router in `app/main.py`:

### Option 1: Comment Out Web Router

```python
# app/main.py

# Register API Routes (always included)
app.include_router(api_router, tags=["API"])

# Register Web UI Routes (optional - comment out if you only need API)
# app.include_router(web_router, tags=["Web UI"])  # <-- Commented out
```

### Option 2: Environment Variable (Future Enhancement)

Add to `.env`:
```env
ENABLE_WEB_UI=false
```

Then in `main.py`:
```python
# Register API Routes
app.include_router(api_router, tags=["API"])

# Conditionally register Web UI Routes
if settings.ENABLE_WEB_UI:
    app.include_router(web_router, tags=["Web UI"])
```

---

## API-Only Authentication Flow

When web routes are disabled, use this flow:

### 1. Get Access Token from Keycloak

```bash
# Direct token request (client credentials)
curl -X POST "http://localhost:8080/realms/demo/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=fastapi-app" \
  -d "client_secret=your-secret"

# Response
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cC...",
  "expires_in": 900,
  "token_type": "Bearer"
}
```

### 2. Use Token in API Calls

```bash
# Store token
TOKEN="eyJhbGciOiJSUzI1NiIsInR5cC..."

# Call protected API
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/me

# Response
{
  "success": true,
  "message": "User information retrieved successfully",
  "data": {
    "sub": "user-uuid",
    "email": "user@example.com",
    "preferred_username": "username",
    "roles": ["manager", "user"]
  },
  "metadata": {
    "timestamp": "2026-02-11T10:30:00Z",
    "version": "1.0"
  }
}
```

### 3. Refresh Token When Expired

```bash
# When you get 401 Unauthorized
curl -X POST http://localhost:8000/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "your-refresh-token"}'

# Response
{
  "access_token": "new-token...",
  "refresh_token": "new-refresh-token...",
  "expires_in": 900,
  "token_type": "Bearer"
}
```

---

## Benefits of Separation

### API Routes Only
✅ Cleaner API surface  
✅ No HTML rendering overhead  
✅ Easier to document (OpenAPI/Swagger)  
✅ Better for microservices  
✅ Simpler deployment  

### With Web UI Routes
✅ Quick testing in browser  
✅ Admin dashboards  
✅ OAuth flow visualization  
✅ User-friendly login  
✅ Internal tools  

---

## OpenAPI Documentation

With both routers, endpoints are grouped by tags:

**Swagger UI**: `http://localhost:8000/docs`

**API Endpoints** (tag: "API"):
- `/health`
- `/me`
- `/refresh`
- `/ceo`
- `/api/data`
- `/cache/info`
- `/cache/clear`

**Web UI Endpoints** (tag: "Web UI"):
- `/`
- `/login`
- `/callback`
- `/logout`
- `/manager`

---

## Production Recommendations

### API-Only Deployment
If deploying as a pure API service:
1. Comment out web router in `main.py`
2. Remove session middleware (not needed)
3. Only allow bearer token authentication
4. Disable CORS for non-browser clients

### Full Deployment
If you need both API and web UI:
1. Keep both routers enabled
2. Use separate subdomains:
   - `api.example.com` → API routes
   - `app.example.com` → Web UI routes
3. Configure CORS appropriately

---

## Testing

### Test API Routes Only

```bash
# Health check
curl http://localhost:8000/health

# Get token from Keycloak
TOKEN=$(curl -s -X POST \
  http://localhost:8080/realms/demo/protocol/openid-connect/token \
  -d "client_id=fastapi-app" \
  -d "client_secret=your-secret" \
  -d "grant_type=client_credentials" | jq -r '.access_token')

# Test API endpoints
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/me
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/data
```

### Test Web UI Routes

```bash
# Open in browser
open http://localhost:8000/
open http://localhost:8000/login
```

---

## Migration Guide

### From Monolithic to API-Only

**Before** (all routes in `routes.py`):
```python
# routes.py had both API and HTML routes mixed together
```

**After** (separated):
```python
# routes.py - API only (JSON responses)
# web_routes.py - Web UI only (HTML/redirects)
# main.py - includes both routers
```

**To disable web UI**:
```python
# main.py
app.include_router(api_router, tags=["API"])
# app.include_router(web_router, tags=["Web UI"])  # Commented out
```

---

## Summary

✅ **API routes** (`routes.py`) - For programmatic access  
✅ **Web UI routes** (`web_routes.py`) - For browser-based login  
✅ **Both enabled by default** - Comment out web router if not needed  
✅ **Clean separation** - Easy to maintain and deploy  

**Current Status**: Both API and Web UI routes are enabled. To use API-only mode, comment out the web router in `main.py`.

---

**Last Updated**: February 11, 2026  
**Version**: 1.0
