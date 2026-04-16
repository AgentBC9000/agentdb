from fastapi import APIRouter
from app.api.v1.endpoints import knowledge, auth, media, webhooks, payments

router = APIRouter()

router.include_router(auth.router,      prefix="/auth",      tags=["Auth"])
router.include_router(knowledge.router, prefix="/knowledge", tags=["Knowledge"])
router.include_router(media.router,     prefix="/media",     tags=["Media"])
router.include_router(payments.router,  prefix="/payments",  tags=["Payments"])
router.include_router(webhooks.router,  prefix="/webhooks",  tags=["Webhooks"])
