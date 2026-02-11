import json
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.exceptions import HTTPException
import httpx
from .auth import oauth, require_manager, require_ceo, require_role, require_auth_bearer
from .config import settings
from .keycloak_admin import get_groups_with_members

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    user = request.session.get("user")

    if not user:
        return '<a href="/login">Login with Keycloak</a>'

    roles = user.get("roles", [])
    name = user.get("preferred_username") or user.get("email") or "User"

    menu = ""

    if "manager" in roles:
        menu += '<li><a href="/manager">Manager Dashboard</a></li>'

    if "ceo" in roles:
        menu += '<li><a href="/ceo">CEO Dashboard</a></li>'

    return f"""
    <h1>Welcome, {name}</h1>
    <p>Roles: {roles}</p>
    <ul>
        {menu}
        <li><a href="/logout">Logout</a></li>
    </ul>
    """


@router.get("/login")
async def login(request: Request):
    # Build Keycloak authorization URL manually for reliable redirect
    redirect_uri = str(request.url_for('auth_callback'))
    
    # Generate state parameter for CSRF protection
    import secrets
    state = secrets.token_urlsafe(32)
    request.session['oauth_state'] = state
    
    auth_url = (
        f"{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}"
        f"/protocol/openid-connect/auth"
        f"?client_id={settings.KEYCLOAK_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope=openid%20email%20profile"
        f"&state={state}"
    )
    
    return RedirectResponse(url=auth_url, status_code=302)

@router.get("/callback", name="auth_callback")
async def auth_callback(request: Request):
    try:
        # Verify state parameter (CSRF protection)
        state = request.query_params.get('state')
        session_state = request.session.get('oauth_state')
        
        if not state or state != session_state:
            return HTMLResponse("Auth failed: Invalid state parameter (CSRF protection)", status_code=400)
        
        # Clear the state from session
        request.session.pop('oauth_state', None)
        
        # Get authorization code
        code = request.query_params.get('code')
        if not code:
            return HTMLResponse("Auth failed: No authorization code received", status_code=400)
        
        # Exchange code for tokens
        token_url = f"{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/token"
        redirect_uri = str(request.url_for('auth_callback'))
        
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                token_url,
                data={
                    'grant_type': 'authorization_code',
                    'client_id': settings.KEYCLOAK_CLIENT_ID,
                    'client_secret': settings.KEYCLOAK_CLIENT_SECRET,
                    'code': code,
                    'redirect_uri': redirect_uri,
                }
            )
        
        if token_response.status_code != 200:
            return HTMLResponse(f"Auth failed: Token exchange failed - {token_response.text}", status_code=400)
        
        token_data = token_response.json()
        access_token = token_data.get('access_token')
        
        # Decode access token to get user info and roles
        import base64
        userinfo = {}
        
        if access_token:
            # Split JWT token (header.payload.signature)
            parts = access_token.split('.')
            if len(parts) == 3:
                # Decode payload (add padding if needed)
                payload = parts[1]
                padding = 4 - len(payload) % 4
                if padding != 4:
                    payload += '=' * padding
                
                # Decode base64
                decoded_bytes = base64.urlsafe_b64decode(payload)
                decoded = json.loads(decoded_bytes)
                
                # Extract user information
                userinfo['sub'] = decoded.get('sub')
                userinfo['email'] = decoded.get('email')
                userinfo['preferred_username'] = decoded.get('preferred_username')
                userinfo['name'] = decoded.get('name')
                
                # Extract roles from realm_access
                realm_roles = decoded.get('realm_access', {}).get('roles', [])
                userinfo['roles'] = realm_roles
                
                # Extract groups if present
                groups = decoded.get('groups', [])
                userinfo['groups'] = groups
                
                # Store token information
                userinfo['access_token'] = access_token
                userinfo['refresh_token'] = token_data.get('refresh_token')
                userinfo['token_type'] = token_data.get('token_type', 'Bearer')
                userinfo['expires_in'] = token_data.get('expires_in')
        
        request.session['user'] = userinfo
        return RedirectResponse(url='/')
    except Exception as e:
        return HTMLResponse(f"Auth failed: {e}", status_code=400)

@router.get("/logout")
async def logout(request: Request):
    request.session.pop('user', None)
    
    # Redirect to Keycloak's logout endpoint
    logout_url = f"{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/logout"
    redirect_param = str(request.url_for('homepage'))
    
    return RedirectResponse(f"{logout_url}?post_logout_redirect_uri={redirect_param}&client_id={settings.KEYCLOAK_CLIENT_ID}")

@router.get("/manager")
async def manager_dashboard(user: dict = Depends(require_manager)):
    return HTMLResponse("<h1>Manager Dashboard</h1><p>Welcome, Admin!</p>")

