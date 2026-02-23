from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.models.achievement import Achievement, UserAchievement, AchievementRuleType
from app.models.user import User
from app.models.bet import Bet
from app.models.race import Race, RaceResult
from app.models.team import Team

class BadgeService:
    
    def check_achievements_after_race(self, db: Session, user_id: int, race_id: int):
        """
        Verifica medalhas de performance (Poles, Pontos, etc) após uma corrida.
        """
        user = db.query(User).filter(User.id == user_id).first()
        bet = db.query(Bet).filter(Bet.user_id == user_id, Bet.race_id == race_id).first()
        race_result = db.query(RaceResult).filter(RaceResult.race_id == race_id).first()
        
        if not user or not bet or not race_result:
            return []

        # Busca IDs de conquistas que o usuário JÁ TEM (para não repetir as únicas)
        # Nota: Se quiser permitir múltiplos "Sniper" no futuro, ajuste aqui. Por enquanto, performance é única.
        existing_ids = db.query(UserAchievement.achievement_id).filter(UserAchievement.user_id == user_id).all()
        existing_ids = [x[0] for x in existing_ids]
        
        available_badges = db.query(Achievement).filter(Achievement.id.notin_(existing_ids)).all()
        
        new_badges = []

        for badge in available_badges:
            if self._check_rule(db, badge, user_id, bet, race_result):
                # Concede a medalha (sem season_id pois é de corrida)
                self._grant_badge(db, user_id, badge.id, race_id=race_id)
                new_badges.append(badge.name)
        
        return new_badges

    def _grant_badge(self, db: Session, user_id: int, achievement_id: int, race_id: int = None, team_id: int = None, season_id: int = None):
        """Salva a conquista no banco com todos os contextos"""
        new_ua = UserAchievement(
            user_id=user_id,
            achievement_id=achievement_id,
            race_id=race_id,
            team_id=team_id,
            season_id=season_id, # <--- Importante para Campeões
            seen=False
        )
        db.add(new_ua)
        db.commit()

    def _check_rule(self, db: Session, badge: Achievement, user_id: int, current_bet: Bet, result: RaceResult) -> bool:
        """Roteador de regras de corrida."""
        rule = badge.rule_type
        target = badge.threshold

        # Ignora regras de fim de temporada aqui
        if rule in [AchievementRuleType.PILOT_RANKING, AchievementRuleType.TEAM_RANKING]:
            return False

        if rule == AchievementRuleType.RACE_POINTS:
            return current_bet.points >= target

        elif rule == AchievementRuleType.TOTAL_POINTS:
            # Soma total (sem filtro de status para pegar a corrida atual também)
            total = db.query(func.sum(Bet.points)).join(Race).filter(
                Bet.user_id == user_id
            ).scalar() or 0
            return total >= target

        elif rule == AchievementRuleType.POLE_HITS:
            return self._count_hits(db, user_id, "pole_driver_id") >= target

        elif rule == AchievementRuleType.WINNER_HITS:
            return self._count_hits(db, user_id, "winning_team_id") >= target

        elif rule == AchievementRuleType.DOTD_HITS:
            return self._count_hits(db, user_id, "dotd_driver_id") >= target

        elif rule == AchievementRuleType.RACES_PARTICIPATED:
            count = db.query(Bet).join(Race).filter(Bet.user_id == user_id).count()
            return count >= target

        return False

    def _count_hits(self, db: Session, user_id: int, field_name: str) -> int:
        bet_field = getattr(Bet, field_name)
        result_field = getattr(RaceResult, field_name)
        # Conta acertos comparando aposta x resultado
        hits = db.query(Bet).join(Race).join(RaceResult).filter(
            Bet.user_id == user_id,
            bet_field == result_field 
        ).count()
        return hits

    # --- PREMIAÇÃO DE FIM DE TEMPORADA ---
    def process_season_end_awards(self, db: Session, season_id: int):
        print(f"--- 🏆 Iniciando Premiação da Temporada {season_id} ---")
        
        ranking_badges = db.query(Achievement).filter(
            Achievement.rule_type.in_([AchievementRuleType.PILOT_RANKING, AchievementRuleType.TEAM_RANKING])
        ).all()
        
        if not ranking_badges:
            return

        # Ranking Pilotos
        driver_ranking = db.query(
            Bet.user_id,
            func.sum(Bet.points).label("total")
        ).join(Race).filter(
            Race.season_id == season_id
        ).group_by(Bet.user_id).order_by(desc("total")).all()
        
        driver_ids_ranked = [row.user_id for row in driver_ranking]

        # Ranking Construtores
        team_ranking = db.query(Team).filter(
            Team.season_id == season_id
        ).order_by(desc(Team.total_points)).all()

        count = 0
        for badge in ranking_badges:
            target_pos = badge.threshold 
            idx = target_pos - 1 
            
            if badge.rule_type == AchievementRuleType.PILOT_RANKING:
                if idx < len(driver_ids_ranked):
                    winner_id = driver_ids_ranked[idx]
                    # Passa season_id para permitir multicampeonato
                    self._grant_badge_if_not_exists(db, winner_id, badge.id, season_id=season_id)
                    count += 1

            elif badge.rule_type == AchievementRuleType.TEAM_RANKING:
                if idx < len(team_ranking):
                    winner_team = team_ranking[idx]
                    # Passa season_id e team_id
                    self._grant_badge_if_not_exists(db, winner_team.captain_id, badge.id, team_id=winner_team.id, season_id=season_id)
                    count += 1
                    if winner_team.partner_id:
                        self._grant_badge_if_not_exists(db, winner_team.partner_id, badge.id, team_id=winner_team.id, season_id=season_id)
                        count += 1
        
        print(f"--- 🎉 Premiação Concluída. {count} medalhas entregues. ---")

    def _grant_badge_if_not_exists(self, db: Session, user_id: int, achievement_id: int, team_id: int = None, season_id: int = None):
        """
        Verifica duplicidade.
        Se for badge de temporada (season_id != None), verifica se já tem NESSA temporada.
        Se for badge comum, verifica se já tem ALGUMA vez.
        """
        query = db.query(UserAchievement).filter(
            UserAchievement.user_id == user_id,
            UserAchievement.achievement_id == achievement_id
        )

        if season_id:
            query = query.filter(UserAchievement.season_id == season_id)
        
        exists = query.first()
        
        if not exists:
            self._grant_badge(db, user_id, achievement_id, team_id=team_id, season_id=season_id)