import json

from bs4 import BeautifulSoup


def test_home_preloads_only_current_route_static_imports(client):
    frontend = client.app.state.settings.frontend_dir
    directory = frontend / ".vite"
    directory.mkdir()
    manifest = {
        "src/views/HomeView.vue": {
            "file": "assets/home-123.js",
            "imports": ["shared"],
            "dynamicImports": ["search"],
        },
        "shared": {"file": "assets/shared-123.js", "imports": ["src/views/HomeView.vue"]},
        "search": {"file": "assets/search-123.js"},
        "src/views/AdminPosts.vue": {"file": "assets/admin-123.js"},
    }
    (directory / "manifest.json").write_text(json.dumps(manifest))
    for path in ("/", "/page/1/", "/tag/missing/"):
        document = BeautifulSoup(client.get(path).text, "html.parser")
        links = [node["href"] for node in document.select('link[rel="modulepreload"]')]
        assert links == ["/assets/home-123.js", "/assets/shared-123.js"]
        assert all(
            node.has_attr("crossorigin") for node in document.select('link[rel="modulepreload"]')
        )
    for path in ("/workspace/login", "/missing/", "/tags/", "/archive/"):
        document = BeautifulSoup(client.get(path).text, "html.parser")
        assert not document.select('link[rel="modulepreload"]')


def test_missing_or_invalid_manifest_keeps_the_page_available(client):
    assert client.get("/").status_code == 200
    directory = client.app.state.settings.frontend_dir / ".vite"
    directory.mkdir()
    for content in ("not json", "[]", '{"src/views/HomeView.vue": null}'):
        (directory / "manifest.json").write_text(content)
        assert client.get("/").status_code == 200
