import json
from sqlalchemy.orm import Session
from pywebpush import webpush, WebPushException
from app.core.config import settings
from app.models.subscription import PushSubscription

class PushService:
    
    def send_notification(self, subscription: PushSubscription, data: dict):
        """Envia um push para uma inscrição específica"""
        if not settings.VAPID_PRIVATE_KEY:
            return

        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {
                        "p256dh": subscription.p256dh_key,
                        "auth": subscription.auth_key
                    }
                },
                data=json.dumps(data),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": settings.VAPID_CLAIMS_EMAIL}
            )
        except WebPushException as ex:
            print(f"❌ Erro Push: {ex}")
            # Todo: Se ex.response.status_code == 410, deletar a inscrição do banco.

    def notify_user(self, db: Session, user_id: int, title: str, body: str, url: str = "/dashboard"):
        """Notifica um único usuário"""
        subs = db.query(PushSubscription).filter(PushSubscription.user_id == user_id).all()
        self._dispatch_batch(subs, title, body, url)

    def broadcast_notification(self, db: Session, title: str, body: str, url: str = "/dashboard"):
        """Notifica TODOS os usuários inscritos (Broadcast)"""
        subs = db.query(PushSubscription).all()
        print(f"📢 Iniciando Broadcast Push para {len(subs)} dispositivos...")
        self._dispatch_batch(subs, title, body, url)

    def _dispatch_batch(self, subs, title, body, url):
        """Helper para envio em lote"""
        payload = {
            "notification": {
                "title": title,
                "body": body,
                "icon": "assets/icons/icon-192x192.png",
                "vibrate": [100, 50, 100],
                "data": { "url": url }
            }
        }
        for sub in subs:
            self.send_notification(sub, payload)