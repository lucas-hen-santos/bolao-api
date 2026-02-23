from typing import List, Any, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from app.api import deps
from app.models.team import Team
from app.models.season import Season
from app.models.user import User
from app.models.ranking_cache import RankingCache # <--- NOVO

router = APIRouter()

@router.get("/teams")
def get_teams_ranking(
    season_id: Optional[int] = Query(None),
    db: Session = Depends(deps.get_db)
):
    """Ranking de Construtores (Via Cache)"""
    
    if season_id:
        target_season_id = season_id
    else:
        active = db.query(Season).filter(Season.is_active == True).first()
        if not active: return []
        target_season_id = active.id

    # Busca do Cache
    cached_data = db.query(RankingCache).filter(
        RankingCache.season_id == target_season_id,
        RankingCache.category == 'TEAM'
    ).order_by(RankingCache.position).all()
    
    # Se não tiver cache (ex: temporada nova sem corridas), retorna vazio ou busca direto
    if not cached_data:
        return []

    ranking = []
    for row in cached_data:
        # Busca dados detalhados da equipe
        team = db.query(Team).options(
            joinedload(Team.captain), joinedload(Team.partner)
        ).filter(Team.id == row.entity_id).first()
        
        if team:
            captain_data = {
                "id": team.captain.id,
                "name": team.captain.full_name,
                "photo": team.captain.profile_image_url
            } if team.captain else None

            partner_data = {
                "id": team.partner.id,
                "name": team.partner.full_name,
                "photo": team.partner.profile_image_url
            } if team.partner else None

            ranking.append({
                "id": team.id,
                "name": team.name,
                "logo_url": team.logo_url,
                "primary_color": team.primary_color,
                "secondary_color": team.secondary_color,
                "points": row.points, # Usa pontos do cache
                "captain": captain_data,
                "partner": partner_data
            })
    return ranking

@router.get("/drivers")
def get_drivers_ranking(
    season_id: Optional[int] = Query(None),
    db: Session = Depends(deps.get_db)
):
    """Ranking de Pilotos (Via Cache)"""
    
    if season_id:
        target_season_id = season_id
    else:
        active = db.query(Season).filter(Season.is_active == True).first()
        if not active: return []
        target_season_id = active.id

    # Busca do Cache
    cached_data = db.query(RankingCache).filter(
        RankingCache.season_id == target_season_id,
        RankingCache.category == 'DRIVER'
    ).order_by(RankingCache.position).all()

    if not cached_data:
        return []

    ranking = []
    for row in cached_data:
        user = db.query(User).filter(User.id == row.entity_id).first()
        
        if user:
            # Busca equipe para exibir no card
            team = db.query(Team).filter(
                Team.season_id == target_season_id,
                (Team.captain_id == user.id) | (Team.partner_id == user.id)
            ).first()

            ranking.append({
                "id": user.id,
                "name": user.full_name,
                "profile_image_url": user.profile_image_url,
                "team_id": team.id if team else None,
                "team_name": team.name if team else "Sem Equipe",
                "team_color": team.primary_color if team else "#666",
                "team_logo": team.logo_url if team else None,
                "points": row.points # Pontos do cache
            })
        
    return ranking