"""
Keycloak Admin API client for fetching full group hierarchy with members.

This module mirrors Keycloak's group structure EXACTLY:
- Groups
- Sub-groups
- Direct members only (no fake inheritance)
"""

import logging
from typing import Dict, List, Any

import httpx
from cachetools import TTLCache

from .config import settings

logger = logging.getLogger("keycloak_admin")

# Cache admin token for 5 minutes
_token_cache = TTLCache(maxsize=1, ttl=300)


# -------------------------------------------------------------------
# AUTH
# -------------------------------------------------------------------

async def get_admin_token() -> str:
    if "admin_token" in _token_cache:
        return _token_cache["admin_token"]

    if not settings.KEYCLOAK_ADMIN_CLIENT_ID or not settings.KEYCLOAK_ADMIN_CLIENT_SECRET:
        raise ValueError(
            "KEYCLOAK_ADMIN_CLIENT_ID / KEYCLOAK_ADMIN_CLIENT_SECRET not set"
        )

    token_url = (
        f"{settings.KEYCLOAK_SERVER_URL}"
        f"/realms/{settings.KEYCLOAK_REALM}"
        f"/protocol/openid-connect/token"
    )

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": settings.KEYCLOAK_ADMIN_CLIENT_ID,
                "client_secret": settings.KEYCLOAK_ADMIN_CLIENT_SECRET,
            },
        )

        response.raise_for_status()
        data = response.json()

        access_token = data.get("access_token")
        if not access_token:
            raise ValueError("No access_token received from Keycloak")

        _token_cache["admin_token"] = access_token
        return access_token


# -------------------------------------------------------------------
# RAW KEYCLOAK CALLS
# -------------------------------------------------------------------

async def get_groups() -> List[Dict[str, Any]]:
    """
    Fetch TOP-LEVEL groups only (Keycloak behavior).
    """
    token = await get_admin_token()

    url = f"{settings.KEYCLOAK_SERVER_URL}/admin/realms/{settings.KEYCLOAK_REALM}/groups"
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()


async def get_group_members(group_id: str) -> List[Dict[str, Any]]:
    """
    Fetch DIRECT members of a group.
    Does NOT include subgroup users.
    """
    token = await get_admin_token()

    url = (
        f"{settings.KEYCLOAK_SERVER_URL}"
        f"/admin/realms/{settings.KEYCLOAK_REALM}"
        f"/groups/{group_id}/members"
    )
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()


async def get_subgroups(group_id: str) -> List[Dict[str, Any]]:
    """
    Fetch sub-groups of a group.
    """
    token = await get_admin_token()

    url = (
        f"{settings.KEYCLOAK_SERVER_URL}"
        f"/admin/realms/{settings.KEYCLOAK_REALM}"
        f"/groups/{group_id}"
    )
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json().get("subGroups", [])


# -------------------------------------------------------------------
# HIERARCHY BUILDER (CORE LOGIC)
# -------------------------------------------------------------------

async def build_group_tree(group: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively build group hierarchy EXACTLY like Keycloak UI.
    """

    group_id = group["id"]

    # Direct members only (truth)
    members = await get_group_members(group_id)

    # Child groups
    subgroups = await get_subgroups(group_id)

    children = []
    for sg in subgroups:
        children.append(await build_group_tree(sg))

    return {
        "id": group_id,
        "name": group["name"],
        "path": group.get("path", ""),
        "members": members,
        "subGroups": children,
    }


# -------------------------------------------------------------------
# PUBLIC API
# -------------------------------------------------------------------

async def get_group_hierarchy() -> List[Dict[str, Any]]:
    """
    Entry point.
    Returns full Keycloak org structure with members.
    """

    top_groups = await get_groups()
    hierarchy = []

    for group in top_groups:
        hierarchy.append(await build_group_tree(group))

    return hierarchy


async def get_groups_with_members() -> List[Dict[str, Any]]:
    """
    Backwards-compatible wrapper used by existing routes.

    Returns a flat list of TOP-LEVEL groups where each group contains:
      - id, name, path
      - members: list of direct members
      - subGroupCount: number of immediate subgroups

    This mirrors the previous `get_groups_with_members` shape used by routes.
    """
    top_groups = await get_groups()
    result: List[Dict[str, Any]] = []

    async def build_full_group(g: Dict[str, Any]) -> Dict[str, Any]:
        group_id = g["id"]
        try:
            members = await get_group_members(group_id)
        except Exception:
            members = []

        # Recursively fetch subgroups
        subgroups = await get_subgroups(group_id)
        children = [await build_full_group(sg) for sg in subgroups]

        return {
            "id": g.get("id"),
            "name": g.get("name"),
            "path": g.get("path", ""),
            "subGroupCount": len(children),
            "members": members,
            "subGroups": children,
        }

    for g in top_groups:
        result.append(await build_full_group(g))

    return result
