import io
from datetime import UTC, datetime, timedelta
from xml.etree import ElementTree

from PIL import Image


def test_auth_csrf_and_logout(client, post_data):
    assert client.post("/api/admin/posts", json=post_data).status_code == 401
    response = client.post(
        "/api/admin/login", json={"username": "writer", "password": "a-safe-test-password"}
    )
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie
    assert client.post("/api/admin/posts", json=post_data).status_code == 403
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    assert (
        client.post(
            "/api/admin/posts", json=post_data, headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )
    assert client.post("/api/admin/posts", json=post_data).status_code == 201
    assert client.post("/api/admin/logout").status_code == 200
    assert client.get("/api/admin/posts").status_code == 401


def test_login_throttle_persists_failed_attempts(client):
    for _ in range(10):
        assert (
            client.post(
                "/api/admin/login", json={"username": "writer", "password": "wrong"}
            ).status_code
            == 401
        )
    assert (
        client.post(
            "/api/admin/login", json={"username": "writer", "password": "a-safe-test-password"}
        ).status_code
        == 429
    )


def test_public_filters_search_pagination_and_seo(admin, post_data):
    published = admin.post("/api/admin/posts", json=post_data).json()
    admin.post("/api/admin/posts", json={**post_data, "slug": "draft", "status": "draft"})
    admin.post("/api/admin/posts", json={**post_data, "slug": "about", "type": "page"})
    future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    admin.post("/api/admin/posts", json={**post_data, "slug": "future", "published_at": future})
    listing = admin.get("/api/posts?limit=1&q=学习").json()
    assert listing["total"] == 1 and listing["items"][0]["id"] == published["id"]
    assert "body" not in listing["items"][0] and "html" not in listing["items"][0]
    assert admin.get("/api/posts/draft").status_code == 404
    assert admin.get("/api/posts/future").status_code == 404
    assert admin.get("/api/posts/about").status_code == 200
    assert admin.get("/api/tags").json()[0]["count"] == 1
    assert admin.get("/api/posts?q=%25").json()["total"] == 0
    assert admin.get("/api/posts?page=0").status_code == 422
    page = admin.get("/python-notes/")
    assert page.status_code == 200 and "Python 学习笔记" in page.text and "print(1)" in page.text
    assert 'rel="canonical"' in page.text
    assert admin.get("/draft/").status_code == 404
    assert admin.get("/missing/").status_code == 404
    assert admin.get("/api/typo").status_code == 404
    rss = ElementTree.fromstring(admin.get("/rss/").content)
    assert len(rss.findall("./channel/item")) == 1
    assert "draft" not in admin.get("/sitemap.xml").text


def test_revision_conflict_slug_redirect_and_delete(admin, post_data):
    p = admin.post("/api/admin/posts", json=post_data).json()
    assert p["excerpt"] == ""  # Keep automatic excerpts editable as an empty field.
    assert admin.post("/api/admin/posts", json=post_data).status_code == 409
    update = {**post_data, "slug": "renamed", "version": p["version"]}
    changed = admin.put("/api/admin/posts/" + p["id"], json=update)
    assert changed.status_code == 200
    assert admin.put("/api/admin/posts/" + p["id"], json=update).status_code == 409
    old = admin.get("/python-notes/", follow_redirects=False)
    assert old.status_code == 301 and old.headers["location"] == "/renamed/"
    assert admin.post("/api/admin/posts", json=post_data).status_code == 409
    assert admin.get("/api/posts/python-notes").json()["redirect"] == "renamed"
    assert admin.delete("/api/admin/posts/" + p["id"]).status_code == 204
    assert admin.get("/api/posts/renamed").status_code == 404
    assert admin.get("/api/tags").json() == []


def test_html_sanitization_and_safe_urls(admin, post_data):
    body = '<h2>相同</h2><h2>相同</h2><script>alert(1)</script><img src=x onerror=alert(2)><a href="javascript:alert(3)">bad</a><pre><code class="language-python">print(1)</code></pre>'
    result = admin.post("/api/admin/preview", json={"body": body, "format": "html"})
    html = result.json()["html"]
    assert "<script" not in html and "onerror" not in html and "javascript:" not in html
    assert "相同-2" in html and "language-python" in html
    assert (
        admin.post(
            "/api/admin/posts", json={**post_data, "feature_image": "javascript:alert(1)"}
        ).status_code
        == 422
    )
    assert admin.post("/api/admin/posts", json={**post_data, "slug": "admin"}).status_code == 422


def test_custom_tag_slug_survives_article_save(admin, post_data):
    tag = admin.post("/api/admin/tags", json={"name": "python", "slug": "python-language"}).json()
    p = admin.post("/api/admin/posts", json=post_data).json()
    assert p["tags"][0]["id"] == tag["id"]
    assert admin.get("/api/posts?tag=python-language").json()["total"] == 1


def test_management_documents_use_workspace_path(client):
    for path in ("/admin", "/admin/", "/admin/login", "/admin/posts"):
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 404
        assert "location" not in response.headers
    for path in ("/workspace", "/workspace/login", "/workspace/posts"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-robots-tag"] == "noindex, nofollow"
        assert 'name="robots"' in response.text
    reset_page = client.get("/workspace/reset-password")
    assert reset_page.headers["referrer-policy"] == "no-referrer"
    assert "Disallow: /workspace" in client.get("/robots.txt").text


def test_concurrent_writers_cannot_overwrite_each_other(admin, post_data):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    p = admin.post("/api/admin/posts", json=post_data).json()
    barrier = Barrier(2)

    def update(title):
        barrier.wait()
        return admin.put(
            "/api/admin/posts/" + p["id"],
            json={**post_data, "title": title, "version": p["version"]},
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(update, ["Writer A", "Writer B"]))
    assert sorted(results) == [200, 409]


def test_upload_validation(admin):
    assert (
        admin.post(
            "/api/admin/images", files={"file": ("evil.svg", b"<svg/>", "image/svg+xml")}
        ).status_code
        == 422
    )
    image = io.BytesIO()
    Image.new("RGB", (8, 8), "red").save(image, format="PNG")
    result = admin.post(
        "/api/admin/images", files={"file": ("../../evil.html", image.getvalue(), "text/html")}
    )
    assert result.status_code == 201 and result.json()["url"].endswith(".png")
    assert admin.get(result.json()["url"]).headers["content-type"] == "image/png"


def test_upload_accepts_supported_codecs_and_rejects_tiff(admin):
    for format, media_type in (
        ("JPEG", "image/jpeg"),
        ("WEBP", "image/webp"),
        ("GIF", "image/gif"),
        ("TIFF", "image/tiff"),
    ):
        image = io.BytesIO()
        Image.new("RGB", (8, 8), "red").save(image, format=format)
        response = admin.post(
            "/api/admin/images", files={"file": ("image", image.getvalue(), media_type)}
        )
        if format == "TIFF":
            assert response.status_code == 422
        else:
            assert response.status_code == 201
            assert admin.get(response.json()["url"]).headers["content-type"] == media_type
