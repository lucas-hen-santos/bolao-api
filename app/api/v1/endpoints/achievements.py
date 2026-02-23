from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session

from app.api import deps
from app.models.achievement import Achievement, UserAchievement, AchievementRuleType
from app.models.user import User
from app.schemas.achievement import AchievementCreate, AchievementResponse, UserAchievementResponse

router = APIRouter()

# ... (Endpoints de Admin Create/Delete mantidos iguais) ...
@router.post("/", response_model=AchievementResponse, status_code=status.HTTP_201_CREATED)
def create_achievement(achievement_in: AchievementCreate, db: Session = Depends(deps.get_db), current_user: User = Depends(deps.get_current_active_admin)):
    existing = db.query(Achievement).filter(Achievement.name == achievement_in.name).first()
    if existing: raise HTTPException(status_code=400, detail="Já existe uma conquista com este nome.")
    new_achievement = Achievement(
        name=achievement_in.name, description=achievement_in.description, icon=achievement_in.icon,
        color=achievement_in.color, rule_type=achievement_in.rule_type.value, threshold=achievement_in.threshold
    )
    db.add(new_achievement)
    db.commit()
    db.refresh(new_achievement)
    return new_achievement

@router.get("/all", response_model=List[AchievementResponse])
def list_all_achievements(db: Session = Depends(deps.get_db), current_user: User = Depends(deps.get_current_user)):
    return db.query(Achievement).all()

@router.delete("/{id}")
def delete_achievement(id: int, db: Session = Depends(deps.get_db), current_user: User = Depends(deps.get_current_active_admin)):
    ach = db.query(Achievement).filter(Achievement.id == id).first()
    if not ach: raise HTTPException(404, "Conquista não encontrada.")
    db.delete(ach)
    db.commit()
    return {"message": "Conquista removida."}

@router.get("/me", response_model=List[UserAchievementResponse])
def get_my_achievements(db: Session = Depends(deps.get_db), current_user: User = Depends(deps.get_current_user)):
    return db.query(UserAchievement).filter(UserAchievement.user_id == current_user.id).all()

# --- NOVOS ENDPOINTS DE NOTIFICAÇÃO ---

@router.get("/me/new", response_model=List[UserAchievementResponse])
def get_new_achievements(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Retorna apenas as conquistas que o usuário ainda não viu (popup).
    """
    return db.query(UserAchievement).filter(
        UserAchievement.user_id == current_user.id,
        UserAchievement.seen == False
    ).all()

@router.put("/me/mark-seen")
def mark_achievements_seen(
    ids: List[int] = Body(...),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Marca uma lista de IDs de conquistas como vistas.
    """
    db.query(UserAchievement).filter(
        UserAchievement.id.in_(ids),
        UserAchievement.user_id == current_user.id
    ).update({UserAchievement.seen: True}, synchronize_session=False)
    
    db.commit()
    return {"message": "Marked as seen"}