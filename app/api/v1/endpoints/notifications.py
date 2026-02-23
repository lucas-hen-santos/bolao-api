from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api import deps
from app.core.config import settings
from app.models.user import User
from app.models.subscription import PushSubscription
from app.schemas.subscription import PushSubscriptionCreate
from app.services.push import PushService

router = APIRouter()

@router.get("/vapid-public-key")
def get_vapid_public_key():
    if not settings.VAPID_PUBLIC_KEY:
        raise HTTPException(500, "VAPID não configurado.")
    return {"publicKey": settings.VAPID_PUBLIC_KEY}

@router.post("/subscribe")
def subscribe(
    sub_in: PushSubscriptionCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    exists = db.query(PushSubscription).filter(
        PushSubscription.endpoint == sub_in.endpoint
    ).first()
    
    if exists:
        if exists.user_id != current_user.id:
            exists.user_id = current_user.id
            db.commit()
        return {"msg": "Atualizado"}

    new_sub = PushSubscription(
        user_id=current_user.id,
        endpoint=sub_in.endpoint,
        auth_key=sub_in.keys.auth,
        p256dh_key=sub_in.keys.p256dh
    )
    db.add(new_sub)
    db.commit()
    return {"msg": "Inscrito!"}

@router.post("/test")
def send_test_notification(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Envia um push de teste para o usuário atual"""
    push_service = PushService()
    
    subs = db.query(PushSubscription).filter(PushSubscription.user_id == current_user.id).all()
    
    if not subs:
        raise HTTPException(400, "Você não tem dispositivos inscritos.")

    count = 0
    for sub in subs:
        try:
            # CORREÇÃO AQUI: Passando 'db' como primeiro argumento
            push_service.send_notification(db, sub, {
                "notification": {
                    "title": "🏎️ Teste de Motor",
                    "body": "Se você está lendo isso, o sistema está voando baixo!",
                    "icon": "assets/icons/icon-192x192.png",
                    "vibrate": [100, 50, 100],
                    "data": { "url": "/dashboard" }
                }
            })
            count += 1
        except Exception as e:
            print(f"Erro ao enviar teste: {e}")

    return {"message": f"Enviado para {count} dispositivos."}

@router.delete("/unsubscribe")
def unsubscribe(
    endpoint: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    sub = db.query(PushSubscription).filter(PushSubscription.endpoint == endpoint).first()
    if sub:
        db.delete(sub)
        db.commit()
    return {"msg": "Removido"}