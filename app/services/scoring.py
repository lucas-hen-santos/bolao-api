from sqlalchemy.orm import Session
from app.models.bet import Bet
from app.models.race import Race, RaceResult, RaceStatus
from app.models.team import Team
from app.models.user import User
from app.models.rivalry import Rivalry, RivalryStatus
from app.services.badge import BadgeService 
from app.services.leaderboard import LeaderboardService 
from app.services.push import PushService # <--- Importar PushService
from app.db.session import SessionLocal

def calculate_race_points(db: Session, race_id: int):
    """
    Calcula a pontuação, distribui medalhas, resolve rivais, atualiza cache e notifica.
    """
    race = db.query(Race).filter(Race.id == race_id).first()
    if not race or not race.result:
        return {"error": "Resultado oficial não encontrado."}
    
    result = race.result
    bets = db.query(Bet).filter(Bet.race_id == race_id).all()
    
    updates_count = 0
    rollback_count = 0
    badges_granted = 0 
    
    badge_service = BadgeService() 

    # --- FASE 1: ROLLBACK (Zerar pontos anteriores para recalcular) ---
    for bet in bets:
        if bet.points > 0:
            if bet.team_id:
                historical_team = db.query(Team).filter(Team.id == bet.team_id).first()
                if historical_team:
                    historical_team.total_points -= bet.points
                    rollback_count += 1
            bet.points = 0
    db.commit()

    # --- FASE 2: CÁLCULO ---
    for bet in bets:
        points = 0
        
        # Extras
        if bet.pole_driver_id == result.pole_driver_id: points += 1
        if bet.dotd_driver_id == result.dotd_driver_id: points += 1
        if bet.winning_team_id == result.winning_team_id: points += 1
        
        # Top 10 (Posição Exata)
        comparisons = [
            (bet.p1_driver_id, result.p1_driver_id),
            (bet.p2_driver_id, result.p2_driver_id),
            (bet.p3_driver_id, result.p3_driver_id),
            (bet.p4_driver_id, result.p4_driver_id),
            (bet.p5_driver_id, result.p5_driver_id),
            (bet.p6_driver_id, result.p6_driver_id),
            (bet.p7_driver_id, result.p7_driver_id),
            (bet.p8_driver_id, result.p8_driver_id),
            (bet.p9_driver_id, result.p9_driver_id),
            (bet.p10_driver_id, result.p10_driver_id),
        ]
        
        for b_id, r_id in comparisons:
            if b_id and b_id == r_id: points += 1
        
        # Atualiza Aposta e Equipe
        bet.points = points 
        if bet.team_id:
            ht = db.query(Team).filter(Team.id == bet.team_id).first()
            if ht: ht.total_points += points
            
        updates_count += 1
        db.commit() 
        
        # Verifica Medalhas
        new_badges = badge_service.check_achievements_after_race(db, bet.user_id, race_id)
        if new_badges:
            badges_granted += len(new_badges)

    # --- FASE 3: RIVAIS ---
    process_rivalries(db, race_id)

    race.status = RaceStatus.FINISHED
    db.commit()
    
    # --- FASE 4: ATUALIZAR CACHE DE RANKING ---
    leaderboard_service = LeaderboardService()
    leaderboard_service.refresh_leaderboard(db, race.season_id)
    
    # --- FASE 5: NOTIFICAR RESULTADO (PUSH) ---
    try:
        push_service = PushService()
        push_service.broadcast_notification(
            db,
            title=f"🏁 Bandeira Quadriculada: {race.name}",
            body="O resultado oficial saiu e os pontos foram calculados. Veja sua posição!",
            url="/ranking"
        )
    except Exception as e:
        print(f"❌ Erro ao enviar push de resultado: {e}")
    
    print(f"--- ✅ Processamento Concluído (Race {race_id}) ---")
    
    return {
        "message": "Cálculo realizado com sucesso.",
        "processed": updates_count,
        "rollbacks": rollback_count,
        "new_badges": badges_granted
    }

def process_rivalries(db: Session, race_id: int):
    """
    Resolve os duelos aceitos para esta corrida.
    """
    print(f"--- ⚔️ Processando Rivais (Race {race_id}) ---")
    
    rivalries = db.query(Rivalry).filter(
        Rivalry.race_id == race_id,
        Rivalry.status == RivalryStatus.ACCEPTED
    ).all()
    
    for r in rivalries:
        bet_challenger = db.query(Bet).filter(Bet.user_id == r.challenger_id, Bet.race_id == race_id).first()
        points_c = bet_challenger.points if bet_challenger else 0
        
        bet_opponent = db.query(Bet).filter(Bet.user_id == r.opponent_id, Bet.race_id == race_id).first()
        points_o = bet_opponent.points if bet_opponent else 0
        
        if points_c > points_o:
            r.winner_id = r.challenger_id
            r.margin = points_c - points_o
        elif points_o > points_c:
            r.winner_id = r.opponent_id
            r.margin = points_o - points_c
        else:
            r.winner_id = None # Empate
            r.margin = 0
            
        r.status = RivalryStatus.FINISHED
    
    db.commit()

def calculate_race_points_async_wrapper(race_id: int):
    print(f"--- ⏳ Iniciando Processamento em Background (Race {race_id}) ---")
    db = SessionLocal()
    try:
        calculate_race_points(db, race_id)
    except Exception as e:
        print(f"--- ❌ Erro no processamento (Race {race_id}): {e}")
    finally:
        db.close()