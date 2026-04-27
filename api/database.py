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
_SessionLocal = None


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
        logger.info("Database engine created.")
    return _engine


def get_db():
    Session = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    db = Session()
    try:
        yield db
    finally:
        db.close()


class Base(DeclarativeBase):
    pass
