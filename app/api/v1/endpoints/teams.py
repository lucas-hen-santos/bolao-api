import os
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc

from app.api import deps
from app.models.team import Team
from app.models.season import Season
from app.models.user import User
from app.models.bet import Bet
from app.models.race import Race

from app.utils.image import process_and_validate_image

router = APIRouter()

@router.get("/{team_id}/public")
def get_public_team_profile(team_id: int, db: Session = Depends(deps.get_db)):
    """
    Retorna o perfil público de uma equipe com Ranking e Gráfico.
    """
    team = db.query(Team).options(
        joinedload(Team.captain), 
        joinedload(Team.partner)
    ).filter(Team.id == team_id).first()
    
    if not team:
        raise HTTPException(status_code=404, detail="Equipe não encontrada.")
    
    # 1. Posição no Ranking de Construtores
    rank = "N/A"
    active_season = db.query(Season).filter(Season.id == team.season_id).first()
    
    if active_season:
        team_ranking = db.query(Team).filter(
            Team.season_id == active_season.id
        ).order_by(desc(Team.total_points)).all()

        for idx, t in enumerate(team_ranking):
            if t.id == team.id:
                rank = f"#{idx + 1}"
                break
    
    # 2. Histórico de Pontos por Corrida (Para Gráfico)
    # Soma os pontos de todas as apostas vinculadas a este time (via snapshot team_id)
    history_data = db.query(
        Race.name,
        func.sum(Bet.points).label("points")
    ).join(Bet).filter(
        Bet.team_id == team.id,
        Race.status == 'FINISHED'
    ).group_by(Race.id).order_by(Race.race_date).all()

    history = [{"race": row.name, "points": row.points} for row in history_data]

    response = {
        "id": team.id,
        "name": team.name,
        "logo_url": team.logo_url,
        "primary_color": team.primary_color,
        "secondary_color": team.secondary_color,
        "total_points": team.total_points,
        "rank": rank, # <--- NOVO
        "history": history, # <--- NOVO
        "captain": {
            "id": team.captain.id,
            "name": team.captain.full_name,
            "photo": team.captain.profile_image_url
        } if team.captain else None,
        "partner": {
            "id": team.partner.id,
            "name": team.partner.full_name,
            "photo": team.partner.profile_image_url
        } if team.partner else None
    }
    return response

# --- CRUD BÁSICO (CREATE, UPDATE, READ) ---

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_team(name: str = Form(...), primary_color: str = Form(...), secondary_color: str = Form(...), logo: UploadFile = File(None), db: Session = Depends(deps.get_db), current_user: User = Depends(deps.get_current_user)):
    active_season = db.query(Season).filter(Season.is_active == True).first()
    if not active_season: raise HTTPException(400, "Não há temporada ativa.")
    existing_team = db.query(Team).filter(Team.season_id == active_season.id, (Team.captain_id == current_user.id) | (Team.partner_id == current_user.id)).first()
    if existing_team: raise HTTPException(400, "Você já está em uma equipe.")
    logo_url = None
    if logo: logo_url = await process_and_validate_image(logo, "teams")
    new_team = Team(name=name, primary_color=primary_color, secondary_color=secondary_color, logo_url=logo_url, season_id=active_season.id, captain_id=current_user.id, total_points=0)
    db.add(new_team)
    db.commit()
    db.refresh(new_team)
    return new_team

@router.put("/{team_id}")
async def update_team(team_id: int, name: str = Form(...), primary_color: str = Form(...), secondary_color: str = Form(...), logo: UploadFile = File(None), db: Session = Depends(deps.get_db), current_user: User = Depends(deps.get_current_user)):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team: raise HTTPException(404, "Equipe não encontrada.")
    if team.captain_id != current_user.id: raise HTTPException(403, "Apenas o capitão pode editar.")
    if logo:
        if team.logo_url and team.logo_url.startswith("/uploads/"):
            try:
                old_file = team.logo_url.lstrip("/") 
                if os.path.exists(old_file): os.remove(old_file)
            except Exception: pass 
        team.logo_url = await process_and_validate_image(logo, "teams")
    team.name = name
    team.primary_color = primary_color
    team.secondary_color = secondary_color
    db.commit()
    db.refresh(team)
    return team

