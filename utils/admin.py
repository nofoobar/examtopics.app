from fastapi import Request
from sqladmin.authentication import AuthenticationBackend

from core.config import settings


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
        if username == settings.ADMIN_USERNAME and password == settings.ADMIN_PASSWORD:
            request.session["admin_authenticated"] = True
            return True
        return False

    async def authenticate(self, request: Request) -> bool:
        return request.session.get("admin_authenticated", False)

    async def logout(self, request: Request) -> bool:
        request.session.pop("admin_authenticated", None)
        return True
