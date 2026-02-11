import json
import base64
import secrets
from typing import Dict, Any

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.exceptions import HTTPException
import httpx

from .auth import require_manager, require_ceo, require_role, require_auth_bearer
from .config import settings
from .keycloak_admin import get_groups_with_members
from .response_wrapper import wrap_response

router = APIRouter()


# Helper Functions
def decode_jwt_payload(token: str) -> Dict[str, Any]:
    """
    Decode JWT payload without verification (for extracting user info).
    
    Args:
        token: JWT access token
        
    Returns:
        Decoded payload as dictionary
    """
    parts = token.split('.')
    if len(parts) != 3:
        raise ValueError("Invalid JWT token format")
    
    # Decode payload (add padding if needed)
    payload = parts[1]
    padding = 4 - len(payload) % 4
    if padding != 4:
        payload += '=' * padding
    
    decoded_bytes = base64.urlsafe_b64decode(payload)
    return json.loads(decoded_bytes)


async def exchange_code_for_tokens(code: str, redirect_uri: str) -> Dict[str, Any]:
    """
    Exchange authorization code for access tokens.
    
    Args:
        code: Authorization code from Keycloak
        redirect_uri: Callback URI
        
    Returns:
        Token response from Keycloak
        
    Raises:
        HTTPException: If token exchange fails
    """
    token_url = f"{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/token"
    
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            token_url,
            data={
                'grant_type': 'authorization_code',
                'client_id': settings.KEYCLOAK_CLIENT_ID,
                'client_secret': settings.KEYCLOAK_CLIENT_SECRET,
                'code': code,
                'redirect_uri': redirect_uri,
            }
        )
    
    if response.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail=f"Token exchange failed: {response.text}"
        )
    
    return response.json()


