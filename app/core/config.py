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
    # Note que removemos os valores padrão das senhas.
    # Agora o Pydantic vai ler do .env. Se não achar, vai dar erro ao iniciar (o que é bom/seguro).
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True

    # --- PUSH NOTIFICATIONS ---
    VAPID_PRIVATE_KEY: str
    VAPID_PUBLIC_KEY: str
    VAPID_CLAIMS_EMAIL: str

    class Config:
        env_file = ".env"
        # Case sensitive = True é opcional, mas ajuda a evitar erros de digitação
        case_sensitive = True 

settings = Settings()