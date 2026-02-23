from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base

class Bet(Base):
    """O Palpite do Usuário"""
    __tablename__ = "bets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    race_id = Column(Integer, ForeignKey("races.id"), nullable=False)
    
    # NOVO: Snapshot da equipe no momento da aposta
    # Permite saber por qual equipe o usuário corria nesta data
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True) 

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    points = Column(Integer, default=0) 

    # Palpites Extras
    pole_driver_id = Column(Integer, ForeignKey("real_drivers.id"))
    dotd_driver_id = Column(Integer, ForeignKey("real_drivers.id"))
    winning_team_id = Column(Integer, ForeignKey("real_teams.id"))

    # Palpites Top 10
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

    race = relationship("Race")
    
    # Relacionamento para acessar dados da equipe histórica
    team = relationship("Team")