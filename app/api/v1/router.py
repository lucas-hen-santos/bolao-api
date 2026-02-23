from fastapi import APIRouter
from app.api.v1.endpoints import achievements, admin, bets, notifications, races, ranking, rivals, teams, users, auth # Importe o auth

api_router = APIRouter()

api_router.include_router(users.router, prefix="/users", tags=["users"])
# Adicione esta linha:
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(teams.router, prefix="/teams", tags=["teams"])
api_router.include_router(races.router, prefix="/races", tags=["races"])
api_router.include_router(bets.router, prefix="/bets", tags=["bets"])
api_router.include_router(ranking.router, prefix="/ranking", tags=["ranking"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(achievements.router, prefix="/achievements", tags=["achievements"])
api_router.include_router(rivals.router, prefix="/rivals", tags=["rivals"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])