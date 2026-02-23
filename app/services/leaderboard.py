from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.models.ranking_cache import RankingCache
from app.models.bet import Bet
from app.models.team import Team
from app.models.race import Race

class LeaderboardService:
    
    def refresh_leaderboard(self, db: Session, season_id: int):
        """
        Recalcula todo o ranking da temporada e salva no cache.
        Chamado após processamento de corridas ou penalidades.
        """
        print(f"--- 🔄 Atualizando Cache de Ranking (Temporada {season_id}) ---")
        
        # 1. Limpar Cache Antigo desta temporada
        db.query(RankingCache).filter(RankingCache.season_id == season_id).delete()
        
        # --- 2. CACHE DE PILOTOS (DRIVERS) ---
        # Soma pontos de todas as corridas finalizadas
        drivers_data = db.query(
            Bet.user_id,
            func.sum(Bet.points).label("total")
        ).join(Race).filter(
            Race.season_id == season_id,
            Race.status == 'FINISHED'
        ).group_by(Bet.user_id).order_by(desc("total")).all()
        
        driver_cache = []
        for i, (user_id, points) in enumerate(drivers_data):
            driver_cache.append(RankingCache(
                season_id=season_id,
                category='DRIVER',
                entity_id=user_id,
                points=points,
                position=i + 1
            ))
        
        if driver_cache:
            db.add_all(driver_cache)

        # --- 3. CACHE DE CONSTRUTORES (TEAMS) ---
        # Para times, podemos confiar no campo 'total_points' que já mantemos atualizado,
        # ou recalcular tudo para garantir consistência. Vamos confiar no Team.total_points por enquanto.
        teams_data = db.query(Team).filter(
            Team.season_id == season_id
        ).order_by(desc(Team.total_points)).all()
        
        team_cache = []
        for i, team in enumerate(teams_data):
            team_cache.append(RankingCache(
                season_id=season_id,
                category='TEAM',
                entity_id=team.id,
                points=team.total_points,
                position=i + 1
            ))
            
        if team_cache:
            db.add_all(team_cache)
            
        db.commit()
        print("--- ✅ Cache Atualizado com Sucesso ---")