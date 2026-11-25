"""FN-02-03 방송국 API 키 확인 · 관리 키 확인."""
import hashlib
import hmac
from datetime import datetime

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from . import config
from .db import get_db
from .models import StationKey


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def station_auth(x_api_key: str | None = Header(default=None), db: Session = Depends(get_db)) -> StationKey:
    """X-API-KEY를 등록된 방송국 키와 대조. 없거나 틀리면 401 (TC-API-01)."""
    if not x_api_key:
        raise HTTPException(401, "X-API-KEY 헤더가 필요합니다")
    h = hash_key(x_api_key)
    for st in db.query(StationKey).filter(StationKey.active.is_(True)).all():
        if hmac.compare_digest(st.api_key_hash, h):
            st.last_called_at = datetime.now()
            db.commit()
            return st
    raise HTTPException(401, "등록되지 않은 API 키입니다")


def admin_auth(x_admin_key: str | None = Header(default=None)) -> None:
    """시뮬레이터 제어용 X-ADMIN-KEY. .env의 ADMIN_KEY와 같아야 함 (TC-API-04)."""
    if not config.ADMIN_KEY:
        raise HTTPException(500, ".env에 ADMIN_KEY가 비어 있습니다")
    if not x_admin_key or not hmac.compare_digest(x_admin_key, config.ADMIN_KEY):
        raise HTTPException(403, "관리 키가 맞지 않습니다")
