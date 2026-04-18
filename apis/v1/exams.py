from fastapi import APIRouter, Depends, Request, HTTPException, Query
from sqlmodel import Session, select, func
from typing import List
import math

from apis.deps import get_db
from db.models.exam import Vendor, Exam, Test, Question
from db.models.advertisement import Advertisement, AdPosition
from schemas.exams import VendorWithExams
from utils.templates import templates

router = APIRouter(tags=["exams"])

QUESTIONS_PER_PAGE = 10


# ── JSON API ──────────────────────────────────────────────────────────────────

@router.get("/api/v1/exams", response_model=List[VendorWithExams])
def list_exams_api(session: Session = Depends(get_db)):
    """Return all active vendors with their active exams."""
    vendors = session.exec(
        select(Vendor).where(Vendor.is_active == True)
    ).all()

    result = []
    for vendor in vendors:
        exams = session.exec(
            select(Exam)
            .where(Exam.vendor_id == vendor.id, Exam.is_active == True)
            .order_by(Exam.name)
        ).all()
        result.append(VendorWithExams(
            id=vendor.id,
            name=vendor.name,
            slug=vendor.slug,
            description=vendor.description,
            exams=[e for e in exams],
        ))

    return result


# ── /exams ────────────────────────────────────────────────────────────────────

@router.get("/exams")
def list_exams_page(request: Request, session: Session = Depends(get_db)):
    """Render the exams list page grouped by vendor."""
    vendors = session.exec(
        select(Vendor).where(Vendor.is_active == True)
    ).all()

    vendors_with_exams = []
    total_exams = 0
    for vendor in vendors:
        exams = session.exec(
            select(Exam)
            .where(Exam.vendor_id == vendor.id, Exam.is_active == True)
            .order_by(Exam.name)
        ).all()
        total_exams += len(exams)
        vendors_with_exams.append({"vendor": vendor, "exams": exams})

    return templates.TemplateResponse(
        request,
        "exams/list.html",
        {
            "vendors_with_exams": vendors_with_exams,
            "total_exams": total_exams,
        },
    )


# ── /exams/vendor/{vendor_slug} — MUST come before /exams/{slug} ─────────────

@router.get("/exams/vendor/{vendor_slug}")
def vendor_page(vendor_slug: str, request: Request, session: Session = Depends(get_db)):
    """All exams for a single vendor."""
    vendor = session.exec(
        select(Vendor).where(Vendor.slug == vendor_slug, Vendor.is_active == True)
    ).first()

    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    exams = session.exec(
        select(Exam)
        .where(Exam.vendor_id == vendor.id, Exam.is_active == True)
        .order_by(Exam.name)
    ).all()

    total_questions = 0
    exams_with_counts = []
    for exam in exams:
        count = session.exec(
            select(func.count(Question.id))
            .join(Test, Question.test_id == Test.id)
            .where(Test.exam_id == exam.id, Question.is_active == True)
        ).one()
        total_questions += count
        exams_with_counts.append({"exam": exam, "question_count": count})

    return templates.TemplateResponse(
        request,
        "exams/vendor.html",
        {
            "vendor": vendor,
            "exams_with_counts": exams_with_counts,
            "total_questions": total_questions,
        },
    )


# ── /exams/{exam_slug}/{test_slug} ──────────────────────────────────────────

@router.get("/exams/{exam_slug}/{test_slug}")
def test_practice_page(
    exam_slug: str,
    test_slug: str,
    request: Request,
    session: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
):
    """Render the practice test page with paginated questions."""
    exam = session.exec(
        select(Exam).where(Exam.slug == exam_slug, Exam.is_active == True)
    ).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    test = session.exec(
        select(Test).where(Test.slug == test_slug, Test.exam_id == exam.id, Test.is_active == True)
    ).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    vendor = session.get(Vendor, exam.vendor_id)

    # Total question count for pagination maths
    total_questions = session.exec(
        select(func.count(Question.id))
        .where(Question.test_id == test.id, Question.is_active == True)
    ).one()

    total_pages = max(1, math.ceil(total_questions / QUESTIONS_PER_PAGE))
    page = min(page, total_pages)  # clamp so out-of-range pages don't 404
    offset = (page - 1) * QUESTIONS_PER_PAGE

    questions = session.exec(
        select(Question)
        .where(Question.test_id == test.id, Question.is_active == True)
        .order_by(Question.created_at)
        .offset(offset)
        .limit(QUESTIONS_PER_PAGE)
    ).all()

    # Ads
    all_ads = session.exec(
        select(Advertisement)
        .where(
            Advertisement.is_active == True,
            (Advertisement.exam_id == exam.id) | (Advertisement.is_generic_ad == True),
        )
    ).all()

    ads_by_position = {
        AdPosition.banner:  [a for a in all_ads if a.position == AdPosition.banner],
        AdPosition.inline:  [a for a in all_ads if a.position == AdPosition.inline],
        AdPosition.sidebar: [a for a in all_ads if a.position == AdPosition.sidebar],
    }

    return templates.TemplateResponse(
        request,
        "exams/test.html",
        {
            "exam": exam,
            "test": test,
            "vendor": vendor,
            "questions": questions,
            "ads": ads_by_position,
            # pagination
            "page": page,
            "total_pages": total_pages,
            "total_questions": total_questions,
            "page_size": QUESTIONS_PER_PAGE,
            "base_url": f"/exams/{exam_slug}/{test_slug}",
        },
    )


# ── /exams/{slug} — MUST come after /exams/vendor/{vendor_slug} ──────────────

@router.get("/exams/{slug}")
def exam_detail_page(slug: str, request: Request, session: Session = Depends(get_db)):
    """Render the exam detail page."""
    exam = session.exec(
        select(Exam).where(Exam.slug == slug, Exam.is_active == True)
    ).first()

    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    vendor = session.get(Vendor, exam.vendor_id)

    tests = session.exec(
        select(Test)
        .where(Test.exam_id == exam.id, Test.is_active == True)
        .order_by(Test.created_at)
    ).all()

    tests_with_counts = []
    total_questions = 0
    for test in tests:
        count = session.exec(
            select(func.count(Question.id))
            .where(Question.test_id == test.id, Question.is_active == True)
        ).one()
        total_questions += count
        tests_with_counts.append({"test": test, "question_count": count})

    return templates.TemplateResponse(
        request,
        "exams/detail.html",
        {
            "exam": exam,
            "vendor": vendor,
            "tests_with_counts": tests_with_counts,
            "total_questions": total_questions,
        },
    )
