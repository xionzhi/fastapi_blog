import io
import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import select

from app.common.database import connect
from app.modules.media import service
from app.modules.media.models import ImageMove
from app.modules.post.models import PostOrm


def upload(admin):
    stream = io.BytesIO()
    Image.new("RGB", (500, 300), "green").save(stream, format="PNG")
    response = admin.post(
        "/api/admin/images", files={"file": ("test.png", stream.getvalue(), "image/png")}
    )
    assert response.status_code == 201
    url = response.json()["url"]
    return next(
        item for item in admin.get("/api/admin/images").json()["items"] if item["url"] == url
    )


def selection(image):
    return {"path": image["path"], "revision": image["revision"]}


def test_upload_rejects_linked_parent_without_writing_files(admin, monkeypatch):
    root = admin.app.state.settings.images
    linked_parent = root / str(datetime.now().year)
    original_check = Path.is_symlink
    monkeypatch.setattr(
        Path, "is_symlink", lambda path: path == linked_parent or original_check(path)
    )
    stream = io.BytesIO()
    Image.new("RGB", (10, 10)).save(stream, format="PNG")
    response = admin.post("/api/admin/images", files={"file": ("image.png", stream.getvalue())})
    assert response.status_code == 400 and response.json()["error_code"] == "media.unsafe_path"
    assert not list(root.rglob("*.png"))


def test_incomplete_upload_is_removed_without_overwriting_existing_files(admin, monkeypatch):
    root = admin.app.state.settings.images
    original_open = Path.open

    class FailedUpload:
        def __init__(self, stream):
            self.stream = stream

        def write(self, content):
            self.stream.write(content[:8])
            raise OSError("out of space")

    @contextmanager
    def broken_open(path, mode="r", *args, **kwargs):
        with original_open(path, mode, *args, **kwargs) as stream:
            yield FailedUpload(stream) if mode == "xb" else stream

    stream = io.BytesIO()
    Image.new("RGB", (10, 10)).save(stream, format="PNG")
    monkeypatch.setattr(Path, "open", broken_open)
    response = admin.post("/api/admin/images", files={"file": ("image.png", stream.getvalue())})
    assert response.status_code == 409 and response.json()["error_code"] == "media.upload_failed"
    assert not list(root.rglob("*.png"))


def test_library_auth_csrf_and_private_thumbnails(client, admin):
    image = upload(admin)
    thumbnail = admin.get(image["thumbnail"])
    assert thumbnail.status_code == 200
    assert thumbnail.headers["cache-control"] == "no-store"
    with Image.open(io.BytesIO(thumbnail.content)) as preview:
        assert preview.size == (480, 288)
    client.headers.pop("X-CSRF-Token")
    assert client.request("DELETE", "/api/admin/images", json=selection(image)).status_code == 403
    client.cookies.clear()
    assert client.get("/api/admin/images").status_code == 401
    assert client.get(image["thumbnail"]).status_code == 401
    assert (
        client.put(
            "/api/admin/images", json={**selection(image), "new_path": "renamed.png"}
        ).status_code
        == 401
    )


def test_image_mutations_have_a_small_request_limit(admin):
    assert (
        admin.put(
            "/api/admin/images", content=b" " * 9000, headers={"Content-Type": "application/json"}
        ).status_code
        == 413
    )


def test_existing_files_search_pagination_and_animated_thumbnail(admin):
    root = admin.app.state.settings.images
    (root / "imported").mkdir()
    Image.new("RGB", (30, 100), "blue").save(root / "imported" / "旧图片.png")
    Image.new("RGB", (100, 30), "red").save(
        root / "animated.gif",
        save_all=True,
        append_images=[Image.new("RGB", (100, 30), "blue")],
        duration=100,
        loop=0,
    )
    (root / ".private.png").write_bytes(b"private")
    page = admin.get("/api/admin/images?limit=1").json()
    assert page["total"] == 2 and page["pages"] == 2 and len(page["items"]) == 1
    matched = admin.get("/api/admin/images", params={"q": "IMPORTED"}).json()
    assert matched["total"] == 1
    assert "%E6%97%A7" in matched["items"][0]["url"]
    gif = admin.get("/api/admin/images", params={"q": ".gif"}).json()["items"][0]
    preview = admin.get(gif["thumbnail"])
    assert preview.status_code == 200 and preview.headers["content-type"] == "image/webp"
    assert len(admin.get("/api/admin/images?page=99").json()["items"]) == 0


