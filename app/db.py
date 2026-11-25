"""DB 연결 — SQLAlchemy. 주소(NEC_DB_URL)만 바꾸면 PostgreSQL로도 옮길 수 있음."""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import NEC_DB_URL

_is_sqlite = NEC_DB_URL.startswith("sqlite")
engine = create_engine(NEC_DB_URL, connect_args={"check_same_thread": False} if _is_sqlite else {})

if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _sqlite_pragma(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")   # 읽기·쓰기가 겹쳐도 덜 막힘
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from . import models  # noqa: F401  (테이블 등록)
    Base.metadata.create_all(engine)
