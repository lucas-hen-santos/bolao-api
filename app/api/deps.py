from typing import Generator, Optional
from fastapi import Depends, HTTPException, status, Request
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.core.config import settings
from app.core import security
from app.models.user import User

def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """
    Lê o cookie 'access_token', decodifica e busca o usuário.
    """
    token_str = request.cookies.get("access_token")
    
    if not token_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado (Cookie ausente)",
        )

    # O token vem como "Bearer eyJhbGci..."
    try:
        scheme, token = token_str.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Formato de token inválido")
            
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[security.ALGORITHM])
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token inválido (sem ID)")
            
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Token expirado ou inválido")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
    return user

def get_current_active_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Verifica se o usuário é ADMIN.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403, detail="O usuário não tem privilégios de administrador"
        )
    return current_user