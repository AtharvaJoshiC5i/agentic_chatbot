"""HTTP route modules."""

from fastapi import APIRouter

from app.routes.actions import router as actions_router
from app.routes.approvals import router as approvals_router
from app.routes.agent import router as agent_router
from app.routes.auth import router as auth_router
from app.routes.chat import router as chat_router
from app.routes.cases import router as cases_router
from app.routes.dashboard import router as dashboard_router
from app.routes.data_browser import router as data_browser_router
from app.routes.documents import router as documents_router
from app.routes.health import router as health_router
from app.routes.monitoring import router as monitoring_router
from app.routes.llm import router as llm_router
from app.routes.investigation import router as investigation_router
from app.routes.orders import router as orders_router
from app.routes.products import router as products_router
from app.routes.recovery import router as recovery_router
from app.routes.notifications import router as notifications_router
from app.routes.refunds import router as refunds_router
from app.routes.replacements import router as replacements_router
from app.routes.returns import router as returns_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router, tags=["auth"])
api_router.include_router(returns_router, tags=["returns"])
api_router.include_router(investigation_router, tags=["investigation"])
api_router.include_router(orders_router, tags=["orders"])
api_router.include_router(products_router, tags=["products"])
api_router.include_router(cases_router, tags=["cases"])
api_router.include_router(refunds_router, tags=["refunds"])
api_router.include_router(replacements_router, tags=["replacements"])
api_router.include_router(notifications_router, tags=["notifications"])
api_router.include_router(recovery_router, tags=["recovery"])
api_router.include_router(actions_router, tags=["actions"])
api_router.include_router(approvals_router, tags=["approvals"])
api_router.include_router(dashboard_router, tags=["dashboard"])
api_router.include_router(monitoring_router, tags=["monitoring"])
api_router.include_router(chat_router, tags=["chat"])
api_router.include_router(documents_router, tags=["documents"])
api_router.include_router(data_browser_router, tags=["data-browser"])
api_router.include_router(agent_router, tags=["agent"])
api_router.include_router(llm_router, tags=["llm"])
