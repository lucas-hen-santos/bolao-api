from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from enum import Enum
from app.schemas.team import TeamResponse # <--- Importar Schema de Time

class RuleTypeEnum(str, Enum):
    TOTAL_POINTS = "TOTAL_POINTS"
    RACE_POINTS = "RACE_POINTS"
    POLE_HITS = "POLE_HITS"
    WINNER_HITS = "WINNER_HITS"
    DOTD_HITS = "DOTD_HITS"
    RACES_PARTICIPATED = "RACES_PARTICIPATED"
    PILOT_RANKING = "PILOT_RANKING"
    TEAM_RANKING = "TEAM_RANKING"

class AchievementBase(BaseModel):
    name: str
    description: str
    icon: str
    color: str
    rule_type: RuleTypeEnum
    threshold: int

class AchievementCreate(AchievementBase):
    pass

class AchievementResponse(AchievementBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class UserAchievementResponse(BaseModel):
    id: int
    user_id: int
    achievement_id: int
    achievement: AchievementResponse
    earned_at: datetime
    
    race_id: Optional[int] = None
    team_id: Optional[int] = None
    team: Optional[TeamResponse] = None
    season_id: Optional[int] = None # <--- NOVO

    class Config:
        from_attributes = True