import os
from typing import Any, List, Optional
# Importamos UploadFile, File, Form para lidar com multipart/form-data
from fastapi import APIRouter, Body, Depends, HTTPException, status, Query, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func, desc

from app.api import deps
from app.core.security import get_password_hash
from app.models.achievement import UserAchievement
from app.models.season import Season
from app.models.team import Team
from app.models.user import User
from app.models.bet import Bet
from app.models.race import Race
from app.schemas.user import UserCreate, UserResponse

# Importação da Utils
from app.utils.image import process_and_validate_image
# Importação do Serviço de Email
from app.services.email import EmailService

router = APIRouter()

@router.get("/search", response_model=List[UserResponse])
def search_users(
    q: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Busca pública de pilotos para desafios (Apenas usuários ativos).
    """
    query = db.query(User).filter(User.is_active == True)
    
    if q:
        # Busca por nome (case insensitive)
        query = query.filter(User.full_name.ilike(f"%{q}%"))
        
    return query.order_by(User.full_name).offset(skip).limit(limit).all()

@router.get("/{user_id}/public")
def get_public_user_profile(user_id: int, db: Session = Depends(deps.get_db)):
    """
    Retorna o perfil público de um piloto com Stats Avançados e Medalhas.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Piloto não encontrado.")
    
    # 1. Dados Básicos e Equipe
    active_season = db.query(Season).filter(Season.is_active == True).first()
    team_data = None
    season_stats = {"rank": "N/A", "points": 0, "history": []}

    if active_season:
        # Busca Equipe
        team = db.query(Team).filter(
            Team.season_id == active_season.id,
            (Team.captain_id == user.id) | (Team.partner_id == user.id)
        ).first()
        
        if team:
            team_data = {
                "id": team.id,
                "name": team.name,
                "logo": team.logo_url,
                "colors": [team.primary_color, team.secondary_color]
            }

        # 2. Pontos na Temporada Atual (Soma das corridas terminadas desta season)
        points_query = db.query(func.sum(Bet.points)).join(Race).filter(
            Bet.user_id == user.id,
            Race.season_id == active_season.id,
            Race.status == 'FINISHED'
        )
        season_stats["points"] = points_query.scalar() or 0

        # 3. Posição no Ranking (Cálculo dinâmico)
        ranking_sub = db.query(
            Bet.user_id,
            func.sum(Bet.points).label("total")
        ).join(Race).filter(
            Race.season_id == active_season.id,
            Race.status == 'FINISHED'
        ).group_by(Bet.user_id).order_by(desc("total")).all()

        for idx, row in enumerate(ranking_sub):
            if row.user_id == user.id:
                season_stats["rank"] = f"#{idx + 1}"
                break
        
        # 4. Histórico para Gráfico (Últimas corridas)
        bets_history = db.query(Bet).join(Race).filter(
            Bet.user_id == user.id,
            Race.season_id == active_season.id,
            Race.status == 'FINISHED'
        ).order_by(Race.race_date).all()

        season_stats["history"] = [
            {"race": b.race.name, "points": b.points} for b in bets_history
        ]

    # 5. Buscar Medalhas (GARANTINDO QUE ESTÃO AQUI)
    badges = db.query(UserAchievement).options(
        joinedload(UserAchievement.achievement), 
        joinedload(UserAchievement.team)
    ).filter(UserAchievement.user_id == user.id).all()
    
    # 6. Pontos Totais da Carreira
    career_points = db.query(func.sum(Bet.points)).filter(Bet.user_id == user.id).scalar() or 0
    races_count = db.query(Bet).filter(Bet.user_id == user.id).count()

    return {
        "id": user.id,
        "name": user.full_name,
        "photo": user.profile_image_url,
        "joined_at": user.created_at,
        "team": team_data,
        "stats": {
            "career_points": career_points,
            "races": races_count,
            "season_points": season_stats["points"], # Novo
            "season_rank": season_stats["rank"],     # Novo
            "season_history": season_stats["history"] # Novo
        },
        "badges": badges 
    }
# --- ROTAS PÚBLICAS ---

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate, 
    background_tasks: BackgroundTasks, # <--- Injetado para envio assíncrono
    db: Session = Depends(deps.get_db)
):
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(status_code=400, detail="Este email já está cadastrado no sistema.")
    
    user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=get_password_hash(user_in.password),
        is_active=True,
        is_admin=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # --- ENVIO DE EMAIL (BACKGROUND) ---
    email_service = EmailService()
    background_tasks.add_task(email_service.send_welcome_email, user)
    # -----------------------------------

    return user

@router.get("/me", response_model=UserResponse)
def read_user_me(current_user: User = Depends(deps.get_current_user)):
    return current_user

# --- NOVO ENDPOINT DE ATUALIZAÇÃO DE PERFIL ---
@router.put("/me", response_model=UserResponse)
async def update_user_me(
    full_name: str = Form(...),
    photo: UploadFile = File(None),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Atualiza dados do perfil (Nome e Foto).
    """
    current_user.full_name = full_name
    
    if photo:
        # Remove foto antiga se existir e for local
        if current_user.profile_image_url and current_user.profile_image_url.startswith("/uploads/"):
            try:
                old_file = current_user.profile_image_url.lstrip("/")
                if os.path.exists(old_file):
                    os.remove(old_file)
            except Exception:
                pass
        
        # Processa e valida a nova foto na pasta 'users'
        url = await process_and_validate_image(photo, "users")
        current_user.profile_image_url = url

    db.commit()
    db.refresh(current_user)
    return current_user

@router.get("/me/history")
def get_my_bet_history(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    bets = db.query(Bet).join(Race).filter(
        Bet.user_id == current_user.id,
        Race.status == 'FINISHED'
    ).order_by(Race.race_date.desc()).all()
    
    history = []
    for bet in bets:
        race = bet.race
        result = race.result
        bet_data = {c.name: getattr(bet, c.name) for c in bet.__table__.columns}
        result_data = None
        if result:
            result_data = {c.name: getattr(result, c.name) for c in result.__table__.columns}

        history.append({
            "race_name": race.name,
            "race_date": race.race_date,
            "points": bet.points,
            "my_bet": bet_data,
            "official_result": result_data
        })
    return history

# --- ROTAS ADMINISTRATIVAS ---

@router.get("/", response_model=List[UserResponse])
def read_all_users(
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_admin),
):
    query = db.query(User)
    if search:
        query = query.filter(
            or_(User.full_name.ilike(f"%{search}%"), User.email.ilike(f"%{search}%"))
        )
    users = query.offset(skip).limit(limit).all()
    return users

@router.put("/{user_id}/status", response_model=UserResponse)
def toggle_user_status(
    user_id: int,
    is_active: bool = Body(..., embed=True),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user: raise HTTPException(404, "Usuário não encontrado")
    if user.id == current_user.id: raise HTTPException(400, "Você não pode banir a si mesmo.")
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    return user

@router.put("/{user_id}/role", response_model=UserResponse)
def toggle_user_role(
    user_id: int,
    is_admin: bool = Body(..., embed=True),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user: raise HTTPException(404, "Usuário não encontrado")
    if user.id == current_user.id: raise HTTPException(400, "Você não pode alterar seu próprio cargo.")
    user.is_admin = is_admin
    db.commit()
    db.refresh(user)
    return user