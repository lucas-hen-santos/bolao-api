# app/db/base.py
from sqlalchemy.orm import declarative_base

# Cria a classe base para os modelos herdarem
Base = declarative_base()