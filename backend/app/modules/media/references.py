"""Find and replace local image URLs without rewriting Markdown or external hosts."""

import html
import os
import posixpath
import re
from collections.abc import Iterator
from typing import Any
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from sqlalchemy import select
from sqlalchemy.orm import Session, raiseload

from app.common.time import utc_now
from app.core.config import Settings
from app.modules.media.models import ImageUsage
from app.modules.post.content import render
from app.modules.post.models import PostOrm
from app.modules.site.models import SiteSettingOrm

PREFIX = "/content/images/"
URLS = re.compile(
    r"""(?<![\w/:])(?:(?:https?:)?//[^/\s<>"'`]+)?/content/images/"""
    r"""(?:[^\s<>"'`()\[\]]|\([^()\s<>"'`]*\))+"""
)
ATTRIBUTES = re.compile(r"""\b(?:src|href|poster)\s*=\s*(["'])(.*?)\1""", re.DOTALL)


def reference_key(path: str) -> str:
    """Match URL paths using the same case rules as local storage."""
    return os.path.normcase(path).replace("\\", "/")


def local_path(url: str, settings: Settings, *, normalize_case: bool = True) -> str | None:
    try:
        parsed = urlsplit(html.unescape(url))
        hosts = {urlsplit(origin).netloc.lower() for origin in settings.allowed_origins}
        hosts.add(urlsplit(settings.site_url).netloc.lower())
        if parsed.netloc and parsed.netloc.lower() not in hosts:
            return None
        if parsed.scheme and parsed.scheme not in {"http", "https"}:
            return None
        path = posixpath.normpath(unquote(parsed.path).replace("\\", "/"))
        if not path.startswith(PREFIX):
            return None
        relative = path[len(PREFIX) :]
        return reference_key(relative) if normalize_case else relative
    except ValueError:
        return None


def image_url(path: str) -> str:
    return PREFIX + quote(path, safe="/")


def paths_in(text: str, settings: Settings) -> set[str]:
    urls = [match.group() for match in URLS.finditer(text)]
    urls.extend(match[2] for match in ATTRIBUTES.finditer(text))
    if "\n" not in text:
        urls.append(text)
    return {path for url in urls if (path := local_path(url, settings)) is not None}


def strings_in(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from strings_in(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings_in(item)


def find_usages(session: Session, settings: Settings) -> dict[str, list[ImageUsage]]:
    usages: dict[str, list[ImageUsage]] = {}
    posts = session.execute(
        select(
            PostOrm.id, PostOrm.title, PostOrm.body, PostOrm.html, PostOrm.feature_image
        ).execution_options(yield_per=50)
    )
    for post in posts:
        paths = set().union(
            *(paths_in(text, settings) for text in (post.body, post.html, post.feature_image))
        )
        for path in paths:
            usages.setdefault(path, []).append(
                ImageUsage(title=post.title, url=f"/workspace/posts/{post.id}")
            )
    for setting in session.scalars(select(SiteSettingOrm)):
        for path in set().union(*(paths_in(text, settings) for text in strings_in(setting.value))):
            usages.setdefault(path, []).append(
                ImageUsage(title=f"Site: {setting.key}", url="/workspace/settings")
            )
    return usages


def replace_text(text: str, old: str, new: str, settings: Settings) -> str:
    def replace_url(url: str) -> str:
        if local_path(url, settings) != reference_key(old):
            return url
        parsed = urlsplit(url)
        return urlunsplit(parsed._replace(path=image_url(new)))

    if local_path(text, settings) == reference_key(old):
        return replace_url(text)
    text = ATTRIBUTES.sub(lambda match: match[0].replace(match[2], replace_url(match[2]), 1), text)
    return URLS.sub(lambda match: replace_url(match[0]), text)


def replace_value(value: Any, old: str, new: str, settings: Settings) -> Any:
    if isinstance(value, str):
        return replace_text(value, old, new, settings)
    if isinstance(value, list):
        return [replace_value(item, old, new, settings) for item in value]
    if isinstance(value, dict):
        return {key: replace_value(item, old, new, settings) for key, item in value.items()}
    return value


def update_references(session: Session, settings: Settings, old: str, new: str) -> None:
    for post in session.scalars(
        select(PostOrm).options(raiseload("*")).execution_options(yield_per=50)
    ):
        body = replace_text(post.body, old, new, settings)
        cover = replace_text(post.feature_image, old, new, settings)
        if body != post.body or cover != post.feature_image:
            post.body, post.feature_image = body, cover
            post.html, post.plain_text = render(body, post.format)
            post.version += 1
            post.updated_at = utc_now()
    for setting in session.scalars(select(SiteSettingOrm)):
        value = replace_value(setting.value, old, new, settings)
        if value != setting.value:
            setting.value = value
