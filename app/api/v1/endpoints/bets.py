from typing import List, Any
from datetime import datetime
import pytz

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.models.bet import Bet
from app.models.race import Race, RaceStatus
from app.models.user import User
from app.models.team import Team # <--- Importar Team
from app.schemas.bet import BetCreate, BetResponse

router = APIRouter()

@router.post("/", response_model=BetResponse)
def create_or_update_bet(
    bet_in: BetCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Recebe o palpite do usuário e GRAVA A EQUIPE ATUAL (Snapshot).
    """
    
    # 1. Buscar a corrida
    race = db.query(Race).filter(Race.id == bet_in.race_id).first()
    if not race:
        raise HTTPException(status_code=404, detail="Corrida não encontrada")

    # 2. Validação de Status
    if race.status == RaceStatus.FINISHED:
        raise HTTPException(
            status_code=400, 
            detail="Esta corrida já foi finalizada. Não é possível apostar."
        )

    # 3. Validação de Horário (Brasília)
    tz_brasilia = pytz.timezone('America/Sao_Paulo')
    agora = datetime.now(tz_brasilia)
    
    fechamento = race.bets_close_at
    if fechamento.tzinfo is None:
        fechamento = tz_brasilia.localize(fechamento)
    else:
        fechamento = fechamento.astimezone(tz_brasilia)

    if agora > fechamento:
        raise HTTPException(
            status_code=400, 
            detail=f"As apostas encerraram em {fechamento.strftime('%d/%m/%Y às %H:%M')}."
        )

    # --- NOVO: IDENTIFICAR EQUIPE (SNAPSHOT) ---
    # Busca a equipe do usuário na temporada desta corrida
    user_team = db.query(Team).filter(
        Team.season_id == race.season_id,
        (Team.captain_id == current_user.id) | (Team.partner_id == current_user.id)
    ).first()
    
    team_id_snapshot = user_team.id if user_team else None
    # -------------------------------------------

    # 4. Upsert
    existing_bet = db.query(Bet).filter(
        Bet.user_id == current_user.id,
        Bet.race_id == bet_in.race_id
    ).first()

    if existing_bet:
        # ATUALIZAÇÃO
        existing_bet.pole_driver_id = bet_in.pole_driver_id
        existing_bet.dotd_driver_id = bet_in.dotd_driver_id
        existing_bet.winning_team_id = bet_in.winning_team_id
        
        existing_bet.p1_driver_id = bet_in.p1_driver_id
        existing_bet.p2_driver_id = bet_in.p2_driver_id
        existing_bet.p3_driver_id = bet_in.p3_driver_id
        existing_bet.p4_driver_id = bet_in.p4_driver_id
        existing_bet.p5_driver_id = bet_in.p5_driver_id
        existing_bet.p6_driver_id = bet_in.p6_driver_id
        existing_bet.p7_driver_id = bet_in.p7_driver_id
        existing_bet.p8_driver_id = bet_in.p8_driver_id
        existing_bet.p9_driver_id = bet_in.p9_driver_id
        existing_bet.p10_driver_id = bet_in.p10_driver_id
        
        # Atualiza a equipe caso ele tenha trocado de time desde a última vez que salvou este palpite
        existing_bet.team_id = team_id_snapshot 
        
        db.commit()
        db.refresh(existing_bet)
        return existing_bet
        
    else:
        # CRIAÇÃO
        new_bet = Bet(
            user_id=current_user.id,
            team_id=team_id_snapshot, # Salva o ID da equipe
            **bet_in.model_dump()
        )
        db.add(new_bet)
        db.commit()
        db.refresh(new_bet)
        return new_bet

@router.get("/my-bets", response_model=List[BetResponse])
def read_my_bets(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    bets = db.query(Bet).filter(Bet.user_id == current_user.id).all()
    return bets