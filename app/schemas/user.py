from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

# Base: campos comuns
class UserBase(BaseModel):
    email: EmailStr
    full_name: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime
    
    # NOVO CAMPO (Opcional, pois pode ser nulo)
    profile_image_url: Optional[str] = None

    class Config:
        from_attributes = True