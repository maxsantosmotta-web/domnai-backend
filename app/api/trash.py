from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy import delete, select

from app.auth import require_authenticated_user
from app.database import session_scope
from app.models import DeletedAsset, LibraryAsset

router = APIRouter(prefix="/api/trash", tags=["trash"])

MAX_FILE_SIZE = 15 * 1024 * 1024


def serialize_asset(asset: DeletedAsset) -> dict:
    return {
        "id": asset.id,
        "name": asset.name,
        "mimeType": asset.mime_type,
        "sizeBytes": asset.size_bytes,
        "deletedAt": asset.deleted_at.isoformat(),
    }


@router.get("")
def list_deleted_assets(session: dict = Depends(require_authenticated_user)):
    user_id = session.get("sub")
    with session_scope() as db:
        assets = db.scalars(
            select(DeletedAsset)
            .where(DeletedAsset.user_id == user_id)
            .order_by(DeletedAsset.deleted_at.desc())
        ).all()
        return {"items": [serialize_asset(asset) for asset in assets]}


@router.post("", status_code=status.HTTP_201_CREATED)
async def move_file_to_trash(
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

    asset = DeletedAsset(
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


@router.post("/{asset_id}/restore")
def restore_asset_to_library(
    asset_id: str,
    session: dict = Depends(require_authenticated_user),
):
    user_id = session.get("sub")
    with session_scope() as db:
        asset = db.scalar(
            select(DeletedAsset).where(
                DeletedAsset.id == asset_id,
                DeletedAsset.user_id == user_id,
            )
        )
        if asset is None:
            raise HTTPException(status_code=404, detail="Arquivo não encontrado na lixeira.")

        library_asset = LibraryAsset(
            user_id=asset.user_id,
            name=asset.name,
            mime_type=asset.mime_type,
            size_bytes=asset.size_bytes,
            content=asset.content,
        )
        db.add(library_asset)
        db.delete(asset)
        db.flush()

        return {
            "id": library_asset.id,
            "name": library_asset.name,
            "mimeType": library_asset.mime_type,
            "sizeBytes": library_asset.size_bytes,
            "createdAt": library_asset.created_at.isoformat(),
        }


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def permanently_delete_asset(
    asset_id: str,
    session: dict = Depends(require_authenticated_user),
):
    user_id = session.get("sub")
    with session_scope() as db:
        asset = db.scalar(
            select(DeletedAsset).where(
                DeletedAsset.id == asset_id,
                DeletedAsset.user_id == user_id,
            )
        )
        if asset is None:
            raise HTTPException(status_code=404, detail="Arquivo não encontrado na lixeira.")
        db.delete(asset)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def empty_trash(session: dict = Depends(require_authenticated_user)):
    user_id = session.get("sub")
    with session_scope() as db:
        db.execute(delete(DeletedAsset).where(DeletedAsset.user_id == user_id))

    return Response(status_code=status.HTTP_204_NO_CONTENT)
