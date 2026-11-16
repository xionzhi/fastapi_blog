"""ORM content transfer with validation, additive conflict handling and atomic writes."""

import hashlib
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.database import begin_snapshot, begin_write, read_settings
from app.common.exceptions import ApplicationError, ConflictError
from app.common.time import utc_now
from app.core.config import PROJECT_ROOT, Settings
from app.modules.post.content import render
from app.modules.post.models import PostOrm, PostRedirectOrm, PostTagOrm
from app.modules.site.models import SiteInput
from app.modules.site.service import update as update_site
from app.modules.tag.models import TagOrm
from app.modules.transfer.models import (
    MAX_JSON_BYTES,
    ImportPreview,
    ImportResult,
    NativeExport,
    NativeFile,
    NativePost,
    NativeRedirect,
    NativeTag,
)

POST_FIELDS = tuple(name for name in NativePost.model_fields if name not in {"id", "tags"})


def digest_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def export_content(*, session: Session, settings: Settings) -> NativeExport:
    # Authentication may already have issued a read in this request's session.
    session.rollback()
    begin_snapshot(session)
    try:
        media_root = settings.images.relative_to(PROJECT_ROOT).as_posix()
    except ValueError as error:
        raise ApplicationError(
            "Image storage must be inside the project root for relative exports",
            code="transfer.media_root",
        ) from error
    posts = [
        NativePost(
            id=p.id,
            **{key: getattr(p, key) for key in POST_FIELDS},
            tags=[link.tag_id for link in p.tag_links],
        )
        for p in session.scalars(select(PostOrm).order_by(PostOrm.id))
    ]
    tags = [
        NativeTag(id=t.id, name=t.name, slug=t.slug, description=t.description)
        for t in session.scalars(select(TagOrm).order_by(TagOrm.id))
    ]
    redirects = [
        NativeRedirect(slug=r.slug, post_id=r.post_id)
        for r in session.scalars(select(PostRedirectOrm).order_by(PostRedirectOrm.slug))
    ]
    site = SiteInput.model_validate(read_settings(session))
    session.commit()
    files = []
    for path in sorted(settings.images.rglob("*")):
        if not path.is_file():
            continue
        if not path.resolve().is_relative_to(settings.images):
            raise ApplicationError(
                "Image storage contains an unsafe link", code="transfer.media_path"
            )
        files.append(
            NativeFile(
                path=media_root + "/" + path.relative_to(settings.images).as_posix(),
                size=path.stat().st_size,
                sha256=digest_file(path),
            )
        )
    return NativeExport(
        format="xionzhi-blog",
        version=1,
        exported_at=utc_now(),
        media_root=media_root,
        posts=posts,
        tags=tags,
        redirects=redirects,
        site=site,
        files=files,
    )


def parse_content(content: bytes) -> NativeExport:
    if len(content) > MAX_JSON_BYTES:
        raise ApplicationError(
            "JSON exports must not exceed 16 MB", code="transfer.too_large", status_code=413
        )
    try:
        return NativeExport.model_validate_json(content)
    except (ValidationError, ValueError, RecursionError) as error:
        raise ApplicationError(
            "Invalid native JSON export. Check the format version, records and relative file paths.",
            code="transfer.invalid_export",
            status_code=422,
        ) from error


def _tag_mapping(session: Session, data: NativeExport, preview: ImportPreview) -> dict[str, str]:
    existing = list(session.scalars(select(TagOrm)))
    by_id = {tag.id: tag for tag in existing}
    by_slug = {tag.slug: tag for tag in existing}
    mapping = {}
    for tag in data.tags:
        record = by_id.get(tag.id) or by_slug.get(tag.slug)
        if record:
            if (record.name, record.slug, record.description) != (
                tag.name,
                tag.slug,
                tag.description,
            ):
                preview.conflicts.append(f"Tag conflict: {tag.slug}")
            mapping[tag.id] = record.id
        else:
            mapping[tag.id] = tag.id
            preview.new_tags += 1
    return mapping


