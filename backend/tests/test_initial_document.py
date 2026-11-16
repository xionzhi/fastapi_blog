import json

from bs4 import BeautifulSoup


def test_home_first_paint_contains_cover_and_public_initial_data(admin, post_data):
    admin.post("/api/admin/posts", json=post_data)
    admin.post("/api/admin/posts", json={**post_data, "slug": "private-draft", "status": "draft"})
    site = admin.get("/api/site").json()
    site.update(cover="/content/images/slow-cover.webp", logo="/content/images/logo.png")
    assert admin.put("/api/admin/site", json=site).status_code == 200
    response = admin.get("/")
    document = BeautifulSoup(response.text, "html.parser")
    root = document.select_one("#app")
    assert root.select_one(".seo-content") is None
    assert root.select_one("header.blog-hero + main#main-content") is not None
    image = root.select_one(".blog-hero > img.hero-cover")
    assert image["src"] == site["cover"] and image["fetchpriority"] == "high"
    assert root.select_one("#content .post-title").get_text() == post_data["title"]
    assert document.select_one('link[rel="preload"][as="image"]')["href"] == site["cover"]
    seed = json.loads(document.select_one("#initial-document").string)
    assert seed["path"] == "/" and seed["site"]["cover"] == site["cover"]
    assert seed["posts"]["total"] == 1
    assert seed["posts"]["items"][0]["slug"] == post_data["slug"]
    assert "body" not in seed["posts"]["items"][0]
    assert "private-draft" not in response.text


def test_initial_state_cannot_break_out_of_its_json_script(admin):
    site = admin.get("/api/site").json()
    attack = '</script><script id="injected">alert(1)</script>'
    site.update(title=attack, description=attack)
    assert admin.put("/api/admin/site", json=site).status_code == 200
    document = BeautifulSoup(admin.get("/").text, "html.parser")
    assert document.select_one("script#injected") is None
    assert json.loads(document.select_one("#initial-document").string)["site"]["title"] == attack
    assert document.select_one(".blog-hero h1").get_text() == attack


def test_initial_posts_are_scoped_to_collection_routes(admin, post_data):
    admin.post("/api/admin/posts", json=post_data)
    document = BeautifulSoup(admin.get("/tag/python/").text, "html.parser")
    assert document.select_one(".collection-hero .page-title").get_text() == "python"
    seed = json.loads(document.select_one("#initial-document").string)
    assert seed["path"] == "/tag/python" and seed["posts"]["total"] == 1
    assert admin.get("/page/2/").status_code == 404
    for path in ("/archive/", "/tags/", "/workspace/login", "/python-notes/"):
        document = BeautifulSoup(admin.get(path).text, "html.parser")
        seed = json.loads(document.select_one("#initial-document").string)
        assert "posts" not in seed
        assert document.select_one(".initial-home") is None
