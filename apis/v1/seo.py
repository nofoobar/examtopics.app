from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from core.config import settings
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
async def sitemap_xml(request: Request):
    """
    Dynamic sitemap. Add your page URLs here as the site grows.
    For exam/question pages, query the DB and yield each URL.
    """
    base = settings.APP_URL
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Static pages — extend this list as you add routes
    static_urls = [
        {"loc": f"{base}/",            "priority": "1.0", "changefreq": "daily"},
        {"loc": f"{base}/exams",        "priority": "0.9", "changefreq": "daily"},
        {"loc": f"{base}/about",        "priority": "0.4", "changefreq": "monthly"},
        {"loc": f"{base}/privacy",      "priority": "0.3", "changefreq": "monthly"},
        {"loc": f"{base}/terms",        "priority": "0.3", "changefreq": "monthly"},
        {"loc": f"{base}/contact",      "priority": "0.3", "changefreq": "monthly"},
    ]

    urls_xml = "\n".join(
        f"""  <url>
    <loc>{u["loc"]}</loc>
    <lastmod>{now}</lastmod>
    <changefreq>{u["changefreq"]}</changefreq>
    <priority>{u["priority"]}</priority>
  </url>"""
        for u in static_urls
    )

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls_xml}
</urlset>"""

    return PlainTextResponse(xml, media_type="application/xml")