@router.get("/ceo")
async def ceo_dashboard(user: dict = Depends(require_ceo)):
    """
    CEO Dashboard - Display teams and employees from Keycloak groups.
    
    Returns:
        - ceo_info: Current CEO's information
        - teams: List of teams with their members
    """
    try:
        # Fetch all groups with their members
        teams = await get_groups_with_members()
        
        return {
            "ceo": {
                "username": user.get('preferred_username') or user.get('email'),
                "email": user.get('email'),
                "name": user.get('name'),
            },
            "teams": teams,
            "totalTeams": len(teams),
            "totalEmployees": sum(len(team.get("members", [])) for team in teams),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch teams data: {str(e)}"
        )


@router.get("/api/data")
async def api_data(user: dict = Depends(require_role("manager"))):
    """Example API endpoint protected by bearer token or session requiring 'manager' role."""
    return {"data": "sensitive-data", "user": user.get("preferred_username")}


@router.get("/me")
async def get_current_user(user: dict = Depends(require_auth_bearer)):
    """
    Get current authenticated user's details with access token information.
    
    This endpoint is called by the frontend to display user info in the app shell.
    It works with both session cookies (browser login) and bearer tokens (API calls).
    
    Returns:
    - sub: Unique user ID from Keycloak
    - email: User's email address
    - preferred_username: Username/login name
    - name: Full name (if available)
    - roles: List of realm roles assigned to user
    - groups: List of groups user belongs to
    - token_info: Access token information (if available)
    - metadata.ttl: Cache TTL information (5 minutes)
    
    Example response:
    {
        "success": true,
        "message": "User information retrieved successfully",
        "data": {
            "sub": "user-uuid-123",
            "email": "john@example.com",
            "preferred_username": "john.smith",
            "name": "John Smith",
            "roles": ["manager", "user"],
            "groups": ["sales-team"],
            "token_info": {
                "token_type": "Bearer",
                "expires_in": 900,
                "access_token": "eyJhbGciOiJSUzI1NiIsInR5cC...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cC..."
            }
        },
        "metadata": {
            "timestamp": "2024-02-10T10:30:00Z",
            "version": "1.0",
            "ttl": {
                "value": 300,
                "unit": "seconds",
                "expires_at": "2024-02-10T10:35:00Z",
                "human_readable": "5 minutes"
            }
        }
    }
    """
    from .response_wrapper import wrap_response
    
    user_data = {
        "sub": user.get("sub"),
        "email": user.get("email"),
        "preferred_username": user.get("preferred_username"),
        "name": user.get("name"),
        "roles": user.get("roles", []),
        "groups": user.get("groups", []),
    }
    
    # Add token information if available
    if user.get("access_token"):
        user_data["token_info"] = {
            "token_type": user.get("token_type", "Bearer"),
            "expires_in": user.get("expires_in"),
            "access_token": user.get("access_token"),
            "refresh_token": user.get("refresh_token"),
        }
    
    # Return with TTL (user info cached for 5 minutes)
    return wrap_response(
        user_data,
        message="User information retrieved successfully",
        ttl=settings.USER_INFO_CACHE_TTL
    )


@router.get("/token")
async def get_token_info(user: dict = Depends(require_auth_bearer)):
    """
    Get access token information for the current user.
    
    This endpoint returns the access token and refresh token that can be used
    for API calls. Useful for:
    - Frontend applications that need to make API calls
    - Mobile apps that need to store tokens
    - Debugging authentication issues
    
    Returns:
    - access_token: JWT access token
    - refresh_token: Refresh token for getting new access tokens
    - token_type: Always "Bearer"
    - expires_in: Token lifetime in seconds
    - user: Basic user information
    
    Example response:
    {
        "success": true,
        "message": "Token information retrieved successfully",
        "data": {
            "access_token": "eyJhbGciOiJSUzI1NiIsInR5cC...",
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cC...",
            "token_type": "Bearer",
            "expires_in": 900,
            "user": {
                "sub": "user-uuid",
                "preferred_username": "john.smith",
                "email": "john@example.com"
            }
        },
        "metadata": {
            "timestamp": "2024-02-10T10:30:00Z",
            "version": "1.0"
        }
    }
    
    Security Note:
    - Store tokens securely (httpOnly cookies or secure storage)
    - Never expose tokens in URLs or logs
    - Use HTTPS in production
    """
    from .response_wrapper import wrap_response
    
    token_data = {
        "access_token": user.get("access_token"),
        "refresh_token": user.get("refresh_token"),
        "token_type": user.get("token_type", "Bearer"),
        "expires_in": user.get("expires_in"),
        "user": {
            "sub": user.get("sub"),
            "preferred_username": user.get("preferred_username"),
            "email": user.get("email"),
            "roles": user.get("roles", [])
        }
    }
    
    # No TTL for token endpoint (tokens have their own expiration)
    return wrap_response(
        token_data,
        message="Token information retrieved successfully"
    )


