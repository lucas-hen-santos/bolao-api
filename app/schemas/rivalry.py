from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.schemas.user import UserResponse
from app.schemas.race import RaceResponse

class RivalryBase(BaseModel):
    opponent_id: int

class RivalryCreate(RivalryBase):
    pass

class RivalryResponse(BaseModel):
    id: int
    challenger_id: int
    opponent_id: int
    race_id: int
    status: str
    winner_id: Optional[int] = None
    margin: int
    created_at: datetime
    
    # Dados aninhados para facilitar o frontend
    challenger: Optional[UserResponse] = None
    opponent: Optional[UserResponse] = None
    race: Optional[RaceResponse] = None

    class Config:
        from_attributes = True