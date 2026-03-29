from fastapi import APIRouter

from apis.v1.common import router as common_router
from apis.v1.seo import router as seo_router
from apis.v1.exams import router as exams_router
from apis.v1.ads import router as ads_router
from apis.v1.generate import router as generate_router
from apis.v1.exam_request import router as exam_request_router
from apis.v1.search import router as search_router

router = APIRouter()
router.include_router(common_router)
router.include_router(seo_router)
router.include_router(exams_router)
router.include_router(ads_router)
router.include_router(generate_router)
router.include_router(exam_request_router)
router.include_router(search_router)
