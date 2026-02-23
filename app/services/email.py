from pathlib import Path
from typing import List, Dict, Any
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from app.core.config import settings
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

# Configuração do Caminho dos Templates
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_FOLDER = BASE_DIR / "templates" / "email"

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=settings.USE_CREDENTIALS,
    VALIDATE_CERTS=settings.VALIDATE_CERTS,
    TEMPLATE_FOLDER=TEMPLATE_FOLDER
)

class EmailService:
    def __init__(self):
        self.fm = FastMail(conf)

    async def send_welcome_email(self, user: User):
        """Envia email de boas vindas"""
        body_data = {
            "name": user.full_name,
            "dashboard_link": f"{settings.FRONTEND_URL}/dashboard"
        }
        message = MessageSchema(
            subject="Bem-vindo ao Bolão Tá Potente! 🏎️",
            recipients=[user.email],
            template_body=body_data,
            subtype=MessageType.html
        )
        await self.fm.send_message(message, template_name="welcome.html")

    async def send_race_open_email(self, emails: List[str], race_name: str, country: str, close_date: str):
        """Envia aviso de abertura de aposta em massa (via BCC)"""
        if not emails: return
        body_data = {
            "race_name": race_name,
            "country": country,
            "close_date": close_date,
            "link": f"{settings.FRONTEND_URL}/dashboard"
        }
        message = MessageSchema(
            subject=f"🟢 Pista Liberada: {race_name}",
            recipients=[], 
            bcc=emails, 
            template_body=body_data,
            subtype=MessageType.html
        )
        await self.fm.send_message(message, template_name="race_open.html")

    async def send_announcement(self, recipients: List[str], subject: str, message_body: str):
        """Envia aviso global"""
        if not recipients: return
        body_data = {
            "subject": subject,
            "message_body": message_body,
            "link": f"{settings.FRONTEND_URL}/dashboard"
        }
        message = MessageSchema(
            subject=f"📢 {subject} | Bolão Tá Potente",
            recipients=[], 
            bcc=recipients,
            template_body=body_data,
            subtype=MessageType.html
        )
        await self.fm.send_message(message, template_name="announcement.html")

    async def send_reset_password_email(self, user: User, token: str):
        """Envia link de redefinição de senha"""
        link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        
        body_data = {
            "name": user.full_name,
            "link": link
        }
        
        message = MessageSchema(
            subject="Redefinição de Senha 🔐",
            recipients=[user.email],
            template_body=body_data,
            subtype=MessageType.html
        )
        
        await self.fm.send_message(message, template_name="reset_password.html")

    async def send_new_challenge_email(self, opponent_email: str, challenger_name: str, race_name: str):
        """Notifica o oponente sobre um novo desafio"""
        body_data = {
            "challenger_name": challenger_name,
            "race_name": race_name,
            "link": f"{settings.FRONTEND_URL}/rivals"
        }
        message = MessageSchema(
            subject=f"⚔️ Desafio de {challenger_name}!",
            recipients=[opponent_email],
            template_body=body_data,
            subtype=MessageType.html
        )
        await self.fm.send_message(message, template_name="new_challenge.html")

    async def send_challenge_accepted_email(self, challenger_email: str, opponent_name: str, race_name: str):
        """Notifica o desafiante que o duelo foi aceito"""
        body_data = {
            "opponent_name": opponent_name,
            "race_name": race_name,
            "link": f"{settings.FRONTEND_URL}/rivals"
        }
        message = MessageSchema(
            subject=f"🔥 {opponent_name} aceitou seu desafio!",
            recipients=[challenger_email],
            template_body=body_data,
            subtype=MessageType.html
        )
        await self.fm.send_message(message, template_name="challenge_accepted.html")

    async def send_race_warning_email(self, emails: List[str], race_name: str, time_left: str):
        """
        Envia aviso de fechamento iminente (1h ou 5min).
        Usa BCC para envio em massa eficiente.
        """
        if not emails: return

        # Prepara a mensagem
        body_data = {
            "race_name": race_name,
            "time_left": time_left,
            "link": f"{settings.FRONTEND_URL}/dashboard"
        }

        # Cria o schema (Recipients vazio + BCC preenchido)
        message = MessageSchema(
            subject=f"⏳ Corra! {time_left} para o {race_name}",
            recipients=[], 
            bcc=emails,
            template_body=body_data,
            subtype=MessageType.html
        )

        try:
            await self.fm.send_message(message, template_name="race_warning.html")
            logger.info(f"📧 Email de aviso ({time_left}) enviado para {len(emails)} usuários via BCC.")
        except Exception as e:
            logger.error(f"❌ Erro ao enviar email de aviso: {e}")