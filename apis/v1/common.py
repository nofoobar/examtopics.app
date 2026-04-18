from fastapi import APIRouter, Depends, Request
from sqlmodel import Session, select, func

from apis.deps import get_db
from db.models.exam import Vendor, Exam
from utils.templates import templates
from core.config import settings


router = APIRouter(prefix="", tags=["common"])


@router.get("/")
async def index(request: Request, session: Session = Depends(get_db)):
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
        "common/homepage.html",
        {
            "vendors_with_exams": vendors_with_exams,
            "total_exams": total_exams,
        },
    )


@router.get("/advertise-with-us")
async def advertise(request: Request, session: Session = Depends(get_db)):
    total_exams = session.exec(
        select(func.count(Exam.id)).where(Exam.is_active == True)
    ).one()
    return templates.TemplateResponse(
        request,
        "common/advertise.html",
        {"total_exams": total_exams},
    )


@router.get("/about")
async def about(request: Request):
    return templates.TemplateResponse(request, "common/about.html", {})


@router.get("/privacy")
async def privacy(request: Request):
    return templates.TemplateResponse(request, "common/privacy.html", {})


@router.get("/terms")
async def terms(request: Request):
    return templates.TemplateResponse(request, "common/terms.html", {})


@router.get("/contact")
async def contact(request: Request):
    return templates.TemplateResponse(request, "common/contact.html", {})
