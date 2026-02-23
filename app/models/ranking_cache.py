from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.db.base import Base

class RankingCache(Base):
    __tablename__ = "ranking_cache"

    id = Column(Integer, primary_key=True, index=True)
    season_id = Column(Integer, ForeignKey("seasons.id"), nullable=False, index=True)
    
    # 'DRIVER' (Pilotos) ou 'TEAM' (Construtores)
    category = Column(String(20), nullable=False) 
    
    # ID do User ou Team
    entity_id = Column(Integer, nullable=False)
    
    points = Column(Integer, default=0)
    position = Column(Integer, default=0)
    
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())