from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import create_engine
from functools import lru_cache

from core.config import get_settings, Settings

# Lazily build & cache the engine
@lru_cache()
def get_engine():
    settings: Settings = get_settings()
    return create_engine(settings.SQLALCHEMY_DATABASE_URL, future=True)

# Lazily build & cache the SessionLocal factory
@lru_cache()
def get_sessionmaker():
    engine = get_engine()
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

class Base(DeclarativeBase):
    pass
