"""Public first-paint markup with the same geometry as the Vue home page."""

from html import escape
from urllib.parse import quote

from app.common.models import Page
from app.modules.post.models import PostSummary
from app.modules.site.models import SiteInput


def home_content(site: SiteInput, posts: Page[PostSummary], tag: str, author: str) -> str:
    title = author or site.title
    if tag:
        title = next((t.name for p in posts.items for t in p.tags if t.slug == tag), tag)
    collection = bool(tag or author)
    classes = "main-header blog-hero"
    if collection:
        classes += " collection-hero"
    if not site.cover:
        classes += " no-cover"
    cover = (
        f'<img class="hero-cover" src="{escape(site.cover)}" alt="" '
        'fetchpriority="high" decoding="async" aria-hidden="true">'
        if site.cover
        else ""
    )
    brand = (
        f'<a class="blog-logo" href="/"><img src="{escape(site.logo)}" '
        f'alt="{escape(site.title)}"></a>'
        if site.logo
        else f'<a class="brand-text" href="/">{escape(site.title)}</a>'
    )
    subtitle = f"{posts.total} posts" if collection else site.description
    description = f'<h2 class="page-description">{escape(subtitle)}</h2>' if subtitle else ""
    scroll = (
        '<a class="hero-scroll" href="#content" aria-label="Scroll to posts">'
        '<svg width="27" height="27" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2"><path d="m6 9 6 6 6-6"/></svg></a>'
        if not collection
        else ""
    )
    articles = []
    for post in posts.items:
        url = f"/{quote(post.slug)}/"
        avatar = (
            f'<img class="author-thumb" src="{escape(site.author_image)}" '
            f'alt="{escape(post.author)}" loading="lazy" decoding="async">'
            if site.author_image
            else ""
        )
        tags = ", ".join(f'<a href="/tag/{quote(t.slug)}/">{escape(t.name)}</a>' for t in post.tags)
        tag_links = f'<span class="meta-tags">on {tags}</span>' if tags else ""
        timestamp = post.published_at.isoformat() if post.published_at else ""
        date = post.published_at.strftime("%d %B %Y") if post.published_at else "Unpublished"
        articles.append(
            f'<article class="post list-post"><header class="post-header">'
            f'<h2 class="post-title"><a href="{url}">{escape(post.title)}</a></h2></header>'
            f'<section class="post-excerpt"><p>{escape(post.excerpt)} '
            f'<a class="read-more" href="{url}" aria-label="Read {escape(post.title)}">»</a>'
            f'</p></section><div class="post-meta article-meta">{avatar}'
            f'<a href="/author/{quote(post.author_slug)}/">{escape(post.author)}</a>'
            f'{tag_links}<time class="post-date" datetime="{timestamp}">{date}</time>'
            "</div></article>"
        )
    if not articles:
        message = "No posts on this page." if posts.page > posts.pages else "No posts yet."
        articles.append(
            f'<div class="state-message"><p>{message}</p><a href="/">Back to home</a></div>'
        )
    pagination = ""
    if posts.pages > 1:
        base = f"/tag/{quote(tag)}" if tag else f"/author/{quote(author)}" if author else ""
        previous = f"{base}/" if posts.page == 2 else f"{base}/page/{posts.page - 1}/"
        newer = (
            f'<a class="newer-posts" href="{previous}">← Newer Posts</a>' if posts.page > 1 else ""
        )
        older = (
            f'<a class="older-posts" href="{base}/page/{posts.page + 1}/">Older Posts →</a>'
            if posts.page < posts.pages
            else ""
        )
        pagination = (
            f'<nav class="pagination blog-pagination" aria-label="Post pagination">{newer}'
            f'<span class="page-number">Page {posts.page} of {posts.pages}</span>{older}</nav>'
        )
    label = "Posts by tag" if tag else "Posts by author" if author else "Latest posts"
    return (
        f'<div class="initial-home"><header class="{classes}">{cover}'
        f'<nav class="main-nav blog-nav clearfix overlay" aria-label="Main navigation">{brand}'
        '<div class="nav-actions"><button class="menu-toggle" disabled>☰ Menu</button></div>'
        f'</nav><div class="hero-shade"></div><div class="vertical">'
        f'<div class="main-header-content inner"><h1 class="page-title">{escape(title)}</h1>'
        f'{description}</div></div>{scroll}</header><main id="main-content">'
        f'<div id="content" class="content post-list"><div class="list-tools">'
        f"<span>{label} <small>/ {posts.total}</small></span>"
        '<button class="text-button" disabled>Search posts</button></div>'
        f'<div class="public-results">{"".join(articles)}{pagination}</div></div></main></div>'
    )
