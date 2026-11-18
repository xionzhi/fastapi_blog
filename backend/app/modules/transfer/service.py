"""ORM content transfer with validation, additive conflict handling and atomic writes."""

from collections.abc import Iterator
from dataclasses import dataclass

from bs4 import BeautifulSoup
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
from app.modules.transfer.media import (
    SITE_IMAGE_FIELDS,
    ImportImages,
    export_files,
    image_references,
)
from app.modules.transfer.models import (
    MAX_JSON_BYTES,
    ImportPreview,
    ImportResult,
    NativeExport,
    NativePost,
    NativeRedirect,
    NativeTag,
)

POST_FIELDS = tuple(name for name in NativePost.model_fields if name not in {"id", "tags"})


@dataclass(frozen=True)
class PreparedPost:
    source: NativePost
    html: str
    plain_text: str


@dataclass(frozen=True)
class ImportPlan:
    preview: ImportPreview
    tag_ids: dict[str, str]
    new_tags: list[NativeTag]
    posts: list[PreparedPost]
    redirects: list[NativeRedirect]
    site: SiteInput


def _image_urls(posts: list[NativePost], site: SiteInput) -> Iterator[str]:
    for post in posts:
        yield post.feature_image
        markup, _ = render(post.body, post.format)
        document = BeautifulSoup(markup, "html.parser")
        for _, _, url in image_references(document):
            yield url
    for field in SITE_IMAGE_FIELDS:
        yield getattr(site, field)
    for item in site.navigation:
        yield item.url


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
    return NativeExport(
        format="xionzhi-blog",
        version=1,
        exported_at=utc_now(),
        media_root=media_root,
        posts=posts,
        tags=tags,
        redirects=redirects,
        site=site,
        files=export_files(settings, media_root, _image_urls(posts, site)),
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


def _plan_tags(
    session: Session, data: NativeExport, preview: ImportPreview
) -> tuple[dict[str, str], list[NativeTag]]:
    existing = list(session.scalars(select(TagOrm)))
    by_id = {tag.id: tag for tag in existing}
    by_slug = {tag.slug: tag for tag in existing}
    mapping = {}
    new_tags = []
    for tag in data.tags:
        record = by_id.get(tag.id) or by_slug.get(tag.slug)
        if record:
            if (record.name, record.slug, record.description) != (
                tag.name,
                tag.slug,
                tag.description,
            ):
                preview.conflicts.append(f"Tag conflict: {tag.slug}")
                continue
            mapping[tag.id] = record.id
        else:
            mapping[tag.id] = tag.id
            new_tags.append(tag)
    return mapping, new_tags


def prepare_import(
    *, session: Session, settings: Settings, data: NativeExport, sha256: str
) -> ImportPlan:
    preview = ImportPreview(
        sha256=sha256,
        posts=sum(p.type == "post" for p in data.posts),
        pages=sum(p.type == "page" for p in data.posts),
        tags=len(data.tags),
        files=0,
    )
    tags, new_tags = _plan_tags(session, data, preview)
    images = ImportImages(settings, data)
    site = images.site_images(data.site)
    posts = []
    included_post_ids: set[str] = set()
    new_redirects = []
    records = list(session.scalars(select(PostOrm)))
    by_id = {p.id: p for p in records}
    by_slug = {p.slug: p for p in records}
    redirects = {r.slug: r.post_id for r in session.scalars(select(PostRedirectOrm))}
    for post in data.posts:
        if any(tag_id not in tags for tag_id in post.tags):
            preview.conflicts.append(f"Post uses a conflicting tag: {post.slug}")
            continue
        record = by_id.get(post.id) or by_slug.get(post.slug)
        if record and (
            record.id != post.id
            or any(
                getattr(record, key) != getattr(post, key)
                for key in POST_FIELDS
                if key != "feature_image"
            )
            or [link.tag_id for link in record.tag_links] != [tags[tag_id] for tag_id in post.tags]
        ):
            preview.conflicts.append(f"Post conflict: {post.slug}")
            continue
        if not record and post.slug in redirects:
            preview.conflicts.append(f"Reserved post URL: {post.slug}")
            continue
        cover = "" if images.is_missing(post.feature_image) else post.feature_image
        if record and record.feature_image not in {post.feature_image, cover}:
            preview.conflicts.append(f"Post conflict: {post.slug}")
            continue
        markup, plain_text = render(post.body, post.format)
        prepared_html = images.body_images(markup)
        included_post_ids.add(post.id)
        if record:
            preview.skipped_posts += 1
        else:
            posts.append(
                PreparedPost(
                    post.model_copy(update={"feature_image": cover}), prepared_html, plain_text
                )
            )
    for redirect in data.redirects:
        existing_target = redirects.get(redirect.slug)
        if redirect.slug not in by_slug and existing_target == redirect.post_id:
            continue
        if redirect.slug in by_slug or existing_target is not None:
            preview.conflicts.append(f"Redirect conflict: {redirect.slug}")
        elif redirect.post_id not in included_post_ids:
            preview.conflicts.append(f"Redirect points to a skipped post: {redirect.slug}")
        else:
            new_redirects.append(redirect)
    preview.new_tags = len(new_tags)
    preview.new_posts = len(posts)
    preview.files = len(images.checked)
    preview.ignored_files = images.ignored_count
    preview.missing_files = sorted(images.missing_files)
    preview.changed_files = sorted(images.changed_files)
    preview.can_import = not preview.conflicts and not preview.changed_files
    preview.can_skip_conflicts = bool(preview.conflicts) and not preview.changed_files
    return ImportPlan(preview, tags, new_tags, posts, new_redirects, site)


def inspect_content(
    *, session: Session, settings: Settings, data: NativeExport, sha256: str
) -> ImportPreview:
    return prepare_import(session=session, settings=settings, data=data, sha256=sha256).preview


def import_content(
    *,
    session: Session,
    settings: Settings,
    data: NativeExport,
    sha256: str,
    include_settings: bool,
    skip_conflicts: bool = False,
) -> ImportResult:
    session.rollback()
    begin_write(session)
    plan = prepare_import(session=session, settings=settings, data=data, sha256=sha256)
    preview = plan.preview
    if not (preview.can_import or (skip_conflicts and preview.can_skip_conflicts)):
        raise ConflictError(
            "Review the conflicts and changed image files in the import preview.",
            code="transfer.conflict",
        )
    session.add_all(TagOrm(**tag.model_dump()) for tag in plan.new_tags)
    session.flush()
    for prepared in plan.posts:
        post = prepared.source
        session.add(
            PostOrm(
                **post.model_dump(exclude={"tags"}),
                html=prepared.html,
                plain_text=prepared.plain_text,
            )
        )
        session.flush()
        session.add_all(
            PostTagOrm(post_id=post.id, tag_id=plan.tag_ids[tag_id], position=index)
            for index, tag_id in enumerate(post.tags)
        )
    session.flush()
    session.add_all(PostRedirectOrm(**redirect.model_dump()) for redirect in plan.redirects)
    if include_settings:
        update_site(db_session=session, data=plan.site)
    session.flush()
    return ImportResult(
        imported_posts=preview.new_posts,
        imported_tags=preview.new_tags,
        skipped_posts=preview.skipped_posts,
        skipped_conflicts=len(preview.conflicts),
        settings_imported=include_settings,
    )