def inspect_content(
    *, session: Session, settings: Settings, data: NativeExport, sha256: str
) -> tuple[ImportPreview, dict[str, str]]:
    preview = ImportPreview(
        sha256=sha256,
        posts=sum(p.type == "post" for p in data.posts),
        pages=sum(p.type == "page" for p in data.posts),
        tags=len(data.tags),
        files=len(data.files),
    )
    tags = _tag_mapping(session, data, preview)
    records = list(session.scalars(select(PostOrm)))
    by_id = {p.id: p for p in records}
    by_slug = {p.slug: p for p in records}
    redirects = {r.slug: r.post_id for r in session.scalars(select(PostRedirectOrm))}
    for post in data.posts:
        record = by_id.get(post.id) or by_slug.get(post.slug)
        if record:
            identical = record.id == post.id and all(
                getattr(record, key) == getattr(post, key) for key in POST_FIELDS
            )
            identical = identical and [link.tag_id for link in record.tag_links] == [
                tags[tag_id] for tag_id in post.tags
            ]
            if identical:
                preview.skipped_posts += 1
            else:
                preview.conflicts.append(f"Post conflict: {post.slug}")
        elif post.slug in redirects:
            preview.conflicts.append(f"Reserved post URL: {post.slug}")
        else:
            preview.new_posts += 1
    for redirect in data.redirects:
        if redirect.slug in by_slug or (
            redirect.slug in redirects and redirects[redirect.slug] != redirect.post_id
        ):
            preview.conflicts.append(f"Redirect conflict: {redirect.slug}")
    for file in data.files:
        suffix = file.path.removeprefix(data.media_root + "/")
        target = (settings.images / suffix).resolve()
        if not target.is_relative_to(settings.images):
            raise ApplicationError("Unsafe image path", code="transfer.media_path", status_code=422)
        if not target.is_file():
            preview.missing_files.append(file.path)
        elif target.stat().st_size != file.size or digest_file(target) != file.sha256:
            preview.changed_files.append(file.path)
    preview.can_import = not preview.conflicts and not preview.changed_files
    return preview, tags


def import_content(
    *,
    session: Session,
    settings: Settings,
    data: NativeExport,
    sha256: str,
    include_settings: bool,
    allow_missing_files: bool,
) -> ImportResult:
    session.rollback()
    begin_write(session)
    preview, mapping = inspect_content(session=session, settings=settings, data=data, sha256=sha256)
    if not preview.can_import:
        raise ConflictError(
            "Content conflicts or changed image files prevent importing. Review the preview again.",
            code="transfer.conflict",
        )
    if preview.missing_files and not allow_missing_files:
        raise ConflictError(
            "Upload the missing image files or explicitly allow missing files",
            code="transfer.missing_files",
        )
    existing_tags = set(session.scalars(select(TagOrm.id)))
    session.add_all(
        TagOrm(**tag.model_dump()) for tag in data.tags if mapping[tag.id] not in existing_tags
    )
    session.flush()
    existing_posts = set(session.scalars(select(PostOrm.id)))
    for post in data.posts:
        if post.id in existing_posts:
            continue
        html, plain_text = render(post.body, post.format)
        session.add(PostOrm(**post.model_dump(exclude={"tags"}), html=html, plain_text=plain_text))
        session.flush()
        session.add_all(
            PostTagOrm(post_id=post.id, tag_id=mapping[tag_id], position=index)
            for index, tag_id in enumerate(post.tags)
        )
    session.flush()
    existing_redirects = set(session.scalars(select(PostRedirectOrm.slug)))
    session.add_all(
        PostRedirectOrm(**r.model_dump())
        for r in data.redirects
        if r.slug not in existing_redirects
    )
    if include_settings:
        update_site(db_session=session, data=data.site)
    session.flush()
    return ImportResult(
        imported_posts=preview.new_posts,
        imported_tags=preview.new_tags,
        skipped_posts=preview.skipped_posts,
        settings_imported=include_settings,
    )
