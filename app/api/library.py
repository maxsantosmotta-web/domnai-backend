from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy import select

from app.auth import require_authenticated_user
from app.database import session_scope
from app.models import DeletedAsset, LibraryAsset

router = APIRouter(prefix="/api/library", tags=["library"])

MAX_FILE_SIZE = 15 * 1024 * 1024


def serialize_asset(asset: LibraryAsset) -> dict:
    return {
        "id": asset.id,
        "name": asset.name,
        "mimeType": asset.mime_type,
        "sizeBytes": asset.size_bytes,
        "createdAt": asset.created_at.isoformat(),
    }


@router.get("")
def list_library_assets(session: dict = Depends(require_authenticated_user)):
    user_id = session.get("sub")
    with session_scope() as db:
        assets = db.scalars(
            select(LibraryAsset)
            .where(LibraryAsset.user_id == user_id)
            .order_by(LibraryAsset.created_at.desc())
        ).all()
        return {"items": [serialize_asset(asset) for asset in assets]}


@router.post("", status_code=status.HTTP_201_CREATED)
async def save_file_to_library(
    file: UploadFile = File(...),
    session: dict = Depends(require_authenticated_user),
):
    user_id = session.get("sub")
    content = await file.read(MAX_FILE_SIZE + 1)

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="O arquivo ultrapassa o limite de 15 MB.",
        )

    if not content:
        raise HTTPException(status_code=400, detail="O arquivo está vazio.")

    asset = LibraryAsset(
        user_id=user_id,
        name=(file.filename or "arquivo")[:255],
        mime_type=(file.content_type or "application/octet-stream")[:120],
        size_bytes=len(content),
        content=content,
    )

    with session_scope() as db:
        db.add(asset)
        db.flush()
        result = serialize_asset(asset)

    return result


@router.get("/{asset_id}/content")
def get_library_asset_content(
    asset_id: str,
    session: dict = Depends(require_authenticated_user),
):
    user_id = session.get("sub")
    with session_scope() as db:
        asset = db.scalar(
            select(LibraryAsset).where(
                LibraryAsset.id == asset_id,
                LibraryAsset.user_id == user_id,
            )
        )
        if asset is None:
            raise HTTPException(status_code=404, detail="Arquivo não encontrado na biblioteca.")

        return Response(
            content=asset.content,
            media_type=asset.mime_type,
            headers={
                "Content-Disposition": f'attachment; filename="{asset.name}"',
                "X-File-Name": asset.name,
            },
        )


@router.post("/{asset_id}/trash")
def move_library_asset_to_trash(
    asset_id: str,
    session: dict = Depends(require_authenticated_user),
):
    user_id = session.get("sub")
    with session_scope() as db:
        asset = db.scalar(
            select(LibraryAsset).where(
                LibraryAsset.id == asset_id,
                LibraryAsset.user_id == user_id,
            )
        )
        if asset is None:
            raise HTTPException(status_code=404, detail="Arquivo não encontrado na biblioteca.")

        deleted_asset = DeletedAsset(
            user_id=asset.user_id,
            name=asset.name,
            mime_type=asset.mime_type,
            size_bytes=asset.size_bytes,
            content=asset.content,
        )
        db.add(deleted_asset)
        db.delete(asset)
        db.flush()

        return {
            "id": deleted_asset.id,
            "name": deleted_asset.name,
            "mimeType": deleted_asset.mime_type,
            "sizeBytes": deleted_asset.size_bytes,
            "deletedAt": deleted_asset.deleted_at.isoformat(),
        }
