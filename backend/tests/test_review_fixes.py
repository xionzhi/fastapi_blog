import json

from bs4 import BeautifulSoup

from app.modules.post.models import PostRead


def test_pagination_rejects_unbounded_api_pages_and_returns_public_404(admin, post_data):
    admin.post("/api/admin/posts", json=post_data)
    huge = "1" + "0" * 30
    for endpoint in ("/api/posts", "/api/admin/posts"):
        assert admin.get(f"{endpoint}?page={huge}").status_code == 422
        result = admin.get(f"{endpoint}?page=1000000000")
        assert result.status_code == 200
        assert result.json()["items"] == []
    for path in (f"/page/{huge}/", f"/tag/python/page/{huge}/"):
        assert admin.get(path).status_code == 404


def test_static_namespace_cannot_be_saved_as_a_post(admin, post_data):
    result = admin.post("/api/admin/posts", json={**post_data, "slug": "legacy"})
    assert result.status_code == 422
    assert admin.get("/api/admin/posts").json()["total"] == 0


def test_article_initial_data_is_public_sanitized_and_scoped(admin, post_data):
    attack = '</script><script id="injected">alert(1)</script>'
    published = admin.post(
        "/api/admin/posts", json={**post_data, "body": "# Heading\n\n" + attack}
    ).json()
    admin.post("/api/admin/posts", json={**post_data, "slug": "private", "status": "draft"})
    response = admin.get(f"/{published['slug']}/")
    doc = BeautifulSoup(response.text, "html.parser")
    seed = json.loads(doc.select_one("#initial-document").string)
    detail = PostRead.model_validate(admin.get(f"/api/posts/{published['slug']}").json())
    assert seed["post"] == detail.model_dump(mode="json", exclude_none=True)
    assert "body" not in seed["post"]
    assert doc.select_one("script#injected") is None
    assert all(item["slug"] != "private" for item in seed["post"]["related"])
    for path in ("/", "/workspace/login", "/private/", "/missing/"):
        doc = BeautifulSoup(admin.get(path).text, "html.parser")
        assert "post" not in json.loads(doc.select_one("#initial-document").string)


def test_administrator_site_reads_bypass_public_caching(admin):
    site = admin.get("/api/site").json()
    site["title"] = "Fresh settings"
    written = admin.put("/api/admin/site", json=site)
    assert written.status_code == 200
    assert written.json()["title"] == site["title"]
    read = admin.get("/api/admin/site")
    assert read.status_code == 200
    assert read.json()["title"] == site["title"]
    assert read.headers["cache-control"] == "no-store"
    admin.post("/api/admin/logout")
    assert admin.get("/api/admin/site").status_code == 401
