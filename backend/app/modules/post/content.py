import re
import unicodedata
from urllib.parse import urlsplit

import bleach
from bs4 import BeautifulSoup
from markdown_it import MarkdownIt

MD = (
    MarkdownIt("commonmark", {"html": True, "linkify": False})
    .enable("table")
    .enable("strikethrough")
)
TAGS = set(bleach.sanitizer.ALLOWED_TAGS) | {
    "p",
    "div",
    "span",
    "br",
    "hr",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "pre",
    "img",
    "figure",
    "figcaption",
    "table",
    "thead",
    "tbody",
    "tr",
    "td",
    "th",
    "del",
    "s",
    "sup",
    "sub",
    "details",
    "summary",
    "kbd",
    "video",
    "audio",
    "source",
    "dl",
    "dt",
    "dd",
    "section",
}
ATTRS = {
    "*": ["class", "id", "title"],
    "a": ["href", "title"],
    "img": ["src", "alt", "width", "height", "loading", "decoding"],
    "code": ["class"],
    "ol": ["start"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan"],
    "video": ["src", "controls", "poster"],
    "audio": ["src", "controls"],
    "source": ["src", "type"],
}
RESERVED = {
    "api",
    "admin",
    "workspace",
    "assets",
    "content",
    "tag",
    "tags",
    "author",
    "page",
    "archive",
    "rss",
    "sitemap.xml",
    "robots.txt",
    "healthz",
}


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).lower().strip()
    return re.sub(r"-+", "-", re.sub(r"[^\w-]+", "-", value)).strip("-_")


def validate_slug(value: str, *, allow_reserved: bool = False) -> str:
    if (
        not value
        or len(value) > 200
        or slugify(value) != value
        or (not allow_reserved and value in RESERVED)
    ):
        raise ValueError(
            "Slugs must use lowercase letters, numbers, Unicode letters, underscores, or hyphens and cannot use reserved paths"
        )
    return value


def safe_url(value: str) -> str:
    if not value:
        return ""
    if any(ord(c) < 32 for c in value) or "\\" in value:
        raise ValueError("Invalid URL")
    parsed = urlsplit(value)
    if value.startswith("/") and not value.startswith("//"):
        return value
    if parsed.scheme in ("https", "http") and parsed.netloc and not parsed.username:
        return value
    raise ValueError("Use an absolute site path or an http(s) URL")


def render(body: str, format: str = "markdown") -> tuple[str, str]:
    raw = MD.render(body) if format == "markdown" else body
    soup = BeautifulSoup(raw, "html.parser")
    for node in soup(["script", "style", "iframe", "object", "embed", "form", "input"]):
        node.decompose()
    cleaned = bleach.clean(
        str(soup), tags=TAGS, attributes=ATTRS, protocols=["http", "https", "mailto"], strip=True
    )
    soup = BeautifulSoup(cleaned, "html.parser")
    ids = set()
    for i, heading in enumerate(soup.select("h1,h2,h3,h4,h5,h6")):
        base = heading.get("id") or slugify(heading.get_text()) or f"section-{i + 1}"
        key, n = base, 2
        while key in ids:
            key = f"{base}-{n}"
            n += 1
        heading["id"] = key
        ids.add(key)
    for image in soup.select("img"):
        image["loading"] = "lazy"
        image["decoding"] = "async"
    for link in soup.select("a[href]"):
        if str(link["href"]).startswith(("http://", "https://")):
            link["rel"] = "noopener noreferrer"
    return str(soup), soup.get_text(" ", strip=True)
