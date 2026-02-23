from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class Season(Base):
    __tablename__ = "seasons"

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, unique=True, nullable=False) # Ex: 2025
    is_active = Column(Boolean, default=False) # Só uma deve ser True
    is_finished = Column(Boolean, default=False)

    races = relationship("Race", back_populates="season", cascade="all, delete-orphan")

class RealTeam(Base):
    """Equipes Reais da F1 (Ex: Ferrari, McLaren)"""
    __tablename__ = "real_teams"

    id = Column(Integer, primary_key=True, index=True)
    season_id = Column(Integer, ForeignKey("seasons.id"))
    name = Column(String(100), nullable=False)
    logo_url = Column(String(255))

class RealDriver(Base):
    """Pilotos Reais da F1 (Ex: Hamilton, Verstappen)"""
    __tablename__ = "real_drivers"

    id = Column(Integer, primary_key=True, index=True)
    season_id = Column(Integer, ForeignKey("seasons.id"))
    real_team_id = Column(Integer, ForeignKey("real_teams.id")) # Equipe atual dele
    name = Column(String(100), nullable=False)
    number = Column(Integer) # Número do carro
    photo_url = Column(String(255))