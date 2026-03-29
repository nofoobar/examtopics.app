from fastapi import APIRouter, Depends, Request, Query
from sqlmodel import Session, select, or_

from apis.deps import get_db
from db.models.exam import Vendor, Exam, Test
from db.models.search import Search
from utils.templates import templates

router = APIRouter(tags=["search"])


def _log_search(session: Session, term: str, results_count: int, request: Request) -> None:
    """Fire-and-forget search log — does not raise."""
    try:
        ip = request.headers.get("x-forwarded-for", request.client.host if request.client else None)
        session.add(Search(search_term=term, results_count=results_count, ip_address=ip))
        session.commit()
    except Exception:
        pass


def _do_search(session: Session, q: str) -> dict:
    """
    Returns {"vendors": [...], "exams": [...], "tests": [...]}
    Each item is a plain dict safe for JSON serialisation.
    """
    term = q.strip()
    if not term:
        return {"vendors": [], "exams": [], "tests": []}

    like = f"%{term}%"

    vendors = session.exec(
        select(Vendor).where(
            Vendor.is_active == True,
            or_(Vendor.name.ilike(like), Vendor.slug.ilike(like)),
        ).limit(5)
    ).all()

    exams = session.exec(
        select(Exam).where(
            Exam.is_active == True,
            or_(
                Exam.name.ilike(like),
                Exam.exam_code.ilike(like),
                Exam.slug.ilike(like),
            ),
        ).limit(10)
    ).all()

    tests = session.exec(
        select(Test).where(
            Test.is_active == True,
            Test.name.ilike(like),
        ).limit(5)
    ).all()

    return {
        "vendors": [
            {"id": v.id, "name": v.name, "slug": v.slug, "url": f"/exams/vendor/{v.slug}"}
            for v in vendors
        ],
        "exams": [
            {
                "id": e.id,
                "name": e.name,
                "exam_code": e.exam_code,
                "slug": e.slug,
                "url": f"/exams/{e.slug}",
            }
            for e in exams
        ],
        "tests": [
            {"id": t.id, "name": t.name, "exam_id": t.exam_id, "slug": t.slug}
            for t in tests
        ],
    }


# ── JSON endpoint (used by the search overlay) ────────────────────────────────

@router.get("/api/v1/search")
def search_api(
    q: str = Query(default="", max_length=200),
    request: Request = None,
    session: Session = Depends(get_db),
):
    results = _do_search(session, q)
    total   = len(results["vendors"]) + len(results["exams"]) + len(results["tests"])
    if q.strip():
        _log_search(session, q.strip(), total, request)
    return results


# ── HTML results page ─────────────────────────────────────────────────────────

@router.get("/search")
def search_page(
    q: str = Query(default="", max_length=200),
    request: Request = None,
    session: Session = Depends(get_db),
):
    results = _do_search(session, q)
    total   = len(results["vendors"]) + len(results["exams"]) + len(results["tests"])
    if q.strip():
        _log_search(session, q.strip(), total, request)

    return templates.TemplateResponse(
        request,
        "search/results.html",
        {"q": q, "results": results, "total": total},
    )
