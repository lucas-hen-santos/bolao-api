from typing import Any, List, Optional
from app.models.ranking_cache import RankingCache
from app.services.badge import BadgeService
from app.services.email import EmailService
from fastapi import APIRouter, Depends, HTTPException, status, Body, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from sqlalchemy import desc, func


from app.api import deps
from app.models.season import Season, RealTeam, RealDriver
from app.models.user import User
from app.models.race import Race, RaceResult
from app.models.team import Team
from app.models.bet import Bet # <--- Importante para contar apostas
from app.schemas.season import SeasonCreate, SeasonResponse
from app.schemas.race import RaceStatus
from app.services.push import PushService
from app.services.scoring import calculate_race_points, calculate_race_points_async_wrapper 

router = APIRouter()

# --- Schemas ---

class RealTeamBase(BaseModel):
    name: str
    logo_url: str

class RealDriverBase(BaseModel):
    real_team_id: int
    name: str
    number: int
    photo_url: str

class RaceResultCreate(BaseModel):
    pole_driver_id: int
    dotd_driver_id: int
    winning_team_id: int
    p1_driver_id: int
    p2_driver_id: int
    p3_driver_id: int
    p4_driver_id: int
    p5_driver_id: int
    p6_driver_id: int
    p7_driver_id: int
    p8_driver_id: int
    p9_driver_id: int
    p10_driver_id: int

class TeamModeration(BaseModel):
    name: Optional[str] = None
    remove_logo: bool = False

class AnnouncementCreate(BaseModel):
    subject: str
    message: str

# --- NOVO: DASHBOARD STATS ---
@router.get("/dashboard/stats")
def get_dashboard_stats(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_admin)
):
    """
    Retorna métricas consolidadas, gráfico de engajamento e top leaders.
    """
    # 1. Totais Gerais
    total_users = db.query(User).count()
    total_teams = db.query(Team).count()
    
    active_season = db.query(Season).filter(Season.is_active == True).first()
    
    next_race_stats = None
    engagement_history = []
    top_drivers = []
    top_teams = []

    if active_season:
        # 2. Próxima Corrida
        next_race = db.query(Race).filter(
            Race.season_id == active_season.id,
            Race.status.in_([RaceStatus.OPEN, RaceStatus.SCHEDULED])
        ).order_by(Race.race_date).first()
        
        if next_race:
            bet_count = db.query(Bet).filter(Bet.race_id == next_race.id).count()
            participation_pct = 0
            if total_users > 0:
                participation_pct = round((bet_count / total_users) * 100)
            
            next_race_stats = {
                "id": next_race.id,
                "name": next_race.name,
                "status": next_race.status,
                "date": next_race.race_date,
                "bets_placed": bet_count,
                "participation_pct": participation_pct
            }

        # 3. Histórico de Engajamento (Últimas 5 Corridas Finalizadas)
        last_races = db.query(Race).filter(
            Race.season_id == active_season.id,
            Race.status == RaceStatus.FINISHED
        ).order_by(Race.race_date.desc()).limit(5).all()
        
        for r in reversed(last_races): # Ordem cronológica para o gráfico
            b_count = db.query(Bet).filter(Bet.race_id == r.id).count()
            pct = round((b_count / total_users) * 100) if total_users > 0 else 0
            engagement_history.append({
                "race_name": r.name,
                "bets": b_count,
                "pct": pct
            })

        # 4. Top 5 Pilotos (Ranking Cache)
        cached_drivers = db.query(RankingCache).filter(
            RankingCache.season_id == active_season.id,
            RankingCache.category == 'DRIVER'
        ).order_by(RankingCache.position).limit(5).all()
        
        for cd in cached_drivers:
            u = db.query(User).filter(User.id == cd.entity_id).first()
            if u:
                top_drivers.append({
                    "name": u.full_name,
                    "points": cd.points,
                    "photo": u.profile_image_url
                })

        # 5. Top 5 Equipes
        top_teams_data = db.query(Team).filter(
            Team.season_id == active_season.id
        ).order_by(desc(Team.total_points)).limit(5).all()
        
        top_teams = [
            {"name": t.name, "points": t.total_points, "logo": t.logo_url} 
            for t in top_teams_data
        ]

    # 6. Saúde das Equipes
    teams_full = db.query(Team).filter(Team.partner_id != None).count()
    teams_incomplete = total_teams - teams_full

    return {
        "total_users": total_users,
        "total_teams": total_teams,
        "active_season": active_season.year if active_season else "N/A",
        "next_race": next_race_stats,
        "team_composition": {
            "full": teams_full,
            "incomplete": teams_incomplete
        },
        "engagement_history": engagement_history, # <--- NOVO
        "top_drivers": top_drivers, # <--- NOVO
        "top_teams": top_teams # <--- NOVO
    }

