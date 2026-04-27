import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:root@localhost:3306/estoque_db",
)

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            pool_recycle=280,
            connect_args={"connect_timeout": 10} if "mysql" in DATABASE_URL else {},
            echo=False,
        )
    return _engine


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Base(DeclarativeBase):
    pass


# Lazy session factory
def get_session_factory():
    return sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
