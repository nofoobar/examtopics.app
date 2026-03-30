from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse
from sqlmodel import Session, select

from apis.deps import get_db
from core.config import settings
from db.models.exam import Exam, Test
from utils.templates import templates

router = APIRouter(tags=["seo"])


@router.get("/robots.txt", response_class=PlainTextResponse, include_in_schema=False)
async def robots_txt():
    content = f"""User-agent: *
Allow: /

Disallow: /api/
Disallow: /admin/
Disallow: /login
Disallow: /register
Disallow: /account/

Sitemap: {settings.APP_URL}/sitemap.xml
"""
    return PlainTextResponse(content, media_type="text/plain")


@router.get("/sitemap.xml", response_class=PlainTextResponse, include_in_schema=False)
async def sitemap_xml(request: Request, session: Session = Depends(get_db)):
    """
    Dynamic sitemap — static pages + all active exam & test pages.
    """
    base = settings.APP_URL
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    all_urls: list[dict] = [
        {"loc": f"{base}/",       "priority": "1.0", "changefreq": "daily"},
        {"loc": f"{base}/exams",  "priority": "0.9", "changefreq": "daily"},
        {"loc": f"{base}/about",  "priority": "0.4", "changefreq": "monthly"},
        {"loc": f"{base}/privacy","priority": "0.3", "changefreq": "monthly"},
        {"loc": f"{base}/terms",  "priority": "0.3", "changefreq": "monthly"},
        {"loc": f"{base}/contact","priority": "0.3", "changefreq": "monthly"},
    ]

    # --- Exam detail pages: /exams/{exam.slug} ---
    exams = session.exec(
        select(Exam).where(Exam.is_active == True).order_by(Exam.updated_at.desc())
    ).all()

    for exam in exams:
        all_urls.append({
            "loc": f"{base}/exams/{exam.slug}",
            "priority": "0.8",
            "changefreq": "weekly",
            "lastmod": exam.updated_at.strftime("%Y-%m-%d") if exam.updated_at else now,
        })

    # --- Test (practice) pages: /exams/{exam.slug}/{test.slug} ---
    tests = session.exec(
        select(Test, Exam)
        .join(Exam, Test.exam_id == Exam.id)
        .where(Test.is_active == True, Exam.is_active == True)
        .order_by(Test.updated_at.desc())
    ).all()

    for test, exam in tests:
        all_urls.append({
            "loc": f"{base}/exams/{exam.slug}/{test.slug}",
            "priority": "0.7",
            "changefreq": "weekly",
            "lastmod": test.updated_at.strftime("%Y-%m-%d") if test.updated_at else now,
        })

    urls_xml = "\n".join(
        f"""  <url>
    <loc>{u["loc"]}</loc>
    <lastmod>{u.get("lastmod", now)}</lastmod>
    <changefreq>{u["changefreq"]}</changefreq>
    <priority>{u["priority"]}</priority>
  </url>"""
        for u in all_urls
    )

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls_xml}
</urlset>"""

    return PlainTextResponse(xml, media_type="application/xml")
