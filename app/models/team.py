from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class Team(Base):
    """Equipe dos Participantes (Bolão)"""
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    season_id = Column(Integer, ForeignKey("seasons.id"), nullable=False)
    
    name = Column(String(100), nullable=False)
    logo_url = Column(String(255)) # Upload do usuário
    primary_color = Column(String(7)) # Hex Code ex: #FF0000
    secondary_color = Column(String(7)) 

    # Definição da Dupla
    captain_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    partner_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Pode começar sem parceiro

    total_points = Column(Integer, default=0)

    # Relacionamentos para facilitar consultas
    captain = relationship("User", foreign_keys=[captain_id])
    partner = relationship("User", foreign_keys=[partner_id])