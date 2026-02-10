# AS-03 Backend - API Quick Reference

## Base URL
```
Development: http://localhost:8000
Production:  https://your-domain.com
```

---

## Quick Reference Table

| Endpoint | Method | Auth | Role | Description |
|----------|--------|------|------|-------------|
| `/` | GET | Optional | - | Homepage |
| `/login` | GET | No | - | Start OAuth login |
| `/callback` | GET | No | - | OAuth callback |
| `/logout` | GET | Optional | - | Logout |
| `/health` | GET | No | - | Health check |
| `/me` | GET | **Yes** | - | Get current user |
| `/refresh` | POST | No | - | Refresh token |
| `/manager` | GET | **Yes** | manager | Manager dashboard |
| `/ceo` | GET | **Yes** | ceo | CEO dashboard |
| `/api/data` | GET | **Yes** | manager | Example API |
| `/cache/info` | GET | **Yes** | admin | Cache statistics |
| `/cache/clear` | POST | **Yes** | admin | Clear caches |

---

## Authentication

### Bearer Token
```bash
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cC...
```

### Get Token
```bash
curl -X POST "http://localhost:8080/realms/demo/protocol/openid-connect/token" \
  -d "grant_type=client_credentials" \
  -d "client_id=fastapi-app" \
  -d "client_secret=your-secret"
```

---

## Common Requests

### Get Current User
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/me
```

**Response**:
```json
{
  "sub": "user-uuid",
  "email": "john@example.com",
  "preferred_username": "john.smith",
  "name": "John Smith",
  "roles": ["manager", "user"],
  "groups": ["sales-team"]
}
```

---

### Refresh Token
```bash
curl -X POST http://localhost:8000/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cC..."}'
```

**Response**:
```json
{
  "access_token": "new-token",
  "refresh_token": "new-refresh-token",
  "expires_in": 900,
  "token_type": "Bearer"
}
```

---

### CEO Dashboard
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/ceo
```

**Response**:
```json
{
  "ceo": {
    "username": "john.ceo",
    "email": "john.ceo@example.com",
    "name": "John CEO"
  },
  "teams": [...],
  "totalTeams": 3,
  "totalEmployees": 25
}
```

---

### Cache Info (Admin)
```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/cache/info
```

**Response**:
```json
{
  "jwt_cache": {
    "maxsize": 2,
    "ttl": 600,
    "current_size": 1
  },
  "admin_cache": {
    "maxsize": 1,
    "ttl": 300,
    "current_size": 1
  }
}
```

---

### Clear Caches (Admin)
```bash
curl -X POST \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/cache/clear
```

**Response**:
```json
{
  "message": "All caches cleared successfully",
  "cleared": ["jwks_cache", "admin_token_cache"]
}
```

---

## Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 307 | Redirect (OAuth) |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden (missing role) |
| 500 | Server Error |

---

## Error Response Format

```json
{
  "detail": "Error message"
}
```

---

## Frontend Integration

### Load Current User
```javascript
async function loadCurrentUser() {
  const response = await fetch('/me', {
    credentials: 'include',
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('access_token')}`
    }
  });
  
  if (response.ok) {
    return await response.json();
  }
}
```

### Refresh Token
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
    return data.access_token;
  }
}
```

### API Call with Auto-Refresh
```javascript
async function callAPI(endpoint) {
  let token = localStorage.getItem('access_token');
  
  let response = await fetch(endpoint, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  
  // If 401, try refresh
  if (response.status === 401) {
    token = await refreshAccessToken();
    if (!token) {
      window.location.href = '/login';
      return;
    }
    
    // Retry with new token
    response = await fetch(endpoint, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
  }
  
  return response;
}
```

---

## Testing Script

```bash
#!/bin/bash

BASE_URL="http://localhost:8000"
KEYCLOAK_URL="http://localhost:8080"
REALM="demo"
CLIENT_ID="fastapi-app"
CLIENT_SECRET="your-secret"

# Get token
TOKEN=$(curl -s -X POST \
  "$KEYCLOAK_URL/realms/$REALM/protocol/openid-connect/token" \
  -d "grant_type=client_credentials" \
  -d "client_id=$CLIENT_ID" \
  -d "client_secret=$CLIENT_SECRET" | jq -r '.access_token')

echo "Token: $TOKEN"

# Test health
echo "\n=== Health Check ==="
curl -s "$BASE_URL/health" | jq

# Test /me
echo "\n=== Current User ==="
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/me" | jq

# Test /api/data
echo "\n=== API Data ==="
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/data" | jq

# Test cache info (if admin)
echo "\n=== Cache Info ==="
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/cache/info" | jq
```

---

## Postman Environment

```json
{
  "name": "AS-03 Backend",
  "values": [
    {
      "key": "base_url",
      "value": "http://localhost:8000",
      "enabled": true
    },
    {
      "key": "keycloak_url",
      "value": "http://localhost:8080",
      "enabled": true
    },
    {
      "key": "realm",
      "value": "demo",
      "enabled": true
    },
    {
      "key": "client_id",
      "value": "fastapi-app",
      "enabled": true
    },
    {
      "key": "client_secret",
      "value": "your-secret",
      "enabled": true
    },
    {
      "key": "access_token",
      "value": "",
      "enabled": true
    }
  ]
}
```

---

## OpenAPI Docs

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

---

## Support

📖 **Full Documentation**: See `API_CONTRACTS.md`

🔧 **Architecture**: See `ARCHITECTURE.md`

⚡ **Quick Start**: See `QUICK_START.md`
