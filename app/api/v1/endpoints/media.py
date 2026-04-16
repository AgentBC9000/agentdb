from fastapi import APIRouter, Depends, HTTPException
from app.core.dependencies import get_current_key, require_pro
from app.db.client import get_db
from app.services.rate_limiter import check_rate_limit
from app.services.storage import get_signed_url

router = APIRouter()


@router.get("/{media_id}")
async def get_media_item(
    media_id: str,
    key_record=Depends(get_current_key),
    db=Depends(get_db),
):
    await check_rate_limit(key_record)

    row = await db.fetch_one(
        "SELECT * FROM media WHERE id = :id",
        {"id": media_id}
    )

    if not row:
        raise HTTPException(status_code=404, detail="Media not found")

    media = dict(row)
    media["signed_url"] = await get_signed_url(row["r2_key"], expires_in=3600)
    media.pop("r2_key")
    return media


@router.get("/{media_id}/transcript")
async def get_transcript(
    media_id: str,
    key_record=Depends(get_current_key),
    db=Depends(get_db),
):
    await check_rate_limit(key_record)

    row = await db.fetch_one(
        "SELECT id, transcript, duration_secs FROM media WHERE id = :id",
        {"id": media_id}
    )

    if not row:
        raise HTTPException(status_code=404, detail="Media not found")

    return {
        "media_id": media_id,
        "transcript": row["transcript"],
        "duration_secs": row["duration_secs"],
    }


@router.get("/{media_id}/keyframes")
async def get_keyframes(
    media_id: str,
    key_record=Depends(require_pro),
    db=Depends(get_db),
):
    row = await db.fetch_one(
        "SELECT keyframes FROM media WHERE id = :id",
        {"id": media_id}
    )

    if not row or not row["keyframes"]:
        raise HTTPException(status_code=404, detail="Keyframes not available")

    signed_frames = []
    for frame_key in row["keyframes"]:
        signed_frames.append(await get_signed_url(frame_key, expires_in=3600))

    return {"media_id": media_id, "keyframes": signed_frames}
