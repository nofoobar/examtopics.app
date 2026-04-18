from sqlmodel import create_engine
from core.config import settings

connect_args = {"check_same_thread": False, "timeout": 30} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