@router.post("/refresh")
async def refresh_token(request: Request):
    """
    Securely refresh an expired access token using a refresh token.
    
    This endpoint is called by the frontend when the access token expires (401).
    The frontend sends the refresh_token (obtained during login), and this endpoint
    exchanges it for a new access_token.
    
    SECURITY: The client_secret is kept on the backend (never exposed to frontend).
    This is more secure than frontend calling Keycloak directly.
    
    Request body:
    {
        "refresh_token": "long-lived-token-from-login"
    }
    
    Returns:
    {
        "access_token": "new-short-lived-token",
        "refresh_token": "new-or-same-refresh-token",
        "expires_in": 900,  # 15 minutes in seconds
        "token_type": "Bearer"
    }
    
    Usage (Frontend):
    1. Store refresh_token securely after login
    2. When access_token expires (401 response), call this endpoint
    3. Use returned access_token for subsequent API calls
    """
    try:
        # Parse request body
        body = await request.json()
        refresh_token_value = body.get("refresh_token")
        
        if not refresh_token_value:
            raise HTTPException(
                status_code=400,
                detail="refresh_token required in request body"
            )
        
        # Call Keycloak token endpoint to exchange refresh token for new access token
        token_url = f"{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/token"
        
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                token_url,
                data={
                    "grant_type": "refresh_token",
                    "client_id": settings.KEYCLOAK_CLIENT_ID,
                    "client_secret": settings.KEYCLOAK_CLIENT_SECRET,  # Secure: backend only!
                    "refresh_token": refresh_token_value,
                },
            )
        
        # Handle Keycloak errors (invalid refresh token, expired, etc.)
        if response.status_code != 200:
            raise HTTPException(
                status_code=401,
                detail="Token refresh failed: invalid or expired refresh_token"
            )
        
        # Return new tokens to frontend
        return response.json()
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Token refresh error: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """
    Health check endpoint for Docker/Kubernetes readiness probes.
    
    Returns:
        Simple status object indicating service is running
    """
    return {"status": "ok"}


@router.get("/cache/info")
async def cache_info(user: dict = Depends(require_role("admin"))):
    """
    Get cache statistics for monitoring and debugging.
    
    Requires 'admin' role.
    
    Returns:
        Cache configuration and current state for all caches with TTL information:
        - JWKS cache (JWT validation)
        - Admin token cache (Keycloak Admin API)
    """
    from .jwt_utils import get_cache_info as get_jwt_cache_info
    from .keycloak_admin import get_cache_info as get_admin_cache_info
    from .response_wrapper import wrap_response
    
    cache_data = {
        "jwt_cache": get_jwt_cache_info(),
        "admin_cache": get_admin_cache_info(),
        "cache_ttl_config": {
            "jwks_ttl": settings.JWKS_CACHE_TTL,
            "jwks_ttl_human": f"{settings.JWKS_CACHE_TTL // 60} minutes",
            "admin_token_ttl": settings.ADMIN_TOKEN_CACHE_TTL,
            "admin_token_ttl_human": f"{settings.ADMIN_TOKEN_CACHE_TTL // 60} minutes",
            "user_info_ttl": settings.USER_INFO_CACHE_TTL,
            "user_info_ttl_human": f"{settings.USER_INFO_CACHE_TTL // 60} minutes",
            "group_ttl": settings.GROUP_CACHE_TTL,
            "group_ttl_human": f"{settings.GROUP_CACHE_TTL // 60} minutes",
        }
    }
    
    # Return with TTL metadata (cache info itself has TTL of 60 seconds)
    return wrap_response(
        cache_data,
        message="Cache information retrieved successfully",
        ttl=60
    )


@router.post("/cache/clear")
async def clear_caches(user: dict = Depends(require_role("admin"))):
    """
    Clear all caches (JWKS, admin token).
    
    Requires 'admin' role.
    
    Useful for:
    - Testing
    - Forcing fresh data fetch
    - After Keycloak configuration changes
    
    Returns:
        Confirmation message with TTL information
    """
    from .jwt_utils import clear_jwks_cache
    from .keycloak_admin import clear_admin_token_cache
    from .response_wrapper import wrap_response
    
    clear_jwks_cache()
    clear_admin_token_cache()
    
    result = {
        "message": "All caches cleared successfully",
        "cleared": ["jwks_cache", "admin_token_cache"],
        "cache_ttl": {
            "jwks": f"{settings.JWKS_CACHE_TTL}s ({settings.JWKS_CACHE_TTL // 60}min)",
            "admin_token": f"{settings.ADMIN_TOKEN_CACHE_TTL}s ({settings.ADMIN_TOKEN_CACHE_TTL // 60}min)"
        }
    }
    
    # Return with no TTL (immediate action)
    return wrap_response(
        result,
        message="Caches cleared successfully"
    )