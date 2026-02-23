from datetime import timedelta
from typing import Any
# Adicione Form nas importações
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Body, BackgroundTasks, Form 
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from pydantic import BaseModel, EmailStr

from app.db.session import SessionLocal
from app.core import security
from app.core.config import settings
from app.models.user import User
from app.services.email import EmailService

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ... (Schemas ForgotPassword e ResetPassword mantidos iguais) ...
class ForgotPassword(BaseModel):
    email: EmailStr

class ResetPassword(BaseModel):
    token: str
    new_password: str

@router.post("/login")
def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    remember_me: bool = Form(False), # <--- NOVO PARÂMETRO
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Email ou senha incorretos")
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Usuário inativo")

    # Access Token: Sempre curto (30 min)
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=user.id, expires_delta=access_token_expires
    )
    
    # Refresh Token: Longo (7 dias)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = security.create_refresh_token(
        subject=user.id, expires_delta=refresh_token_expires
    )

    # Cookie de Acesso (Sempre expira rápido)
    response.set_cookie(
        key="access_token", 
        value=f"Bearer {access_token}", 
        httponly=True, 
        max_age=1800,
        expires=1800,
        samesite="lax",
        secure=False 
    )
    
    # LÓGICA DO "MANTER CONECTADO"
    if remember_me:
        # Persistente: Dura 7 dias
        max_age_refresh = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        response.set_cookie(
            key="refresh_token", 
            value=refresh_token, 
            httponly=True, 
            max_age=max_age_refresh, # Define validade
            samesite="lax",
            secure=False
        )
    else:
        # Sessão: Morre ao fechar o navegador (max_age=None)
        response.set_cookie(
            key="refresh_token", 
            value=refresh_token, 
            httponly=True, 
            max_age=None, # <--- ISSO TORNA O COOKIE DE SESSÃO
            expires=None, # <--- GARANTE COMPATIBILIDADE
            samesite="lax",
            secure=False
        )

    return {"msg": "Login realizado com sucesso", "user_id": user.id}

# ... (Restante do arquivo mantido igual: refresh, logout, forgot-password...) ...
@router.post("/refresh")
def refresh_token(request: Request, response: Response, db: Session = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token não encontrado")

    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[security.ALGORITHM])
        token_type = payload.get("type")
        if token_type != "refresh":
            raise HTTPException(status_code=401, detail="Token inválido")
        
        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="Usuário não encontrado")
            
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = security.create_access_token(
        subject=user.id, expires_delta=access_token_expires
    )

    response.set_cookie(
        key="access_token", 
        value=f"Bearer {new_access_token}", 
        httponly=True, 
        max_age=1800,
        samesite="lax",
        secure=False
    )

    return {"msg": "Token atualizado"}

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"msg": "Logout realizado"}

@router.post("/forgot-password")
def forgot_password(
    data: ForgotPassword,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email não encontrado no sistema.")
    expires = timedelta(minutes=30)
    reset_token = security.create_access_token(subject=user.id, expires_delta=expires)
    email_service = EmailService()
    background_tasks.add_task(email_service.send_reset_password_email, user, reset_token)
    return {"message": "Email de recuperação enviado."}

@router.post("/reset-password")
def reset_password(
    data: ResetPassword,
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(data.token, settings.SECRET_KEY, algorithms=[security.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=400, detail="Token inválido.")
    except JWTError:
        raise HTTPException(status_code=400, detail="O link expirou ou é inválido. Solicite novamente.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    user.hashed_password = security.get_password_hash(data.new_password)
    db.commit()
    return {"message": "Senha alterada com sucesso! Faça login."}