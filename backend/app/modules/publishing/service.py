"""Public HTML documents, crawler metadata, and feeds backed by ORM services."""

import re
from email.utils import format_datetime
from html import escape
from pathlib import Path
from urllib.parse import quote, unquote
from xml.etree.ElementTree import Element, SubElement, tostring

from bs4 import BeautifulSoup
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import select

from app.common.database import connect, read_settings
from app.common.models import Page
from app.core.config import Settings
from app.core.paths import is_workspace_path
from app.modules.post.models import PostOrm, PostRedirectOrm, PostSummary
from app.modules.post.service import list_posts, public_predicate
from app.modules.publishing.models import InitialDocument
from app.modules.publishing.rendering import home_content


def rss(*, config: Settings) -> Response:
    root = Element("rss", version="2.0")
    channel = SubElement(root, "channel")
    with connect(config) as session:
        info = read_settings(session)
        for key, value in [
            ("title", info["title"]),
            ("link", config.site_url),
            ("description", info["description"]),
        ]:
            SubElement(channel, key).text = str(value)
        records = session.scalars(
            select(PostOrm)
            .where(PostOrm.type == "post", public_predicate())
            .order_by(PostOrm.published_at.desc())
            .limit(50)
        )
        for post in records:
            item = SubElement(channel, "item")
            url = config.site_url + "/" + quote(post.slug) + "/"
            for key, value in [
                ("title", post.title),
                ("link", url),
                ("guid", url),
                ("description", post.html),
                ("pubDate", format_datetime(post.published_at)),
            ]:
                SubElement(item, key).text = str(value)
    return Response(
        tostring(root, encoding="utf-8", xml_declaration=True), media_type="application/rss+xml"
    )


def sitemap(*, config: Settings) -> Response:
    root = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    SubElement(SubElement(root, "url"), "loc").text = config.site_url + "/"
    with connect(config) as session:
        for post in session.scalars(select(PostOrm).where(public_predicate())):
            item = SubElement(root, "url")
            SubElement(item, "loc").text = config.site_url + "/" + quote(post.slug) + "/"
            SubElement(item, "lastmod").text = post.updated_at.isoformat()
    return Response(
        tostring(root, encoding="utf-8", xml_declaration=True), media_type="application/xml"
    )


def seo_page(config: Settings, index: Path, path: str) -> HTMLResponse | RedirectResponse:
    path = unquote(path).strip("/")
    status = 200
    canonical = config.site_url + ("/" + quote(path, safe="/") if path else "") + "/"
    with connect(config) as session:
        info = read_settings(session)
        initial = InitialDocument(site=info, path="/" + path)
        home = False
        title, description, image = info["title"], info["description"], info["cover"]
        content = f"<h1>{escape(title)}</h1>"
        if is_workspace_path("/" + path):
            content, title = "", "Content management"
        elif path in ("", "archive", "tags") or re.fullmatch(
            r"(page/\d+|tag/[^/]+(?:/page/\d+)?|author/[^/]+(?:/page/\d+)?)", path
        ):
            tag = path.split("/")[1] if path.startswith("tag/") else ""
            author = path.split("/")[1] if path.startswith("author/") else ""
            page_match = re.search(r"(?:^|/)page/(\d+)$", path)
            page = max(1, int(page_match.group(1))) if page_match else 1
            data = list_posts(
                session, page=page, limit=info["posts_per_page"], tag=tag, author=author
            )
            if page > data["pages"] or ((tag or author) and not data["total"]):
                status = 404
            if path not in ("archive", "tags"):
                home = True
                initial.posts = Page[PostSummary].model_validate(data)
                content = home_content(initial.site, initial.posts, tag, author)
            else:
                for post in data["items"]:
                    content += f'<article><h2><a href="/{quote(post["slug"])}/">{escape(post["title"])}</a></h2><p>{escape(post["excerpt"])}</p></article>'
        else:
            post = session.scalar(select(PostOrm).where(PostOrm.slug == path, public_predicate()))
            if post is None:
                alias = session.scalar(
                    select(PostOrm.slug)
                    .join(PostRedirectOrm)
                    .where(PostRedirectOrm.slug == path, public_predicate())
                )
                if alias:
                    return RedirectResponse("/" + quote(alias) + "/", status_code=301)
                status, title, content = 404, "Page not found", "<h1>Page not found</h1>"
            else:
                title = post.title + " · " + info["title"]
                description = post.excerpt or post.plain_text[:180]
                image = post.feature_image or image
                content = f"<article><h1>{escape(post.title)}</h1>{post.html}</article>"
        document = BeautifulSoup(index.read_text(encoding="utf-8"), "html.parser")
        document.title.string = title
        for node in document.select(
            'meta[name="description"],link[rel="canonical"],meta[property^="og:"]'
        ):
            node.decompose()
        document.head.append(
            document.new_tag("meta", attrs={"name": "description", "content": description})
        )
        document.head.append(document.new_tag("link", rel="canonical", href=canonical))
        for key, value in {
            "title": title,
            "description": description,
            "url": canonical,
            "image": url_absolute(config.site_url, image),
            "type": "article" if is_article_path(path) else "website",
        }.items():
            document.head.append(
                document.new_tag("meta", attrs={"property": "og:" + key, "content": value})
            )
        if is_workspace_path("/" + path):
            document.head.append(
                document.new_tag("meta", attrs={"name": "robots", "content": "noindex,nofollow"})
            )
        root = document.select_one("#app")
        if root is not None:
            if content:
                root.clear()
            markup = content if home else f'<div class="seo-content">{content}</div>'
            root.append(BeautifulSoup(markup, "html.parser"))
        seed = document.new_tag("script", id="initial-document", type="application/json")
        seed.string = initial.model_dump_json(exclude_none=True).replace("<", "\\u003c")
        document.head.append(seed)
        if home and initial.site.cover:
            document.head.append(
                document.new_tag(
                    "link",
                    rel="preload",
                    href=initial.site.cover,
                    attrs={"as": "image", "fetchpriority": "high"},
                )
            )
        return HTMLResponse(str(document), status_code=status)


def is_article_path(path: str) -> bool:
    return bool(
        path
        and "/" not in path
        and path not in ("tags", "archive")
        and not is_workspace_path("/" + path)
    )


def url_absolute(base: str, value: str) -> str:
    return base + value if value.startswith("/") else value