@router.get("/my-team")
def get_my_team(db: Session = Depends(deps.get_db), current_user: User = Depends(deps.get_current_user)):
    active_season = db.query(Season).filter(Season.is_active == True).first()
    if not active_season: return None
    team = db.query(Team).options(joinedload(Team.captain), joinedload(Team.partner)).filter(Team.season_id == active_season.id, (Team.captain_id == current_user.id) | (Team.partner_id == current_user.id)).first()
    if not team: return None
    captain_points = db.query(func.sum(Bet.points)).join(Race).filter(Bet.user_id == team.captain_id, Race.season_id == active_season.id, Race.status == 'FINISHED').scalar() or 0
    partner_points = 0
    if team.partner_id:
        partner_points = db.query(func.sum(Bet.points)).join(Race).filter(Bet.user_id == team.partner_id, Race.season_id == active_season.id, Race.status == 'FINISHED').scalar() or 0
    recent_races = db.query(Race).filter(Race.season_id == active_season.id, Race.status == 'FINISHED').order_by(Race.race_date.desc()).limit(5).all()
    recent_performance = []
    for race in reversed(recent_races):
        race_points = 0
        bets = db.query(Bet).filter(Bet.race_id == race.id, Bet.user_id.in_([team.captain_id, team.partner_id] if team.partner_id else [team.captain_id])).all()
        for b in bets: race_points += b.points
        recent_performance.append({"race_name": race.name, "points": race_points})
    return {"team": team, "stats": {"captain_points": captain_points, "partner_points": partner_points, "recent_performance": recent_performance}}

@router.get("/{team_id}/preview")
def preview_team(team_id: int, db: Session = Depends(deps.get_db), current_user: User = Depends(deps.get_current_user)):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team: raise HTTPException(404, "Equipe não encontrada")
    return {"id": team.id, "name": team.name, "logo_url": team.logo_url, "captain_name": team.captain.full_name if team.captain else "Desconhecido", "members_count": 2 if team.partner_id else 1}

@router.post("/{team_id}/join")
def join_team(team_id: int, db: Session = Depends(deps.get_db), current_user: User = Depends(deps.get_current_user)):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team: raise HTTPException(404, "Equipe não encontrada")
    if team.partner_id: raise HTTPException(400, "Equipe cheia")
    if team.captain_id == current_user.id: raise HTTPException(400, "Você é o capitão")
    active_season = db.query(Season).filter(Season.is_active == True).first()
    existing = db.query(Team).filter(Team.season_id == active_season.id, (Team.captain_id == current_user.id) | (Team.partner_id == current_user.id)).first()
    if existing: raise HTTPException(400, "Você já tem equipe")
    team.partner_id = current_user.id
    db.commit()
    return {"message": f"Bem-vindo à {team.name}!"}

# --- FUNÇÃO AUXILIAR PARA DÉBITO DE PONTOS ---
def debit_points_from_team(db: Session, team: Team, user_id: int):
    """
    Calcula e subtrai os pontos que o usuário gerou para esta equipe.
    Apenas as apostas feitas ENQUANTO ele estava nesta equipe (team_id gravado) contam.
    """
    points_contributed = db.query(func.sum(Bet.points)).filter(
        Bet.user_id == user_id,
        Bet.team_id == team.id
    ).scalar() or 0
    
    if points_contributed > 0:
        team.total_points = max(0, team.total_points - points_contributed)
        return points_contributed
    return 0

# --- ENDPOINTS COM LÓGICA DE DÉBITO ---

@router.post("/leave")
def leave_team(db: Session = Depends(deps.get_db), current_user: User = Depends(deps.get_current_user)):
    active_season = db.query(Season).filter(Season.is_active == True).first()
    if not active_season: raise HTTPException(400, "Sem temporada ativa")

    team = db.query(Team).filter(Team.season_id == active_season.id, Team.partner_id == current_user.id).first()

    if not team:
        captain_check = db.query(Team).filter(Team.season_id == active_season.id, Team.captain_id == current_user.id).first()
        if captain_check: raise HTTPException(400, "Capitão não pode abandonar o barco! Você deve excluir a equipe.")
        raise HTTPException(404, "Você não está em nenhuma equipe como parceiro.")

    # 1. Debita pontos antes de sair
    points_removed = debit_points_from_team(db, team, current_user.id)
    
    # 2. Remove da equipe
    team.partner_id = None
    db.commit()
    
    return {"message": f"Você saiu da equipe. {points_removed} pontos foram debitados."}

@router.post("/{team_id}/kick")
def kick_partner(team_id: int, db: Session = Depends(deps.get_db), current_user: User = Depends(deps.get_current_user)):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team: raise HTTPException(404, "Equipe não encontrada")
    if team.captain_id != current_user.id: raise HTTPException(403, "Apenas o capitão pode remover membros.")
    if not team.partner_id: raise HTTPException(400, "Não há parceiro para remover.")

    partner_id = team.partner_id

    # 1. Debita pontos antes de remover
    points_removed = debit_points_from_team(db, team, partner_id)

    # 2. Remove da equipe
    team.partner_id = None
    db.commit()
    
    return {"message": f"Parceiro removido. {points_removed} pontos foram debitados da equipe."}