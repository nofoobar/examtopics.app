from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqladmin import Admin

from core.config import settings
from db.database import engine
from utils.admin import AdminAuth
from apis.main import router as api_router
from db.admin.exam_admin import VendorAdmin, ExamAdmin, TestAdmin, QuestionAdmin
from db.admin.search_admin import SearchAdmin
from db.admin.advertisement_admin import AdvertisementAdmin
from db.admin.exam_request_admin import ExamRequestAdmin
from db.admin.generation_job_admin import GenerationJobAdmin


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/api/docs",
)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(api_router)

authentication_backend = AdminAuth(secret_key=settings.SECRET_KEY)
admin = Admin(app, engine, authentication_backend=authentication_backend)
admin.add_view(VendorAdmin)
admin.add_view(ExamAdmin)
admin.add_view(TestAdmin)
admin.add_view(QuestionAdmin)
admin.add_view(SearchAdmin)
admin.add_view(AdvertisementAdmin)
admin.add_view(ExamRequestAdmin)
admin.add_view(GenerationJobAdmin)


@app.get("/health")
async def health():
    return {"status": "ok"}
