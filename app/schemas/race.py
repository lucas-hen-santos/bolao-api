from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from enum import Enum

class RaceStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    FINISHED = "FINISHED"
    COMPLETED = "COMPLETED" # Adicionado para compatibilidade

class RaceBase(BaseModel):
    name: str
    country: str
    race_date: datetime
    bets_open_at: Optional[datetime] = None
    bets_close_at: datetime

class RaceCreate(RaceBase):
    pass

# ✅ ADICIONADO: Classe para atualização (campos opcionais)
class RaceUpdate(BaseModel):
    name: Optional[str] = None
    country: Optional[str] = None
    race_date: Optional[datetime] = None
    bets_open_at: Optional[datetime] = None
    bets_close_at: Optional[datetime] = None
    status: Optional[RaceStatus] = None

class RaceResponse(RaceBase):
    id: int
    season_id: int
    status: RaceStatus

    class Config:
        from_attributes = True