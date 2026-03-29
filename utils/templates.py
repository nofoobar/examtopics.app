from datetime import datetime

from fastapi.templating import Jinja2Templates

from core.config import settings

templates = Jinja2Templates(directory="templates")

# ── Globals available in every template ──────────────────────────────────────
templates.env.globals["settings"] = settings
templates.env.globals["now"] = datetime.now()
templates.env.globals["month_and_year"] = datetime.now().strftime("%B %Y")
