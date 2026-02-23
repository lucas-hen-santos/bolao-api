from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks # <--- Importar BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.api import deps
from app.models.rivalry import Rivalry, RivalryStatus
from app.models.race import Race, RaceStatus
from app.models.user import User
from app.schemas.rivalry import RivalryCreate, RivalryResponse
from app.services.email import EmailService # <--- Importar EmailService

router = APIRouter()

@router.get("/user/{user_id}/history", response_model=List[RivalryResponse])
def get_user_rivalry_history(
    user_id: int,
    db: Session = Depends(deps.get_db)
):
    """
    Retorna o histórico de duelos FINALIZADOS de um piloto específico (Perfil Público).
    """
    rivalries = db.query(Rivalry).options(
        joinedload(Rivalry.challenger),
        joinedload(Rivalry.opponent),
        joinedload(Rivalry.race)
    ).filter(
        or_(Rivalry.challenger_id == user_id, Rivalry.opponent_id == user_id),
        Rivalry.status == RivalryStatus.FINISHED
    ).order_by(Rivalry.created_at.desc()).all()
    
    return rivalries

@router.post("/challenge", response_model=RivalryResponse)
def create_challenge(
    rivalry_in: RivalryCreate,
    background_tasks: BackgroundTasks, # <--- Injeção
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Cria um desafio contra outro usuário para a PRÓXIMA corrida aberta/agendada e envia email.
    """
    next_race = db.query(Race).filter(
        Race.status.in_([RaceStatus.OPEN, RaceStatus.SCHEDULED])
    ).order_by(Race.race_date).first()

    if not next_race:
        raise HTTPException(400, "Não há corridas disponíveis para desafiar.")

    if rivalry_in.opponent_id == current_user.id:
        raise HTTPException(400, "Você não pode desafiar a si mesmo.")

    existing = db.query(Rivalry).filter(
        Rivalry.race_id == next_race.id,
        or_(
            (Rivalry.challenger_id == current_user.id) & (Rivalry.opponent_id == rivalry_in.opponent_id),
            (Rivalry.challenger_id == rivalry_in.opponent_id) & (Rivalry.opponent_id == current_user.id)
        )
    ).first()

    if existing:
        raise HTTPException(400, "Já existe um desafio pendente ou ativo entre vocês para esta corrida.")

    # Cria o desafio
    rivalry = Rivalry(
        challenger_id=current_user.id,
        opponent_id=rivalry_in.opponent_id,
        race_id=next_race.id,
        status=RivalryStatus.PENDING
    )
    db.add(rivalry)
    db.commit()
    db.refresh(rivalry)

    # --- EMAIL NOTIFICATION (BACKGROUND) ---
    opponent = db.query(User).filter(User.id == rivalry_in.opponent_id).first()
    if opponent:
        email_service = EmailService()
        background_tasks.add_task(
            email_service.send_new_challenge_email,
            opponent.email,
            current_user.full_name,
            next_race.name
        )
    # ---------------------------------------

    return rivalry

@router.put("/{rivalry_id}/accept")
def accept_challenge(
    rivalry_id: int,
    background_tasks: BackgroundTasks, # <--- Injeção
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    rivalry = db.query(Rivalry).filter(Rivalry.id == rivalry_id).first()
    if not rivalry: raise HTTPException(404, "Desafio não encontrado.")
    
    if rivalry.opponent_id != current_user.id:
        raise HTTPException(403, "Este desafio não é para você.")
        
    if rivalry.status != RivalryStatus.PENDING:
        raise HTTPException(400, "Este desafio não está mais pendente.")

    rivalry.status = RivalryStatus.ACCEPTED
    db.commit()
    
    # --- EMAIL NOTIFICATION (BACKGROUND) ---
    # Notifica o desafiante (challenger) que o oponente (current_user) aceitou
    challenger = db.query(User).filter(User.id == rivalry.challenger_id).first()
    race = db.query(Race).filter(Race.id == rivalry.race_id).first() # Busca nome da corrida
    
    if challenger and race:
        email_service = EmailService()
        background_tasks.add_task(
            email_service.send_challenge_accepted_email,
            challenger.email,
            current_user.full_name, # Quem aceitou
            race.name
        )
    # ---------------------------------------

    return {"message": "Desafio aceito! Que vença o melhor."}

@router.put("/{rivalry_id}/decline")
def decline_challenge(
    rivalry_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    rivalry = db.query(Rivalry).filter(Rivalry.id == rivalry_id).first()
    if not rivalry: raise HTTPException(404, "Desafio não encontrado.")
    
    if rivalry.opponent_id != current_user.id:
        raise HTTPException(403, "Este desafio não é para você.")

    rivalry.status = RivalryStatus.DECLINED
    db.commit()
    return {"message": "Desafio recusado."}

@router.get("/my-rivals", response_model=List[RivalryResponse])
def get_my_rivals(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    rivalries = db.query(Rivalry).options(
        joinedload(Rivalry.challenger),
        joinedload(Rivalry.opponent),
        joinedload(Rivalry.race)
    ).filter(
        or_(Rivalry.challenger_id == current_user.id, Rivalry.opponent_id == current_user.id)
    ).order_by(Rivalry.created_at.desc()).all()
    
    return rivalries