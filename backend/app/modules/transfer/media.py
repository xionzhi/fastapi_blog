"""Resolve the local images used by a native transfer."""

import hashlib
from collections.abc import Iterator
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from app.common.exceptions import ApplicationError
from app.core.config import Settings
from app.modules.media.references import local_path, reference_key
from app.modules.site.models import SiteInput
from app.modules.transfer.models import NativeExport, NativeFile, relative_path

SITE_IMAGE_FIELDS = ("cover", "logo", "author_image")
IMAGE_ATTRIBUTES = {"img": "src", "video": "poster", "a": "href"}


def image_references(document: BeautifulSoup) -> Iterator[tuple[Tag, str, str]]:
    for node in document.select("img[src], video[poster], a[href]"):
        attribute = IMAGE_ATTRIBUTES[node.name]
        url = node.get(attribute)
        if isinstance(url, str) and url:
            yield node, attribute, url


def image_target(settings: Settings, relative: str) -> Path | None:
    try:
        relative_path(relative)
    except ValueError:
        return None
    target = (settings.images / relative).resolve()
    if not target.is_relative_to(settings.images):
        raise ApplicationError("Unsafe image path", code="transfer.media_path", status_code=422)
    return target


def digest_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def export_files(settings: Settings, media_root: str, urls: Iterator[str]) -> list[NativeFile]:
    paths = {
        path
        for url in urls
        if (path := local_path(url, settings, normalize_case=False)) is not None
    }
    files: dict[str, NativeFile] = {}
    for relative in sorted(paths):
        key = reference_key(relative)
        if key in files:
            continue
        target = image_target(settings, relative)
        if target is not None and target.is_file():
            path = f"{media_root}/{relative}"
            try:
                files[key] = NativeFile(
                    path=path, size=target.stat().st_size, sha256=digest_file(target)
                )
            except FileNotFoundError:
                continue
    return list(files.values())


class ImportImages:
    """Check each referenced local image once, ignoring unrelated manifest entries."""

    def __init__(self, settings: Settings, data: NativeExport) -> None:
        self.settings = settings
        self.media_root = data.media_root
        self.manifest = {
            reference_key(file.path.removeprefix(f"{data.media_root}/")): file
            for file in data.files
        }
        self.checked: dict[str, bool] = {}
        self.missing_files: list[str] = []
        self.changed_files: list[str] = []

    @property
    def ignored_count(self) -> int:
        return len(self.manifest.keys() - self.checked.keys())

    def is_missing(self, url: str) -> bool:
        relative = local_path(url, self.settings, normalize_case=False)
        if relative is None:
            return False
        key = reference_key(relative)
        if key in self.checked:
            return self.checked[key]
        file = self.manifest.get(key)
        path = file.path if file else f"{self.media_root}/{relative}"
        target = image_target(self.settings, path.removeprefix(f"{self.media_root}/"))
        missing = target is None or not target.is_file()
        if target is not None and file is not None and not missing:
            try:
                if target.stat().st_size != file.size or digest_file(target) != file.sha256:
                    self.changed_files.append(path)
            except FileNotFoundError:
                missing = True
        if missing:
            self.missing_files.append(path)
        self.checked[key] = missing
        return missing

    def site_images(self, site: SiteInput) -> SiteInput:
        for item in site.navigation:
            self.is_missing(item.url)
        return site.model_copy(
            update={
                field: "" for field in SITE_IMAGE_FIELDS if self.is_missing(getattr(site, field))
            }
        )

    def body_images(self, markup: str) -> str:
        document = BeautifulSoup(markup, "html.parser")
        changed = False
        for node, attribute, url in image_references(document):
            if not self.is_missing(url):
                continue
            changed = True
            if node.name != "img":
                del node[attribute]
                continue
            replacement = document.new_tag("span", attrs={"class": "missing-image"})
            alt = str(node.get("alt", "")).strip()
            replacement.string = f"Image unavailable: {alt}" if alt else "Image unavailable"
            node.replace_with(replacement)
        return str(document) if changed else markup
