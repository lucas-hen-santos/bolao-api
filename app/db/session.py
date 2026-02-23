from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Cria o motor de conexão com o MySQL
engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True, # Verifica se a conexão está viva antes de usar
    echo=False # Mude para True se quiser ver os comandos SQL no terminal
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)