def extract_user_info(token_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract user information from token response.
    
    Args:
        token_data: Token response from Keycloak
        
    Returns:
        User information dictionary
    """
    access_token = token_data.get('access_token')
    if not access_token:
        return {}
    
    decoded = decode_jwt_payload(access_token)
    
    return {
        'sub': decoded.get('sub'),
        'email': decoded.get('email'),
        'preferred_username': decoded.get('preferred_username'),
        'name': decoded.get('name'),
        'roles': decoded.get('realm_access', {}).get('roles', []),
        'groups': decoded.get('groups', []),
        'access_token': access_token,
        'refresh_token': token_data.get('refresh_token'),
        'token_type': token_data.get('token_type', 'Bearer'),
        'expires_in': token_data.get('expires_in'),
    }


# Routes
@router.get("/", response_class=HTMLResponse)
async def homepage(request: Request) -> HTMLResponse:
    """Homepage with login link or user dashboard."""
    user = request.session.get("user")

    if not user:
        return HTMLResponse('<a href="/login">Login with Keycloak</a>')

    roles = user.get("roles", [])
    name = user.get("preferred_username") or user.get("email") or "User"

    menu_items = []
    if "manager" in roles:
        menu_items.append('<li><a href="/manager">Manager Dashboard</a></li>')
    if "ceo" in roles:
        menu_items.append('<li><a href="/ceo">CEO Dashboard</a></li>')
    
    menu_items.append('<li><a href="/logout">Logout</a></li>')

    return HTMLResponse(f"""
        <h1>Welcome, {name}</h1>
        <p>Roles: {roles}</p>
        <ul>{''.join(menu_items)}</ul>
    """)



@router.get("/login")
async def login(request: Request) -> RedirectResponse:
    """Redirect to Keycloak login page."""
    redirect_uri = str(request.url_for('auth_callback'))
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
async def auth_callback(request: Request) -> RedirectResponse:
    """Handle OAuth callback from Keycloak."""
    try:
        # Verify state (CSRF protection)
        state = request.query_params.get('state')
        session_state = request.session.get('oauth_state')
        
        if not state or state != session_state:
            raise HTTPException(
                status_code=400,
                detail="Invalid state parameter (CSRF protection)"
            )
        
        request.session.pop('oauth_state', None)
        
        # Get authorization code
        code = request.query_params.get('code')
        if not code:
            raise HTTPException(
                status_code=400,
                detail="No authorization code received"
            )
        
        # Exchange code for tokens
        redirect_uri = str(request.url_for('auth_callback'))
        token_data = await exchange_code_for_tokens(code, redirect_uri)
        
        # Extract and store user info
        userinfo = extract_user_info(token_data)
        request.session['user'] = userinfo
        
        return RedirectResponse(url='/', status_code=302)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Authentication failed: {str(e)}"
        )


@router.get("/logout")
async def logout(request: Request) -> RedirectResponse:
    """Logout user and redirect to Keycloak logout."""
    request.session.pop('user', None)
    
    logout_url = (
        f"{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}"
        f"/protocol/openid-connect/logout"
        f"?post_logout_redirect_uri={request.url_for('homepage')}"
        f"&client_id={settings.KEYCLOAK_CLIENT_ID}"
    )
    
    return RedirectResponse(url=logout_url, status_code=302)


@router.get("/manager")
async def manager_dashboard(user: Dict[str, Any] = Depends(require_manager)) -> HTMLResponse:
    """Manager dashboard (requires 'manager' role)."""
    return HTMLResponse("<h1>Manager Dashboard</h1><p>Welcome, Manager!</p>")


@router.get("/ceo")
async def ceo_dashboard(user: Dict[str, Any] = Depends(require_ceo)) -> Dict[str, Any]:
    """
    CEO Dashboard - Display teams and employees from Keycloak groups.
    Requires 'ceo' role.
    """
    try:
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
async def api_data(user: Dict[str, Any] = Depends(require_role("manager"))) -> Dict[str, Any]:
    """Example protected API endpoint (requires 'manager' role)."""
    return {
        "data": "sensitive-data",
        "user": user.get("preferred_username")
    }



@router.get("/me")
async def get_current_user(user: Dict[str, Any] = Depends(require_auth_bearer)) -> Dict[str, Any]:
    """
    Get current authenticated user's details.
    Works with both session cookies and bearer tokens.
    """
    user_data = {
        "sub": user.get("sub"),
        "email": user.get("email"),
        "preferred_username": user.get("preferred_username"),
        "name": user.get("name"),
        "roles": user.get("roles", []),
        "groups": user.get("groups", []),
    }
    
    return wrap_response(
        user_data,
        message="User information retrieved successfully",
        ttl=settings.USER_INFO_CACHE_TTL
    )


@router.post("/refresh")
async def refresh_token(request: Request) -> Dict[str, Any]:
    """
    Refresh an expired access token using a refresh token.
    Client secret is kept secure on backend.
    """
    try:
        body = await request.json()
        refresh_token_value = body.get("refresh_token")
        
        if not refresh_token_value:
            raise HTTPException(
                status_code=400,
                detail="refresh_token required in request body"
            )
        
        token_url = f"{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/token"
        
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                token_url,
                data={
                    "grant_type": "refresh_token",
                    "client_id": settings.KEYCLOAK_CLIENT_ID,
                    "client_secret": settings.KEYCLOAK_CLIENT_SECRET,
                    "refresh_token": refresh_token_value,
                },
            )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=401,
                detail="Token refresh failed: invalid or expired refresh_token"
            )
        
        return response.json()
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Token refresh error: {str(e)}"
        )


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint for monitoring."""
    return {"status": "ok"}


@router.get("/cache/info")
async def cache_info(user: Dict[str, Any] = Depends(require_role("admin"))) -> Dict[str, Any]:
    """
    Get cache statistics (requires 'admin' role).
    Returns cache configuration and current state.
    """
    from .jwt_utils import get_cache_info as get_jwt_cache_info
    from .keycloak_admin import get_cache_info as get_admin_cache_info
    
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
    
    return wrap_response(
        cache_data,
        message="Cache information retrieved successfully",
        ttl=60
    )


@router.post("/cache/clear")
async def clear_caches(user: Dict[str, Any] = Depends(require_role("admin"))) -> Dict[str, Any]:
    """
    Clear all caches (requires 'admin' role).
    Useful for testing or after Keycloak configuration changes.
    """
    from .jwt_utils import clear_jwks_cache
    from .keycloak_admin import clear_admin_token_cache
    
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
    
    return wrap_response(
        result,
        message="Caches cleared successfully"
    )