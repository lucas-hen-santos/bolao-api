from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # --- GERAIS ---
    API_V1_STR: str
    PROJECT_NAME: str
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # --- BANCO DE DADOS ---
    SQLALCHEMY_DATABASE_URI: str

    # --- URLs ---
    FRONTEND_URL: str
    BACKEND_URL: str

    # --- CONFIGURAÇÕES DE EMAIL ---
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    
    # CONFIGURAÇÕES FIXAS (Para evitar erros de conversão do Render)
    MAIL_PORT: int = 465
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_STARTTLS: bool = False
    MAIL_SSL_TLS: bool = True
    
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True

    # --- PUSH NOTIFICATIONS ---
    VAPID_PRIVATE_KEY: str
    VAPID_PUBLIC_KEY: str
    VAPID_CLAIMS_EMAIL: str

    class Config:
        env_file = ".env"
        case_sensitive = True 

settings = Settings()