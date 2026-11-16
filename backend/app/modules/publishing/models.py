from pydantic import BaseModel

from app.common.models import Page
from app.modules.post.models import PostSummary
from app.modules.site.models import SiteInput


class InitialDocument(BaseModel):
    site: SiteInput
    path: str
    posts: Page[PostSummary] | None = None
