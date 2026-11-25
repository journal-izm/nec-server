"""API-02-03 · API-02-04 — 시뮬레이터 제어·상태 (X-ADMIN-KEY)."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import admin_auth
from ..db import get_db
from ..models import StationKey
from ..simulator import sim

router = APIRouter(prefix="/nec/v1/sim", tags=["시뮬레이터 (X-ADMIN-KEY)"], dependencies=[Depends(admin_auth)])


class Control(BaseModel):
    action: Literal["start", "pause", "reset", "speed"]
    speed: int | None = None


def _status(db: Session) -> dict:
    st = sim.state(db)
    return {"status": st.status, "speed": st.speed, "current_seq": st.current_seq,
            "elapsed_sec": round(st.elapsed_sec, 1), "duration_sec": sim.duration,
            "total_rate": sim.total_rate(db), "scenario": st.scenario,
            "stations": [{"code": s.station_code, "name": s.station_name,
                          "last_called_at": s.last_called_at.strftime("%H:%M:%S") if s.last_called_at else None}
                         for s in db.query(StationKey).order_by(StationKey.station_code).all()]}


@router.post("/control", summary="API-02-03 시뮬레이터 제어")
def control(body: Control, db: Session = Depends(get_db)):
    try:
        if body.action == "start":
            sim.start(db, body.speed)
        elif body.action == "pause":
            sim.pause(db)
        elif body.action == "reset":
            sim.reset(db)
            if body.speed:
                sim.set_speed(db, body.speed)
        elif body.action == "speed":
            if not body.speed:
                raise HTTPException(422, "speed 값이 필요합니다")
            sim.set_speed(db, body.speed)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return _status(db)


@router.get("/status", summary="API-02-04 시뮬레이터 상태")
def status(db: Session = Depends(get_db)):
    return _status(db)
