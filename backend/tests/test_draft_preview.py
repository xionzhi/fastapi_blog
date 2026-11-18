import json

from bs4 import BeautifulSoup


def test_draft_preview_sharing_is_opt_in_and_revocable(admin, post_data):
    draft = {**post_data, "status": "draft", "body": "Review this confidential draft."}
    created = admin.post("/api/admin/posts", json=draft)
    assert created.status_code == 201
    post = created.json()
    assert post["preview_shared"] is False
    path = f"/preview/{post['id']}"
    api_path = f"/api{path}"
    settings_path = f"/api/admin/posts/{post['id']}/preview"

    def guest(method, url, **kwargs):
        request = admin.build_request(method, url, **kwargs)
        request.headers.pop("cookie", None)
        request.headers.pop("x-csrf-token", None)
        return admin.send(request)

    for url in (path, api_path, "/preview/not-an-id"):
        response = guest("GET", url)
        assert response.status_code == 404
        assert response.headers["cache-control"] == "no-store"
        assert draft["body"] not in response.text

    assert guest("PUT", settings_path, json={"enabled": True}).status_code == 401
    enabled = admin.put(settings_path, json={"enabled": True})
    assert enabled.status_code == 200 and enabled.json() == {"enabled": True}
    assert admin.get(f"/api/admin/posts/{post['id']}").json()["preview_shared"] is True

    page = guest("GET", path)
    api = guest("GET", api_path)
    for response in (page, api):
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-robots-tag"] == "noindex, nofollow"
        assert response.headers["referrer-policy"] == "no-referrer"
    assert "cloudflareinsights.com" not in page.headers["content-security-policy"]
    document = BeautifulSoup(page.text, "html.parser")
    assert draft["body"] in document.select_one("#app").get_text()
    assert document.select_one('meta[name="robots"]')["content"] == "noindex,nofollow"
    assert not document.select('[rel="canonical"],meta[property^="og:"]')
    initial = json.loads(document.select_one("#initial-document").string)
    assert initial["post"]["id"] == post["id"]
    assert initial["post"]["html"] == api.json()["html"]
    assert "body" not in api.json() and "preview_shared" not in api.json()

    for url in ("/", "/archive/", "/api/posts?q=confidential", "/rss/", "/sitemap.xml"):
        response = guest("GET", url)
        assert post["id"] not in response.text and draft["body"] not in response.text
    assert guest("GET", f"/{post['slug']}/").status_code == 404

    edited = {**draft, "body": "Updated draft for review.", "version": post["version"]}
    updated = admin.put(f"/api/admin/posts/{post['id']}", json=edited).json()
    assert updated["preview_shared"] is True
    assert edited["body"] in guest("GET", path).text

    disabled = admin.put(settings_path, json={"enabled": False})
    assert disabled.status_code == 200 and disabled.json() == {"enabled": False}
    assert guest("GET", path).status_code == 404
    assert guest("GET", api_path).status_code == 404

    assert admin.put(settings_path, json={"enabled": True}).status_code == 200
    published = admin.put(
        f"/api/admin/posts/{post['id']}",
        json={**edited, "status": "published", "version": updated["version"]},
    ).json()
    assert published["preview_shared"] is False
    assert guest("GET", path).status_code == 404
    assert admin.put(settings_path, json={"enabled": True}).status_code == 409
    unpublished = admin.put(
        f"/api/admin/posts/{post['id']}", json={**edited, "version": published["version"]}
    ).json()
    assert unpublished["preview_shared"] is False
    assert guest("GET", api_path).status_code == 404
