from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api import deps
from app.models.race import Race, RaceStatus
from app.models.season import Season, RealDriver, RealTeam
from app.schemas.race import RaceCreate, RaceUpdate, RaceResponse as RaceSchema, RaceStatus as RaceStatusEnum

router = APIRouter()

def strip_tz(dt):
    """Pega a data exata que veio do front-end e garante que não tem fuso, salvando o valor cru."""
    if not dt:
        return dt
    return dt.replace(tzinfo=None)

# --- 1. Endpoints Auxiliares ---

@router.get("/drivers-list", response_model=List[dict])
def get_all_drivers(db: Session = Depends(deps.get_db)):
    active_season = db.query(Season).filter(Season.is_active == True).first()
    if not active_season: return []
    drivers = db.query(RealDriver).filter(RealDriver.season_id == active_season.id).all()
    return [{"id": d.id, "name": d.name, "number": d.number, "team_id": d.real_team_id, "photo_url": d.photo_url} for d in drivers]

@router.get("/teams-list", response_model=List[dict])
def get_all_teams(db: Session = Depends(deps.get_db)):
    active_season = db.query(Season).filter(Season.is_active == True).first()
    if not active_season: return []
    teams = db.query(RealTeam).filter(RealTeam.season_id == active_season.id).all()
    return [{"id": t.id, "name": t.name, "logo_url": t.logo_url} for t in teams]

# --- 2. CRUD de Corridas ---

@router.post("/", response_model=RaceSchema, status_code=status.HTTP_201_CREATED)
def create_race(
    race_in: RaceCreate,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_active_admin)
):
    active_season = db.query(Season).filter(Season.is_active == True).first()
    if not active_season:
        raise HTTPException(status_code=400, detail="Nenhuma temporada ativa encontrada.")

    race = Race(
        name=race_in.name,
        country=race_in.country,
        race_date=strip_tz(race_in.race_date),
        bets_open_at=strip_tz(race_in.bets_open_at),
        bets_close_at=strip_tz(race_in.bets_close_at),
        season_id=active_season.id,
        status=RaceStatus.SCHEDULED
    )
    db.add(race)
    db.commit()
    db.refresh(race)
    return race

@router.put("/{race_id}", response_model=RaceSchema)
def update_race_details(
    race_id: int,
    race_in: RaceUpdate,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_active_admin)
):
    race = db.query(Race).filter(Race.id == race_id).first()
    if not race:
        raise HTTPException(status_code=404, detail="Corrida não encontrada")
    
    if race_in.race_date:
        race_in.race_date = strip_tz(race_in.race_date)
    if race_in.bets_open_at:
        race_in.bets_open_at = strip_tz(race_in.bets_open_at)
    if race_in.bets_close_at:
        race_in.bets_close_at = strip_tz(race_in.bets_close_at)
    
    update_data = race_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(race, field, value)
    
    db.commit()
    db.refresh(race)
    return race

@router.get("/", response_model=List[RaceSchema])
def list_races(
    season_id: Optional[int] = Query(None), 
    db: Session = Depends(deps.get_db), 
    current_user = Depends(deps.get_current_user)
):
    if season_id: 
        target_season_id = season_id
    else:
        active_season = db.query(Season).filter(Season.is_active == True).first()
        if not active_season: return []
        target_season_id = active_season.id
    return db.query(Race).filter(Race.season_id == target_season_id).order_by(Race.race_date).all()

@router.put("/{race_id}/status", response_model=RaceSchema)
def update_race_status(
    race_id: int, 
    new_status: RaceStatusEnum, 
    db: Session = Depends(deps.get_db), 
    current_user = Depends(deps.get_current_active_admin)
):
    race = db.query(Race).filter(Race.id == race_id).first()
    if not race: raise HTTPException(404, "Corrida não encontrada")
    race.status = new_status
    db.commit()
    db.refresh(race)
    return race

@router.delete("/{race_id}")
def delete_race(
    race_id: int, 
    db: Session = Depends(deps.get_db), 
    current_user = Depends(deps.get_current_active_admin)
):
    race = db.query(Race).filter(Race.id == race_id).first()
    if not race: raise HTTPException(404, "Corrida não encontrada")
    db.delete(race)
    db.commit()
    return {"message": "Corrida removida com sucesso"}

@router.get("/{race_id}/result")
def get_race_result_public(
    race_id: int, 
    db: Session = Depends(deps.get_db), 
    current_user = Depends(deps.get_current_user)
):
    race = db.query(Race).filter(Race.id == race_id).first()
    if not race: raise HTTPException(404, "Corrida não encontrada")
    if not race.result: return {"race": race, "result": None}
    return {"race": race, "result": race.result}

@router.get("/seasons-list", response_model=List[dict])
def get_public_seasons_list(db: Session = Depends(deps.get_db)):
    seasons = db.query(Season).order_by(Season.year.desc()).all()
    return [{"id": s.id, "year": s.year, "is_active": s.is_active} for s in seasons]

@router.get("/grid-info", response_model=List[dict])
def get_grid_info(
    season_id: Optional[int] = Query(None), 
    db: Session = Depends(deps.get_db)
):
    if season_id:
        season = db.query(Season).filter(Season.id == season_id).first()
    else:
        season = db.query(Season).filter(Season.is_active == True).first()
    
    if not season: return []

    teams = db.query(RealTeam).filter(RealTeam.season_id == season.id).all()
    drivers = db.query(RealDriver).filter(RealDriver.season_id == season.id).all()

    grid = []
    for t in teams:
        team_drivers = [d for d in drivers if d.real_team_id == t.id]
        grid.append({
            "id": t.id,
            "name": t.name,
            "logo_url": t.logo_url,
            "drivers": [{"id": d.id, "name": d.name, "number": d.number, "photo_url": d.photo_url} for d in team_drivers]
        })
    return grid