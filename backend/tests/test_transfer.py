"""Native transfers preserve content, never copy credentials, and validate before writing."""

import hashlib
import json
import uuid

import pytest
from sqlalchemy import select

from app.common.database import connect
from app.modules.auth.models import UserOrm
from app.modules.transfer import service


def native_data():
    post_id, tag_id = uuid.uuid4().hex, uuid.uuid4().hex
    timestamp = "2020-01-02T03:04:05Z"
    return {
        "format": "xionzhi-blog",
        "version": 1,
        "exported_at": timestamp,
        "media_root": "data/dev/images",
        "posts": [
            {
                "id": post_id,
                "title": "Original article 中文",
                "slug": "native-article",
                "body": "# Heading\n\nOriginal text\n\n```html\n<script>example</script>\n```",
                "format": "markdown",
                "status": "published",
                "type": "post",
                "excerpt": "",
                "feature_image": "",
                "author": "Writer",
                "author_slug": "writer",
                "created_at": timestamp,
                "updated_at": timestamp,
                "published_at": timestamp,
                "version": 4,
                "tags": [tag_id],
            }
        ],
        "tags": [{"id": tag_id, "name": "API", "slug": "api", "description": "Custom tag"}],
        "redirects": [{"slug": "old-native-url", "post_id": post_id}],
        "site": {
            "title": "无情老小儿",
            "description": "Transferred description",
            "posts_per_page": 7,
            "navigation": [{"label": "Home", "url": "/"}],
        },
        "files": [],
    }


def encoded(data):
    return json.dumps(data, ensure_ascii=False).encode("utf-8")


def preview(client, data):
    return client.post(
        "/api/admin/data/preview",
        content=encoded(data),
        headers={"Content-Type": "application/json"},
    )


def apply(client, data, **options):
    content = encoded(data)
    params = {"sha256": hashlib.sha256(content).hexdigest(), **options}
    return client.post(
        "/api/admin/data/import",
        content=content,
        params=params,
        headers={"Content-Type": "application/json"},
    )


def test_import_roundtrip_preserves_source_metadata_and_destination_accounts(admin, monkeypatch):
    monkeypatch.setattr(service, "PROJECT_ROOT", admin.app.state.settings.data_dir.parent)
    data = native_data()
    before_site = admin.get("/api/site").json()
    with connect(admin.app.state.settings) as session:
        before_accounts = [
            (u.username, u.password_hash, u.email) for u in session.scalars(select(UserOrm))
        ]
    checked = preview(admin, data)
    assert checked.status_code == 200
    assert checked.json()["new_posts"] == 1 and checked.json()["new_tags"] == 1
    assert apply(admin, data).status_code == 200
    result = admin.get("/api/admin/posts/" + data["posts"][0]["id"]).json()
    assert result["body"] == data["posts"][0]["body"]
    assert result["version"] == 4 and result["created_at"].startswith("2020-01-02")
    assert result["tags"][0]["slug"] == "api"
    assert admin.get("/api/posts/old-native-url").json()["redirect"] == "native-article"
    assert admin.get("/api/site").json()["description"] == before_site["description"]
    again = apply(admin, data, include_settings=True)
    assert again.status_code == 200 and again.json()["imported_posts"] == 0
    assert again.json()["skipped_posts"] == 1
    assert admin.get("/api/site").json()["description"] == "Transferred description"
    export = admin.get("/api/admin/data/export")
    assert export.status_code == 200
    assert "attachment" in export.headers["content-disposition"]
    payload = export.json()
    assert payload["posts"][0]["body"] == data["posts"][0]["body"]
    assert "users" not in payload and "password_hash" not in export.text
    assert payload["media_root"] == "data/images"
    with connect(admin.app.state.settings) as session:
        assert [
            (u.username, u.password_hash, u.email) for u in session.scalars(select(UserOrm))
        ] == before_accounts


def test_conflict_blocks_all_imported_content(admin):
    data = native_data()
    assert apply(admin, data).status_code == 200
    changed = native_data()
    checked = preview(admin, changed).json()
    assert not checked["can_import"] and checked["conflicts"]
    changed["posts"].append(
        {**changed["posts"][0], "id": uuid.uuid4().hex, "slug": "must-not-be-added"}
    )
    assert apply(admin, changed).status_code == 409
    assert admin.get("/api/admin/posts").json()["total"] == 1
    assert admin.get("/api/posts/must-not-be-added").status_code == 404


