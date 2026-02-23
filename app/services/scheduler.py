from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import pytz
import logging
import asyncio

from app.db.session import SessionLocal
from app.models.race import Race, RaceStatus
from app.models.user import User

# Configuração de Logs
logger = logging.getLogger(__name__)

# Inicializa o agendador
scheduler = BackgroundScheduler()

def get_brazil_time():
    """Retorna a data/hora atual de Brasília (naive) para comparar com o banco."""
    tz = pytz.timezone('America/Sao_Paulo')
    return datetime.now(tz).replace(tzinfo=None)

def check_race_status_job():
    """Verifica status das corridas e envia notificações (Push + Email)"""
    
    # ✅ IMPORTAÇÃO TARDIA (Essencial para não travar o servidor)
    from app.services.push import PushService
    from app.services.email import EmailService
    
    logger.info(f"⏱️ [Scheduler] Verificando status...")
    db = SessionLocal()
    push_service = PushService()
    email_service = EmailService()
    
    try:
        now = get_brazil_time()
        
        # --- 1. ABERTURA (Scheduled -> Open) ---
        races_to_open = db.query(Race).filter(
            Race.status == RaceStatus.SCHEDULED,
            Race.bets_open_at <= now
        ).all()

        for race in races_to_open:
            logger.info(f"🟢 Abrindo apostas para: {race.name}")
            race.status = RaceStatus.OPEN
            db.commit()
            
            try:
                push_service.broadcast_notification(
                    db, 
                    title=f"Apostas Abertas: {race.name} 🏎️",
                    body=f"O grid para o GP de {race.country} está liberado!",
                    url="/bet-maker"
                )
            except Exception as e:
                logger.error(f"Erro push open: {e}")

        # --- 2. FECHAMENTO (Open -> Closed) ---
        races_to_close = db.query(Race).filter(
            Race.status == RaceStatus.OPEN,
            Race.bets_close_at <= now
        ).all()

        for race in races_to_close:
            logger.info(f"🔴 Fechando apostas para: {race.name}")
            race.status = RaceStatus.CLOSED
            db.commit()
            
            try:
                push_service.broadcast_notification(
                    db,
                    title="Box Fechado! 🚫",
                    body=f"Apostas encerradas para o {race.name}.",
                    url="/dashboard"
                )
            except Exception as e:
                logger.error(f"Erro push close: {e}")

        # --- 3. ALERTAS DE TEMPO (1h e 5min) ---
        open_races = db.query(Race).filter(Race.status == RaceStatus.OPEN).all()
        
        # Carrega e-mails uma vez
        active_emails = []
        if open_races:
            users = db.query(User).filter(User.is_active == True).all()
            active_emails = [u.email for u in users if u.email]

        for race in open_races:
            if not race.bets_close_at: continue
            
            time_left = race.bets_close_at - now
            minutes_left = time_left.total_seconds() / 60

            if minutes_left < 0: continue

            # Alerta 1 Hora
            if 55 <= minutes_left <= 65 and not race.alert_1h_sent:
                logger.info(f"⚠️ Alerta 1h: {race.name}")
                push_service.broadcast_notification(db, title="⏳ 1 Hora Restante", body=f"O box fecha em breve para o {race.name}.", url="/bet-maker")
                
                if active_emails:
                    try:
                        asyncio.run(email_service.send_race_warning_email(active_emails, race.name, "1 hora"))
                    except Exception as e:
                        logger.error(f"Erro email 1h: {e}")

                race.alert_1h_sent = True
                db.commit()

            # Alerta 5 Minutos
            if 2 <= minutes_left <= 7 and not race.alert_5m_sent:
                logger.info(f"🚨 Alerta 5min: {race.name}")
                push_service.broadcast_notification(db, title="🚨 5 Minutos Finais!", body=f"Última chamada para o {race.name}!", url="/bet-maker")
                
                if active_emails:
                    try:
                        asyncio.run(email_service.send_race_warning_email(active_emails, race.name, "5 minutos"))
                    except Exception as e:
                        logger.error(f"Erro email 5min: {e}")

                race.alert_5m_sent = True
                db.commit()

    except Exception as e:
        logger.error(f"❌ Erro Scheduler: {e}")
        db.rollback()
    finally:
        db.close()

def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(check_race_status_job, 'interval', minutes=1)
        scheduler.start()
        logger.info("--- 🕒 Scheduler Iniciado (1 min) ---")

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()