def test_move_updates_saved_markdown_html_and_site_without_touching_external_urls(admin, post_data):
    image = upload(admin)
    url = image["url"]
    body = f'![one]({url}?width=96#here)\n\n<img src="http://testserver{url}" alt="two">\n\n![external](https://other.test{url})'
    post = admin.post("/api/admin/posts", json={**post_data, "body": body}).json()
    html_post = admin.post(
        "/api/admin/posts",
        json={
            **post_data,
            "slug": "html-post",
            "format": "html",
            "body": f'<img src="{url}">',
            "status": "draft",
        },
    ).json()
    site = admin.get("/api/admin/site").json()
    site.update(cover=url, navigation=[{"label": "Image", "url": url}])
    assert admin.put("/api/admin/site", json=site).status_code == 200
    image = admin.get("/api/admin/images").json()["items"][0]
    assert len(image["usages"]) == 4
    response = admin.put(
        "/api/admin/images", json={**selection(image), "new_path": "library/新图片 1.png"}
    )
    assert response.status_code == 200, response.text
    moved = response.json()["image"]
    assert not response.json()["source_retained"]
    assert admin.get(moved["url"]).status_code == 200
    assert admin.get(url).status_code == 404
    updated = admin.get(f"/api/admin/posts/{post['id']}").json()
    assert moved["url"] + "?width=96#here" in updated["body"]
    assert f"https://other.test{url}" in updated["body"]
    assert updated["version"] == post["version"] + 1
    assert moved["url"] in updated["html"]
    assert moved["url"] in admin.get(f"/api/admin/posts/{html_post['id']}").json()["body"]
    assert admin.get("/api/site").json()["cover"] == moved["url"]
    assert admin.get("/api/site").json()["navigation"][0]["url"] == moved["url"]
    stale = admin.put(
        f"/api/admin/posts/{post['id']}", json={**post_data, "version": post["version"]}
    )
    assert stale.status_code == 409
    blocked = admin.request("DELETE", "/api/admin/images", json=selection(moved))
    assert blocked.status_code == 409 and blocked.json()["error_code"] == "media.in_use"


def test_delete_rechecks_usage_and_stale_file_revision(admin, post_data):
    image = upload(admin)
    # A reference added after listing must still block deletion.
    post = admin.post("/api/admin/posts", json={**post_data, "feature_image": image["url"]}).json()
    assert admin.request("DELETE", "/api/admin/images", json=selection(image)).status_code == 409
    assert admin.delete(f"/api/admin/posts/{post['id']}").status_code == 204
    path = admin.app.state.settings.images / image["path"]
    path.write_bytes(path.read_bytes() + b"changed")
    assert admin.request("DELETE", "/api/admin/images", json=selection(image)).status_code == 409
    fresh = admin.get("/api/admin/images").json()["items"][0]
    assert admin.request("DELETE", "/api/admin/images", json=selection(fresh)).status_code == 204
    assert not path.exists()


@pytest.mark.parametrize(
    "target",
    [
        "../outside.png",
        "/absolute.png",
        "a/../../outside.png",
        "a\\outside.png",
        "a/.hidden.png",
        "a/%2e%2e/outside.png",
        "a//b.png",
        "a/not-an-image.svg",
        "a/photo.jpg",
        "a/photo.png?x=1",
        "a/photo.png#x",
        "a/photo.png\x00",
    ],
)
def test_move_rejects_unsafe_paths_and_format_changes(admin, target):
    image = upload(admin)
    result = admin.put("/api/admin/images", json={**selection(image), "new_path": target})
    assert result.status_code == 422
    assert admin.get(image["url"]).status_code == 200


def test_move_never_overwrites_existing_file(admin):
    first, second = upload(admin), upload(admin)
    response = admin.put("/api/admin/images", json={**selection(first), "new_path": second["path"]})
    assert response.status_code == 409 and response.json()["error_code"] == "media.path_taken"
    assert admin.get(first["url"]).status_code == admin.get(second["url"]).status_code == 200


def test_move_database_failure_keeps_original_and_rolls_back_references(
    admin, post_data, monkeypatch
):
    image = upload(admin)
    admin.post("/api/admin/posts", json={**post_data, "feature_image": image["url"]})
    settings = admin.app.state.settings
    with connect(settings) as session:

        def failed_commit():
            raise RuntimeError("database unavailable")

        monkeypatch.setattr(session, "commit", failed_commit)
        with pytest.raises(RuntimeError):
            service.move_image(
                session=session,
                settings=settings,
                data=ImageMove(**selection(image), new_path="moved.png"),
            )
        monkeypatch.undo()
    assert (settings.images / image["path"]).is_file()
    assert not (settings.images / "moved.png").exists()
    with connect(settings) as session:
        assert session.scalar(select(PostOrm.feature_image)) == image["url"]


