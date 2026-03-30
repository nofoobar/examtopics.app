import secrets
from fastapi import FastAPI, Depends, HTTPException, status
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
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.openapi.docs import get_swagger_ui_html


security = HTTPBasic()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
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


def verify_docs_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, settings.DOCS_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, settings.DOCS_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Basic"},
        )


@app.get("/api/openapi.json", include_in_schema=False)
async def openapi(credentials: HTTPBasicCredentials = Depends(verify_docs_credentials)):
    return app.openapi()


@app.get("/api/docs", include_in_schema=False)
async def docs(credentials: HTTPBasicCredentials = Depends(verify_docs_credentials)):
    return get_swagger_ui_html(openapi_url="/api/openapi.json", title=settings.APP_NAME)