# --- 1. CRUD F1 (TEAMS/DRIVERS) ---

@router.post("/f1/teams/", status_code=status.HTTP_201_CREATED)
def create_real_team(team_in: RealTeamBase, db: Session = Depends(deps.get_db), current_user = Depends(deps.get_current_active_admin)):
    active_season = db.query(Season).filter(Season.is_active == True).first()
    if not active_season: raise HTTPException(status_code=400, detail="No active season.")
    new_team = RealTeam(**team_in.model_dump(), season_id=active_season.id)
    db.add(new_team)
    db.commit()
    db.refresh(new_team)
    return new_team

@router.get("/f1/teams/")
def list_real_teams(db: Session = Depends(deps.get_db), current_user = Depends(deps.get_current_active_admin)):
    active_season = db.query(Season).filter(Season.is_active == True).first()
    if not active_season: return []
    return db.query(RealTeam).filter(RealTeam.season_id == active_season.id).all()

@router.put("/f1/teams/{team_id}")
def update_real_team(team_id: int, team_in: RealTeamBase, db: Session = Depends(deps.get_db), current_user = Depends(deps.get_current_active_admin)):
    team = db.query(RealTeam).filter(RealTeam.id == team_id).first()
    if not team: raise HTTPException(404, "Team not found.")
    team.name = team_in.name
    team.logo_url = team_in.logo_url
    db.commit()
    db.refresh(team)
    return team

@router.delete("/f1/teams/{team_id}")
def delete_real_team(team_id: int, db: Session = Depends(deps.get_db), current_user = Depends(deps.get_current_active_admin)):
    team = db.query(RealTeam).filter(RealTeam.id == team_id).first()
    if not team: raise HTTPException(404, "Team not found.")
    db.delete(team)
    db.commit()
    return {"message": "Team deleted"}

@router.post("/f1/drivers/", status_code=status.HTTP_201_CREATED)
def create_real_driver(driver_in: RealDriverBase, db: Session = Depends(deps.get_db), current_user = Depends(deps.get_current_active_admin)):
    active_season = db.query(Season).filter(Season.is_active == True).first()
    if not active_season: raise HTTPException(400, "No active season.")
    team = db.query(RealTeam).filter(RealTeam.id == driver_in.real_team_id).first()
    if not team: raise HTTPException(404, "Team not found.")
    new_driver = RealDriver(**driver_in.model_dump(), season_id=active_season.id)
    db.add(new_driver)
    db.commit()
    db.refresh(new_driver)
    return new_driver

@router.get("/f1/drivers/")
def list_real_drivers(db: Session = Depends(deps.get_db), current_user = Depends(deps.get_current_active_admin)):
    active_season = db.query(Season).filter(Season.is_active == True).first()
    if not active_season: return []
    return db.query(RealDriver).filter(RealDriver.season_id == active_season.id).all()

@router.put("/f1/drivers/{driver_id}")
def update_real_driver(driver_id: int, driver_in: RealDriverBase, db: Session = Depends(deps.get_db), current_user = Depends(deps.get_current_active_admin)):
    driver = db.query(RealDriver).filter(RealDriver.id == driver_id).first()
    if not driver: raise HTTPException(404, "Driver not found.")
    driver.name = driver_in.name
    driver.number = driver_in.number
    driver.photo_url = driver_in.photo_url
    driver.real_team_id = driver_in.real_team_id
    db.commit()
    db.refresh(driver)
    return driver

@router.delete("/f1/drivers/{driver_id}")
def delete_real_driver(driver_id: int, db: Session = Depends(deps.get_db), current_user = Depends(deps.get_current_active_admin)):
    driver = db.query(RealDriver).filter(RealDriver.id == driver_id).first()
    if not driver: raise HTTPException(404, "Driver not found.")
    db.delete(driver)
    db.commit()
    return {"message": "Driver deleted"}


# --- 3. TEMPORADAS E RESULTADOS ---

@router.get("/seasons/", response_model=List[SeasonResponse])
def list_seasons(db: Session = Depends(deps.get_db), current_user: User = Depends(deps.get_current_active_admin)):
    return db.query(Season).order_by(Season.year.desc()).all()

@router.post("/seasons/", response_model=SeasonResponse)
def create_new_season(season_in: SeasonCreate, db: Session = Depends(deps.get_db), current_user: User = Depends(deps.get_current_active_admin)):
    existing = db.query(Season).filter(Season.year == season_in.year).first()
    if existing: raise HTTPException(status_code=400, detail="Temporada já existe")
    
    db.query(Season).update({Season.is_active: False})
    
    new_season = Season(year=season_in.year, is_active=True, is_finished=False)
    db.add(new_season)
    db.commit()
    db.refresh(new_season)
    return new_season

