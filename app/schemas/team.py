from pydantic import BaseModel
from typing import Optional

class TeamBase(BaseModel):
    name: str
    primary_color: str
    secondary_color: str

# Para criar, não enviamos logo aqui (vai ser via Form Data por causa do arquivo)
class TeamCreate(TeamBase):
    pass

class TeamResponse(TeamBase):
    id: int
    logo_url: Optional[str] = None
    captain_id: int
    partner_id: Optional[int] = None
    season_id: int
    invite_link: Optional[str] = None # Vamos gerar isso dinamicamente

    class Config:
        from_attributes = True