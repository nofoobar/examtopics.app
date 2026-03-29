from sqlmodel import Session
from db.database import engine


def get_db():
    with Session(engine) as session:
        yield session
