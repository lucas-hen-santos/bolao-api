from pydantic import BaseModel

class SeasonBase(BaseModel):
    year: int

class SeasonCreate(SeasonBase):
    pass

class SeasonResponse(SeasonBase):
    id: int
    is_active: bool
    is_finished: bool

    class Config:
        from_attributes = True