from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from apis.deps import get_db
from db.models.advertisement import Advertisement

router = APIRouter(prefix="/api/v1/ads", tags=["ads"])


@router.post("/{ad_id}/click")
def track_click(ad_id: int, session: Session = Depends(get_db)):
    """Increment click counter for an ad. Called fire-and-forget from JS."""
    ad = session.get(Advertisement, ad_id)
    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")
    ad.click_count += 1
    session.add(ad)
    session.commit()
    return JSONResponse({"ok": True})
