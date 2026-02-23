from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.db.base import Base
import enum

class RaceStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    FINISHED = "FINISHED"

class Race(Base):
    __tablename__ = "races"

    id = Column(Integer, primary_key=True, index=True)
    season_id = Column(Integer, ForeignKey("seasons.id"), nullable=False)
    name = Column(String(100), nullable=False)
    country = Column(String(100), nullable=False)
    race_date = Column(DateTime, nullable=False)
    
    # Prazos de Aposta
    bets_open_at = Column(DateTime, nullable=True)
    bets_close_at = Column(DateTime, nullable=True)
    
    # Status: SCHEDULED, OPEN, CLOSED, FINISHED
    status = Column(String(20), default="SCHEDULED") 
    
    # Controle de Notificações (NOVO)
    alert_1h_sent = Column(Boolean, default=False)
    alert_5m_sent = Column(Boolean, default=False)

    # Relacionamentos
    season = relationship("Season", back_populates="races")
    result = relationship("RaceResult", back_populates="race", uselist=False)

class RaceResult(Base):
    """O Gabarito Oficial da Corrida"""
    __tablename__ = "race_results"

    id = Column(Integer, primary_key=True, index=True)
    race_id = Column(Integer, ForeignKey("races.id"), unique=True, nullable=False)

    pole_driver_id = Column(Integer, ForeignKey("real_drivers.id"))
    dotd_driver_id = Column(Integer, ForeignKey("real_drivers.id"))
    winning_team_id = Column(Integer, ForeignKey("real_teams.id"))

    p1_driver_id = Column(Integer, ForeignKey("real_drivers.id"))
    p2_driver_id = Column(Integer, ForeignKey("real_drivers.id"))
    p3_driver_id = Column(Integer, ForeignKey("real_drivers.id"))
    p4_driver_id = Column(Integer, ForeignKey("real_drivers.id"))
    p5_driver_id = Column(Integer, ForeignKey("real_drivers.id"))
    p6_driver_id = Column(Integer, ForeignKey("real_drivers.id"))
    p7_driver_id = Column(Integer, ForeignKey("real_drivers.id"))
    p8_driver_id = Column(Integer, ForeignKey("real_drivers.id"))
    p9_driver_id = Column(Integer, ForeignKey("real_drivers.id"))
    p10_driver_id = Column(Integer, ForeignKey("real_drivers.id"))

    race = relationship("Race", back_populates="result")