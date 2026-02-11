# Security Model

## Token Handling

### Session-Based Authentication (Browser)
- Tokens are stored server-side in session (secure)
- Session ID sent via httpOnly cookie (not accessible to JavaScript)
- Tokens never exposed in API responses
- Frontend doesn't need to handle tokens

### Bearer Token Authentication (API)
- Frontend/mobile apps send tokens in `Authorization: Bearer <token>` header
- Tokens obtained during initial OAuth flow
- Backend validates tokens on each request
- Tokens never returned in API responses (except during OAuth callback)

## Authentication Flow

### Browser Login
1. User clicks "Login with Keycloak"
2. Redirected to Keycloak login page
3. After login, redirected back to `/callback`
4. Backend exchanges code for tokens
5. Tokens stored in server-side session
6. Session ID sent to browser as httpOnly cookie
7. Browser sends cookie with each request

### API Authentication
1. Client obtains tokens via OAuth flow
2. Client stores tokens securely (mobile: keychain, web: secure storage)
3. Client sends `Authorization: Bearer <token>` header with each request
4. Backend validates token and extracts user info
5. No tokens returned in responses

## Security Best Practices

### ✅ What We Do
- Store tokens server-side in session (not in localStorage)
- Use httpOnly cookies (not accessible to JavaScript)
- Validate tokens on every request
- Never expose tokens in API responses
- Use HTTPS in production
- CSRF protection with state parameter
- Client secret kept on backend only

### ❌ What We Don't Do
- Don't store tokens in localStorage (XSS vulnerable)
- Don't send tokens in URL parameters
- Don't log tokens
- Don't expose tokens in API responses
- Don't send client_secret to frontend

## Endpoints

### Public Endpoints
- `GET /` - Homepage
- `GET /login` - Redirect to Keycloak
- `GET /callback` - OAuth callback (stores tokens in session)
- `GET /health` - Health check

### Protected Endpoints (Session or Bearer Token)
- `GET /me` - Get user info (no tokens in response)
- `GET /logout` - Logout
- `POST /refresh` - Refresh access token

### Role-Protected Endpoints
- `GET /manager` - Requires 'manager' role
- `GET /ceo` - Requires 'ceo' role
- `GET /api/data` - Requires 'manager' role
- `GET /cache/info` - Requires 'admin' role
- `POST /cache/clear` - Requires 'admin' role

## Token Refresh

When access token expires:
1. Frontend detects 401 Unauthorized
2. Frontend calls `POST /refresh` with refresh_token
3. Backend exchanges refresh_token for new access_token
4. Backend returns new tokens
5. Frontend updates stored tokens

Note: Refresh tokens are long-lived, access tokens are short-lived (15 minutes default).