def test_symlink_files_and_folders_are_not_managed(admin, tmp_path):
    root = admin.app.state.settings.images
    outside = tmp_path / "outside.png"
    Image.new("RGB", (10, 10)).save(outside)
    try:
        (root / "linked.png").symlink_to(outside)
        (root / "linked-folder").symlink_to(tmp_path, target_is_directory=True)
    except OSError:
        pytest.skip("Creating symlinks requires privileges on this platform")
    assert admin.get("/api/admin/images").json()["total"] == 0
    assert (
        admin.get("/api/admin/images/thumbnail", params={"path": "linked.png"}).status_code == 400
    )
    image = upload(admin)
    assert (
        admin.put(
            "/api/admin/images", json={**selection(image), "new_path": "linked-folder/image.png"}
        ).status_code
        == 400
    )
    assert outside.is_file()


@pytest.mark.parametrize("middle", ["folder/../", "folder/%2e%2e/", "./", "/"])
def test_normalized_image_references_block_deletion_and_survive_moves(admin, post_data, middle):
    image = upload(admin)
    url = image["url"].replace("/content/images/", f"/content/images/{middle}")
    post = admin.post("/api/admin/posts", json={**post_data, "body": f"![Image]({url})"}).json()
    assert admin.request("DELETE", "/api/admin/images", json=selection(image)).status_code == 409
    moved = admin.put("/api/admin/images", json={**selection(image), "new_path": "moved.png"})
    assert moved.status_code == 200, moved.text
    updated = admin.get(f"/api/admin/posts/{post['id']}").json()
    assert moved.json()["image"]["url"] in updated["body"]
    assert moved.json()["image"]["url"] in updated["html"]


def test_parenthesized_image_names_are_rewritten_without_changing_markdown(admin, post_data):
    root = admin.app.state.settings.images
    Image.new("RGB", (20, 20)).save(root / "photo(1).png")
    post = admin.post(
        "/api/admin/posts",
        json={**post_data, "body": "Before\n\n![Photo](/content/images/photo(1).png)\n\nAfter"},
    ).json()
    image = admin.get("/api/admin/images").json()["items"][0]
    moved = admin.put("/api/admin/images", json={**selection(image), "new_path": "new.png"})
    assert moved.status_code == 200, moved.text
    updated = admin.get(f"/api/admin/posts/{post['id']}").json()
    assert updated["body"] == "Before\n\n![Photo](/content/images/new.png)\n\nAfter"


def test_unrewritable_markdown_aborts_move_without_breaking_original(admin, post_data):
    root = admin.app.state.settings.images
    Image.new("RGB", (20, 20)).save(root / "photo(1).png")
    body = r"![Photo](/content/images/photo\(1\).png)"
    post = admin.post("/api/admin/posts", json={**post_data, "body": body}).json()
    image = admin.get("/api/admin/images").json()["items"][0]
    assert image["usages"]
    result = admin.put("/api/admin/images", json={**selection(image), "new_path": "new.png"})
    assert (
        result.status_code == 409 and result.json()["error_code"] == "media.references_unsupported"
    )
    assert (root / "photo(1).png").is_file() and not (root / "new.png").exists()
    assert admin.get(f"/api/admin/posts/{post['id']}").json()["body"] == body


def test_case_variations_cannot_bypass_usage_checks(admin, post_data):
    image = upload(admin)
    url = image["url"].upper() if os.name == "nt" else image["url"]
    # Keep the routing prefix intact; only the file/directory names differ in case.
    url = "/content/images/" + url[len("/content/images/") :]
    admin.post("/api/admin/posts", json={**post_data, "feature_image": url})
    response = admin.request("DELETE", "/api/admin/images", json=selection(image))
    assert response.status_code == 409
    forged = {**selection(image), "path": image["path"].upper()}
    assert admin.request("DELETE", "/api/admin/images", json=forged).status_code in {404, 409}
    assert (admin.app.state.settings.images / image["path"]).is_file()


def test_failed_rollback_cleanup_preserves_original_error_and_image(admin, monkeypatch):
    image = upload(admin)
    settings = admin.app.state.settings
    target = settings.images / "moved.png"
    original_unlink = Path.unlink

    def blocked_unlink(path, *args, **kwargs):
        if path == target:
            raise PermissionError("locked file")
        return original_unlink(path, *args, **kwargs)

    with connect(settings) as session:

        def failed_commit():
            raise RuntimeError("commit failed")

        with monkeypatch.context() as patch:
            patch.setattr(session, "commit", failed_commit)
            patch.setattr(Path, "unlink", blocked_unlink)
            with pytest.raises(RuntimeError, match="commit failed"):
                service.move_image(
                    session=session,
                    settings=settings,
                    data=ImageMove(**selection(image), new_path="moved.png"),
                )
    assert (settings.images / image["path"]).is_file()
