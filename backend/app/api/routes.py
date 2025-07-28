"""
Main API Router
Aggregates all endpoint routers
"""

from fastapi import APIRouter

from app.api.endpoints import chat, discounts, health, supervision, admin, shows, users, auth

# Main API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(
    chat.router, 
    prefix="/chat", 
    tags=["chat"]
)

api_router.include_router(
    discounts.router, 
    prefix="/discounts", 
    tags=["discounts"]
)

api_router.include_router(
    health.router, 
    prefix="/health", 
    tags=["health"]
)

api_router.include_router(
    supervision.router, 
    prefix="/supervision", 
    tags=["supervision"]
)

api_router.include_router(
    admin.router, 
    prefix="/admin", 
    tags=["admin"]
)

api_router.include_router(
    shows.router, 
    prefix="/shows", 
    tags=["shows"]
)

api_router.include_router(
    users.router, 
    prefix="/users", 
    tags=["users"]
)

api_router.include_router(
    auth.router, 
    prefix="/auth", 
    tags=["authentication"]
) 