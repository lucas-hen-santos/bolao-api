from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import datetime

class BetBase(BaseModel):
    race_id: int
    
    # Extras
    pole_driver_id: int
    dotd_driver_id: int
    winning_team_id: int

    # Top 10
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

    @field_validator('p10_driver_id') # Validação acionada no último campo
    def check_duplicates_in_top10(cls, v, values):
        """
        Verifica se o usuário não repetiu pilotos no Top 10.
        """
        # Pega os dados já validados dos outros campos
        data = values.data
        drivers = [
            data.get('p1_driver_id'), data.get('p2_driver_id'), data.get('p3_driver_id'),
            data.get('p4_driver_id'), data.get('p5_driver_id'), data.get('p6_driver_id'),
            data.get('p7_driver_id'), data.get('p8_driver_id'), data.get('p9_driver_id'),
            v # O valor atual (p10)
        ]
        
        # Filtra None caso algum campo anterior tenha falhado
        drivers = [d for d in drivers if d is not None]

        if len(drivers) != len(set(drivers)):
            raise ValueError('Não é permitido repetir pilotos no Top 10.')
        return v

class BetCreate(BetBase):
    pass

class BetResponse(BetBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True