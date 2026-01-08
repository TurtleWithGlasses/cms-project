"""
API Versioning Module

This module provides centralized API version management for all routes.
"""

from fastapi import APIRouter

# API Version prefix
API_V1_PREFIX = "/api/v1"


def create_api_router(
    *,
    prefix: str = "",
    tags: list[str] | None = None,
    version: str = "v1",
    include_in_schema: bool = True,
) -> APIRouter:
    """
    Create a versioned API router.

    Args:
        prefix: Additional prefix after version (e.g., "/users")
        tags: OpenAPI tags for documentation
        version: API version (default: "v1")
        include_in_schema: Whether to include in OpenAPI schema

    Returns:
        APIRouter with proper version prefix

    Example:
        >>> router = create_api_router(prefix="/users", tags=["Users"])
        >>> # This creates a router with path /api/v1/users
    """
    version_prefix = f"/api/{version}"
    full_prefix = f"{version_prefix}{prefix}" if prefix else version_prefix

    return APIRouter(
        prefix=full_prefix,
        tags=tags,  # type: ignore[arg-type]
        include_in_schema=include_in_schema,
    )


# Pre-configured router for v1 API
api_v1_router = APIRouter(prefix=API_V1_PREFIX)
