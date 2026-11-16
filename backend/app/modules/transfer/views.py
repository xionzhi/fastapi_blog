"""Authenticated native JSON transfer; uploaded paths are never used as filesystem roots."""

import hashlib
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from starlette.concurrency import run_in_threadpool

from app.common.exceptions import ApplicationError
from app.core.dependencies import DbSession, SettingsDependency
from app.modules.auth.dependencies import get_current_user
from app.modules.transfer import service
from app.modules.transfer.models import MAX_JSON_BYTES, ImportPreview, ImportResult

router = APIRouter(
    prefix="/admin/data", tags=["admin data"], dependencies=[Depends(get_current_user)]
)


async def read_content(request: Request) -> bytes:
    content = bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content) > MAX_JSON_BYTES:
            raise ApplicationError(
                "JSON exports must not exceed 16 MB", code="transfer.too_large", status_code=413
            )
    return bytes(content)


@router.get("/export")
def export_data(db_session: DbSession, settings: SettingsDependency) -> Response:
    data = service.export_content(session=db_session, settings=settings)
    content = data.model_dump_json(indent=2).encode("utf-8")
    if len(content) > MAX_JSON_BYTES:
        raise ApplicationError(
            "This export exceeds the 16 MB JSON transfer limit",
            code="transfer.too_large",
            status_code=413,
        )
    return Response(
        content,
        media_type="application/json",
        headers={
            "Content-Disposition": 'attachment; filename="xionzhi-blog.json"',
            "Cache-Control": "no-store",
        },
    )


@router.post("/preview", response_model=ImportPreview)
async def preview_data(
    request: Request, db_session: DbSession, settings: SettingsDependency
) -> ImportPreview:
    content = await read_content(request)
    data = await run_in_threadpool(service.parse_content, content)
    result, _ = await run_in_threadpool(
        service.inspect_content,
        session=db_session,
        settings=settings,
        data=data,
        sha256=hashlib.sha256(content).hexdigest(),
    )
    return result


@router.post("/import", response_model=ImportResult)
async def import_data(
    request: Request,
    db_session: DbSession,
    settings: SettingsDependency,
    sha256: Annotated[str, Query(pattern=r"^[a-f0-9]{64}$")],
    include_settings: bool = False,
    allow_missing_files: bool = False,
) -> ImportResult:
    content = await read_content(request)
    actual = hashlib.sha256(content).hexdigest()
    if actual != sha256:
        raise ApplicationError(
            "The selected file changed. Preview it again before importing.",
            code="transfer.file_changed",
            status_code=409,
        )
    data = await run_in_threadpool(service.parse_content, content)
    return await run_in_threadpool(
        service.import_content,
        session=db_session,
        settings=settings,
        data=data,
        sha256=actual,
        include_settings=include_settings,
        allow_missing_files=allow_missing_files,
    )
