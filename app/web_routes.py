"""
Web UI Routes - HTML pages and OAuth flow for browser-based login.

These routes are for the web interface. If you only need API access,
you can disable these routes by not including this router in main.py.
"""

import secrets
from typing import Dict, Any

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.exceptions import HTTPException

from .auth import require_manager, require_ceo
from .config import settings
from .routes import exchange_code_for_tokens, extract_user_info

router = APIRouter()


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
