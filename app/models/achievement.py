from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base
import enum

class AchievementRuleType(str, enum.Enum):
    # Regras de Corrida / Acumuladas
    TOTAL_POINTS = "TOTAL_POINTS"
    RACE_POINTS = "RACE_POINTS"
    POLE_HITS = "POLE_HITS"
    WINNER_HITS = "WINNER_HITS"
    DOTD_HITS = "DOTD_HITS"
    RACES_PARTICIPATED = "RACES_PARTICIPATED"
    
    # Regras de Fim de Temporada
    PILOT_RANKING = "PILOT_RANKING"
    TEAM_RANKING = "TEAM_RANKING"

class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=False)
    icon = Column(String(50), default="🏆")
    color = Column(String(20), default="gold")
    
    rule_type = Column(String(50), nullable=False)
    threshold = Column(Integer, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    achievement_id = Column(Integer, ForeignKey("achievements.id"), nullable=False)
    
    earned_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Contexto
    race_id = Column(Integer, ForeignKey("races.id"), nullable=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    season_id = Column(Integer, ForeignKey("seasons.id"), nullable=True) # <--- NOVO
    
    seen = Column(Boolean, default=False) 

    user = relationship("User")
    achievement = relationship("Achievement")
    race = relationship("Race")
    team = relationship("Team")