def test_skip_conflicts_imports_independent_records_and_preserves_existing_content(admin):
    original = native_data()
    assert apply(admin, original).status_code == 200
    original_post = original["posts"][0]
    original_tag = original["tags"][0]
    data = native_data()
    changed = {**original_post, "title": "Incoming replacement", "tags": []}
    new_tag = {**original_tag, "slug": "new-tag", "id": uuid.uuid4().hex}
    conflicting_tag = {
        **original_tag,
        "id": uuid.uuid4().hex,
        "description": "Incoming replacement",
    }
    new = {
        **data["posts"][0],
        "slug": "safe-new-post",
        "tags": [new_tag["id"]],
    }
    dependent = {
        **new,
        "id": uuid.uuid4().hex,
        "slug": "uses-conflicting-tag",
        "tags": [conflicting_tag["id"]],
    }
    data["tags"] = [conflicting_tag, new_tag]
    data["posts"] = [changed, new, dependent]
    data["redirects"] = [
        {"slug": "old-native-url", "post_id": new["id"]},
        {"slug": "skip-this-redirect", "post_id": changed["id"]},
        {"slug": "new-redirect", "post_id": new["id"]},
    ]

    checked = preview(admin, data).json()
    assert not checked["can_import"] and checked["can_skip_conflicts"]
    assert checked["new_posts"] == 1 and len(checked["conflicts"]) == 5
    assert apply(admin, data).status_code == 409
    imported = apply(admin, data, skip_conflicts=True)
    assert imported.status_code == 200, imported.text
    assert imported.json()["imported_posts"] == 1
    assert imported.json()["imported_tags"] == 1
    assert imported.json()["skipped_conflicts"] == 5
    assert admin.get("/api/posts/native-article").json()["title"] == original_post["title"]
    assert admin.get("/api/posts/old-native-url").json()["redirect"] == "native-article"
    assert admin.get("/api/posts/new-redirect").json()["redirect"] == "safe-new-post"
    assert admin.get("/api/posts/skip-this-redirect").status_code == 404
    assert admin.get("/api/posts/uses-conflicting-tag").status_code == 404
    tags = {tag["slug"]: tag["description"] for tag in admin.get("/api/admin/tags").json()}
    assert tags == {"api": original_tag["description"], "new-tag": original_tag["description"]}

    repeated = apply(admin, data, skip_conflicts=True).json()
    assert repeated["imported_posts"] == repeated["imported_tags"] == 0
    assert repeated["skipped_posts"] == 1


def test_different_tag_ids_with_identical_slug_reuse_target_tag(admin):
    data = native_data()
    assert apply(admin, data).status_code == 200
    newer = native_data()
    newer["posts"][0]["slug"] = "second-native"
    newer["redirects"] = []
    checked = preview(admin, newer).json()
    assert checked["new_tags"] == 0 and checked["can_import"]
    assert apply(admin, newer).status_code == 200
    assert len(admin.get("/api/admin/tags").json()) == 1
    assert admin.get("/api/admin/posts").json()["total"] == 2


def test_relative_files_are_resolved_in_target_storage_and_checked(admin):
    data = native_data()
    content = b"image fixture"
    data["posts"][0]["feature_image"] = "/content/images/file/cover.webp"
    data["files"] = [
        {
            "path": "data/dev/images/file/cover.webp",
            "size": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        }
    ]
    checked = preview(admin, data).json()
    assert checked["missing_files"] == [data["files"][0]["path"]]
    assert checked["can_import"]
    target = admin.app.state.settings.images / "file" / "cover.webp"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"different image")
    checked = preview(admin, data).json()
    assert checked["changed_files"] and not checked["can_import"]
    assert not checked["can_skip_conflicts"]
    assert apply(admin, data, skip_conflicts=True).status_code == 409
    target.write_bytes(content)
    assert preview(admin, data).json()["missing_files"] == []
    assert apply(admin, data).status_code == 200
    assert target.read_bytes() == content
    assert admin.get("/api/posts/native-article").json()["feature_image"] == (
        "/content/images/file/cover.webp"
    )