@router.put("/seasons/{season_id}/close", response_model=SeasonResponse)
def close_season(
    season_id: int, 
    db: Session = Depends(deps.get_db), 
    current_user: User = Depends(deps.get_current_active_admin)
):
    season = db.query(Season).filter(Season.id == season_id).first()
    if not season:
        raise HTTPException(status_code=404, detail="Temporada não encontrada")
    
    # 1. Processar Premiação
    badge_service = BadgeService()
    badge_service.process_season_end_awards(db, season_id)
    
    # 2. Fechar temporada
    season.is_active = False
    season.is_finished = True
    
    db.commit()
    db.refresh(season)
    return season

@router.post("/races/{race_id}/result")
def set_race_result(
    race_id: int, 
    result_in: RaceResultCreate, 
    background_tasks: BackgroundTasks, # <--- Injeção
    db: Session = Depends(deps.get_db), 
    current_user: User = Depends(deps.get_current_active_admin)
):
    """
    Define o resultado e agenda o processamento de pontos em background.
    """
    race = db.query(Race).filter(Race.id == race_id).first()
    if not race: raise HTTPException(status_code=404, detail="Corrida não encontrada")
    
    # Se já existir resultado, removemos o objeto RaceResult antigo
    existing_result = db.query(RaceResult).filter(RaceResult.race_id == race_id).first()
    if existing_result: 
        db.delete(existing_result)
        db.commit()
    
    # Cria novo gabarito
    result = RaceResult(race_id=race_id, **result_in.model_dump())
    db.add(result)
    db.commit()
    
    # --- AGENDAMENTO ASSÍNCRONO ---
    # O servidor responde imediatamente, e o cálculo roda "por fora"
    background_tasks.add_task(calculate_race_points_async_wrapper, race_id)
    
    return {"msg": "Resultado salvo! O processamento dos pontos iniciou em segundo plano."}

# --- 4. MODERAÇÃO DE EQUIPES (COMUNIDADE) ---

@router.get("/teams/", response_model=List[dict])
def list_user_teams(
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_admin)
):
    query = db.query(Team)
    if search: query = query.filter(Team.name.ilike(f"%{search}%"))
    teams = query.order_by(Team.id.desc()).offset(skip).limit(limit).all()
    return [{"id": t.id, "name": t.name, "logo_url": t.logo_url, "primary_color": t.primary_color, "secondary_color": t.secondary_color, "captain_name": t.captain.full_name if t.captain else "Unknown", "partner_name": t.partner.full_name if t.partner else "Vaga", "total_points": t.total_points} for t in teams]

@router.put("/teams/{team_id}/moderate")
def moderate_team(
    team_id: int,
    mod_in: TeamModeration,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_admin)
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team: raise HTTPException(404, "Equipe não encontrada")
    if mod_in.name: team.name = mod_in.name
    if mod_in.remove_logo: team.logo_url = None
    db.commit()
    db.refresh(team)
    return {"message": "Equipe moderada com sucesso", "team_name": team.name}

@router.delete("/teams/{team_id}")
def delete_user_team(
    team_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_admin)
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team: raise HTTPException(404, "Equipe não encontrada")
    db.delete(team)
    db.commit()
    return {"message": "Equipe excluída com sucesso"}

# --- ANNOUNCEMENTS (COM PUSH) ---
@router.post("/announce")
def send_announcement(
    announce_in: dict, # {subject: str, message: str}
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_admin) # <--- Corrigido
):
    """Envia comunicado por Email e Push"""
    users = db.query(User).filter(User.is_active == True).all()
    emails = [u.email for u in users if u.email]
    
    subject = announce_in.get("subject")
    message = announce_in.get("message")

    # 1. Enviar Email (Background)
    email_service = EmailService()
    background_tasks.add_task(
        email_service.send_announcement,
        emails,
        subject,
        message
    )

    # 2. Enviar Push Notification (Broadcast)
    try:
        push_service = PushService()
        # Push é rápido, pode ser síncrono ou task, aqui faremos síncrono para garantir log imediato
        push_service.broadcast_notification(
            db,
            title=f"📢 {subject}",
            body=message[:100] + "..." if len(message) > 100 else message, # Corta texto longo
            url="/dashboard"
        )
    except Exception as e:
        print(f"❌ Erro ao enviar push de anúncio: {e}")

    return {"message": f"Comunicado disparado para {len(users)} usuários via Email e Push."}