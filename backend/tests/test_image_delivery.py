import io
import json
from pathlib import Path

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from PIL import Image

from app.application import build_application
from app.core.config import Settings
from app.modules.media.variants import describe, variant


def write_image(path: Path, size: tuple[int, int] = (1600, 1000)) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.effect_noise(size, 40).convert("RGB").save(
        path, format="WEBP" if path.suffix == ".webp" else "PNG"
    )
    return path.read_bytes()


def test_local_derivatives_are_small_versioned_and_preserve_originals(tmp_path):
    settings = Settings(data_dir=tmp_path)
    source = settings.images / "file/avatar.png"
    original = write_image(source)
    info = describe(settings, "/content/images/file/avatar.png", "avatar")
    assert (info.width, info.height) == (1600, 1000)
    assert "96w" in info.srcset and info.sizes == "24px"
    target, version = variant(source, tmp_path / "image-cache", 48)
    assert len(target.read_bytes()) < len(original)
    with Image.open(target) as output:
        assert output.size == (48, 30) and output.format == "WEBP"
    assert source.read_bytes() == original
    assert variant(source, tmp_path / "image-cache", 48) == (target, version)
    source.write_bytes(original + b"updated")
    assert describe(settings, "/content/images/file/avatar.png", "avatar").src != info.src


def test_image_requests_handle_cache_ranges_and_bounded_widths(tmp_path):
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "index.html").write_text(
        "<html><head><title>Blog</title></head><body><div id='app'></div></body></html>"
    )
    settings = Settings(
        environment="production",
        data_dir=tmp_path / "data",
        frontend_dir=frontend,
        site_url="https://blog.example.test",
        allowed_origins=["https://blog.example.test"],
        secure_cookies=True,
    )
    original = write_image(settings.images / "avatar.png", (300, 300))
    info = describe(settings, "/content/images/avatar.png", "avatar")
    with TestClient(build_application(settings=settings), base_url=settings.site_url) as client:
        response = client.get(info.src)
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/webp"
        assert response.headers["cache-control"] == "public, max-age=31536000, immutable"
        with Image.open(io.BytesIO(response.content)) as image:
            assert image.size == (48, 48)
        assert (
            client.get(info.src, headers={"If-None-Match": response.headers["etag"]}).status_code
            == 304
        )
        partial = client.get(info.src, headers={"Range": "bytes=0-5"})
        assert partial.status_code == 206 and partial.content == response.content[:6]
        assert client.head(info.src).content == b""
        assert client.get("/content/images/avatar.png").content == original
        assert (
            client.get("/content/images/avatar.png")
            .headers["cache-control"]
            .startswith("public, max-age=86400")
        )
        assert client.get("/content/images/avatar.png?width=99999999").status_code == 400
        assert client.get("/content/images/missing.png?width=48").status_code == 404


def test_cover_seed_preload_and_delivery_preserve_the_original_webp(admin):
    settings = admin.app.state.settings
    original = write_image(settings.images / "cover.webp")
    write_image(settings.images / "logo.png", (300, 100))
    site = admin.get("/api/site").json()
    site.update(cover="/content/images/cover.webp", logo="/content/images/logo.png", description="")
    site = admin.put("/api/admin/site", json=site).json()
    document = BeautifulSoup(admin.get("/").text, "html.parser")
    seed = json.loads(document.select_one("#initial-document").string)
    cover = document.select_one(".hero-cover")
    preload = document.select_one('link[rel="preload"][as="image"]')
    assert cover["src"] == preload["href"] == site["cover"]
    assert seed["site"]["images"]["cover"]["src"] == site["cover"]
    assert "srcset" not in cover and "imagesrcset" not in preload
    assert not site["images"]["cover"]["srcset"]
    assert (cover["width"], cover["height"]) == ("1600", "1000")
    delivered = admin.get(cover["src"])
    assert delivered.content == original
    assert delivered.headers["content-type"] == "image/webp"
    assert (settings.images / "cover.webp").read_bytes() == original
    logo = document.select_one(".blog-logo img")
    assert (logo["width"], logo["height"]) == ("300", "100")
    assert document.select_one('meta[name="description"]')["content"].strip()
    assert site["description"] == ""  # Fallback metadata does not rewrite the site's settings.


def test_external_unsafe_missing_and_animated_images_use_originals(tmp_path):
    settings = Settings(data_dir=tmp_path)
    for url in (
        "https://other.example/cover.png",
        "/content/images/../../secret.png",
        "/content/images/missing.png",
        "/content/images/%00.png",
    ):
        assert describe(settings, url, "cover") is None
    source = settings.images / "animated.gif"
    source.parent.mkdir(parents=True)
    Image.new("RGB", (20, 20), "red").save(
        source,
        save_all=True,
        append_images=[Image.new("RGB", (20, 20), "blue")],
        duration=100,
        loop=0,
    )
    assert describe(settings, "/content/images/animated.gif", "cover") is None
    assert variant(source, tmp_path / "image-cache", 48) is None
    assert variant(tmp_path / "missing.png", tmp_path / "image-cache", 48) is None