@pytest.mark.parametrize(
    ("article_format", "body"),
    [
        (
            "markdown",
            "Before ![Diagram][missing] and ![External](https://example.org/chart.png) after.\n\n"
            "```markdown\n![Literal](/content/images/literal.png)\n```\n\n"
            '[missing]: /content/images/diagram.png "Caption"',
        ),
        (
            "html",
            '<p>Before <a href="/content/images/diagram.png">'
            '<img src="/content/images/diagram.png" alt="Diagram"></a> and '
            '<img src="https://example.org/chart.png" alt="External"> after.</p>'
            "<pre>![Literal](/content/images/literal.png)</pre>",
        ),
    ],
)
def test_import_degrades_missing_images_and_ignores_unused_files(admin, article_format, body):
    data = native_data()
    data["posts"][0].update(
        body=body, format=article_format, feature_image="/content/images/cover.png"
    )
    data["site"]["cover"] = "/content/images/home.png"
    images = admin.app.state.settings.images
    unused = images / "unused.png"
    unused.write_bytes(b"keep this local file")
    data["files"] = [
        {"path": f"data/dev/images/{name}", "size": 10, "sha256": "0" * 64}
        for name in ("cover.png", "unused.png", "unused-missing.png")
    ]
    checked = preview(admin, data).json()
    assert checked["can_import"]
    assert checked["missing_files"] == [
        f"data/dev/images/{name}" for name in ("cover.png", "diagram.png", "home.png")
    ]
    assert checked["ignored_files"] == 2 and not checked["changed_files"]
    assert apply(admin, data, include_settings=True).status_code == 200
    saved = admin.get("/api/admin/posts/" + data["posts"][0]["id"]).json()
    assert saved["feature_image"] == ""
    assert saved["body"] == body
    assert '<span class="missing-image">Image unavailable: Diagram</span>' in saved["html"]
    assert 'src="https://example.org/chart.png"' in saved["html"]
    assert "![Literal](/content/images/literal.png)" in saved["html"]
    assert 'href="/content/images/diagram.png"' not in saved["html"]
    assert admin.get("/api/site").json()["cover"] == ""
    assert apply(admin, data).json()["skipped_posts"] == 1
    assert unused.read_bytes() == b"keep this local file"


@pytest.mark.parametrize(
    "path",
    [
        "../secret",
        "/etc/passwd",
        "C:/secret",
        "data/dev/images/../secret.png",
        "data/dev/images\\secret.png",
        "data/dev/images//file.png",
    ],
)
def test_unsafe_paths_are_rejected_without_mutations(admin, path):
    data = native_data()
    data["files"] = [{"path": path, "size": 0, "sha256": "0" * 64}]
    assert preview(admin, data).status_code == 422
    assert admin.get("/api/admin/posts").json()["total"] == 0


def test_invalid_references_duplicates_and_versions_are_rejected(admin):
    for mutation in ("version", "duplicate", "unknown-tag", "unknown-post", "missing-format"):
        data = native_data()
        if mutation == "version":
            data["version"] = 99
        elif mutation == "duplicate":
            data["posts"].append(data["posts"][0])
        elif mutation == "unknown-tag":
            data["posts"][0]["tags"] = [uuid.uuid4().hex]
        elif mutation == "unknown-post":
            data["redirects"][0]["post_id"] = uuid.uuid4().hex
        else:
            del data["format"]
        assert preview(admin, data).status_code == 422


def test_transfer_requires_authentication_csrf_and_matching_preview(client, admin):
    data = native_data()
    content = encoded(data)
    assert (
        client.post(
            "/api/admin/logout", headers={"X-CSRF-Token": admin.headers["X-CSRF-Token"]}
        ).status_code
        == 200
    )
    assert client.get("/api/admin/data/export").status_code == 401
    assert preview(client, data).status_code == 401
    login = client.post(
        "/api/admin/login", json={"username": "writer", "password": "a-safe-test-password"}
    ).json()
    client.headers.pop("X-CSRF-Token", None)
    assert preview(client, data).status_code == 403
    client.headers["X-CSRF-Token"] = login["csrf_token"]
    response = client.post(
        "/api/admin/data/import?sha256=" + "0" * 64,
        content=content,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 409
    assert client.get("/api/admin/posts").json()["total"] == 0


def test_import_rerenders_html_instead_of_trusting_executable_markup(admin):
    data = native_data()
    data["posts"][0]["format"] = "html"
    data["posts"][0]["body"] = "<h1>Safe</h1><script>alert(1)</script><img src=x onerror=alert(1)>"
    assert apply(admin, data).status_code == 200
    rendered = admin.get("/api/posts/native-article").json()["html"]
    assert "<script" not in rendered and "onerror" not in rendered


def test_export_contains_relative_paths_and_integrity_metadata(admin, monkeypatch):
    settings = admin.app.state.settings
    monkeypatch.setattr(service, "PROJECT_ROOT", settings.data_dir.parent)
    image = settings.images / "example.png"
    image.write_bytes(b"content")
    (settings.images / "unused.png").write_bytes(b"unused")
    source = native_data()
    source["posts"][0]["body"] += "\n\n![Example](/content/images/example.png)"
    assert apply(admin, source).status_code == 200
    data = admin.get("/api/admin/data/export").json()
    assert data["files"] == [
        {
            "path": "data/images/example.png",
            "size": 7,
            "sha256": hashlib.sha256(b"content").hexdigest(),
        }
    ]


def test_import_is_atomic_when_rendering_fails(admin, monkeypatch):
    data = native_data()

    def failure(*args, **kwargs):
        raise RuntimeError("simulated renderer failure")

    monkeypatch.setattr(service, "render", failure)
    with pytest.raises(RuntimeError):
        apply(admin, data)
    assert admin.get("/api/admin/posts").json()["total"] == 0
    assert admin.get("/api/admin/tags").json() == []
