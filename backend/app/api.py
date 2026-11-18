"""API route composition. Individual features own their route declarations."""

from fastapi import APIRouter, Depends

from app.modules.analytics.views import admin_router as admin_analytics_router
from app.modules.analytics.views import router as analytics_router
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.views import admin_router as admin_auth_router
from app.modules.auth.views import router as auth_router
from app.modules.health.views import router as health_router
from app.modules.mail.views import router as mail_router
from app.modules.media.views import router as media_router
from app.modules.post.views import admin_router as admin_post_router
from app.modules.post.views import router as post_router
from app.modules.site.views import admin_router as admin_site_router
from app.modules.site.views import router as site_router
from app.modules.tag.views import admin_router as admin_tag_router
from app.modules.tag.views import router as tag_router
from app.modules.transfer.views import router as transfer_router

api_router = APIRouter(prefix="/api")
api_router.include_router(health_router)
api_router.include_router(analytics_router)
api_router.include_router(auth_router)
api_router.include_router(post_router)
api_router.include_router(tag_router)
api_router.include_router(site_router)

# Every administrator feature inherits session and CSRF checks at this boundary.
# Sign-in is the one public /admin endpoint and remains in auth_router above.
admin_router = APIRouter(prefix="/admin", dependencies=[Depends(get_current_user)])
for router in (
    admin_auth_router,
    admin_post_router,
    admin_tag_router,
    admin_site_router,
    admin_analytics_router,
    mail_router,
    media_router,
    transfer_router,
):
    admin_router.include_router(router)
api_router.include_router(admin_router)
