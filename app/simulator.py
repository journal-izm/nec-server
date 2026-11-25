"""FN-02-04 개표 시뮬레이터 — 시나리오를 시간에 맞춰 DB(count_region·count_candidate)에 발표.

- 시작·일시정지·배속(1·2·5)·초기화
- 1배속 환산 경과 시간(elapsed_sec)이 시나리오 줄의 t_sec를 넘으면 그 줄을 새 seq로 발표
- 초기화하면 발표한 집계를 모두 지우고 seq 0부터 (같은 시나리오 → 같은 결과, NFR-04)
- DEMO_MODE: 서버가 켜지면 자동 시작, 끝나면 DEMO_RESTART_SEC 뒤 다시 처음부터
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from . import config, scenario
from .db import SessionLocal
from .models import CountCandidate, CountRegion, Election, SimState

log = logging.getLogger("simulator")
ALLOWED_SPEED = (1, 2, 5)


class Simulator:
    def __init__(self, scenario_path=config.SCENARIO_PATH):
        self.rows = scenario.load(scenario_path)
        self.duration = scenario.total_duration(self.rows)
        self._task: asyncio.Task | None = None
        self._done_at: datetime | None = None

    # ── 상태 ──
    def state(self, db: Session) -> SimState:
        st = db.get(SimState, 1)
        if st is None:
            st = SimState(id=1, status="READY", speed=1, current_seq=0, scenario=config.SCENARIO)
            db.add(st)
            db.commit()
        return st

    def _election(self, db: Session) -> Election | None:
        return db.get(Election, config.ELECTION_ID)

    # ── 제어 (API-02-03) ──
    def start(self, db: Session, speed: int | None = None) -> SimState:
        st = self.state(db)
        if speed:
            self.set_speed(db, speed)
        if st.status == "DONE":
            self.reset(db)
            st = self.state(db)
        if st.status in ("READY", "PAUSED"):
            st.status = "RUNNING"
            st.started_at = st.started_at or datetime.now()
            el = self._election(db)
            if el:
                el.status = "COUNTING"
        db.commit()
        return st

    def pause(self, db: Session) -> SimState:
        st = self.state(db)
        if st.status == "RUNNING":
            st.status = "PAUSED"
        db.commit()
        return st

    def set_speed(self, db: Session, speed: int) -> SimState:
        if speed not in ALLOWED_SPEED:
            raise ValueError(f"배속은 {ALLOWED_SPEED} 중 하나여야 합니다")
        st = self.state(db)
        st.speed = speed
        db.commit()
        return st

    def reset(self, db: Session) -> SimState:
        db.query(CountCandidate).delete()
        db.query(CountRegion).delete()
        st = self.state(db)
        st.status, st.current_seq, st.elapsed_sec, st.next_index, st.started_at = "READY", 0, 0.0, 0, None
        el = self._election(db)
        if el:
            el.status = "READY"
        db.commit()
        self._done_at = None
        return st

    # ── 시계 한 칸 ──
    def step(self, db: Session, real_dt: float) -> int:
        """실제로 real_dt초가 지났을 때 호출. 새로 발표한 줄 수를 돌려줌."""
        st = self.state(db)
        if st.status != "RUNNING":
            return 0
        st.elapsed_sec += real_dt * st.speed
        rows = scenario.due(self.rows, st.next_index, st.elapsed_sec)
        for r in rows:
            st.current_seq += 1
            db.add(CountRegion(seq=st.current_seq, region_code=r.region_code, counted_votes=r.counted_votes,
                               invalid_votes=r.invalid_votes, counted_rate=r.counted_rate, created_at=datetime.now()))
            for cid, v in r.votes.items():
                db.add(CountCandidate(seq=st.current_seq, region_code=r.region_code, candidate_id=cid, votes=v))
        st.next_index += len(rows)
        if st.next_index >= len(self.rows):
            st.status = "DONE"
            el = self._election(db)
            if el:
                el.status = "CLOSED"
            self._done_at = datetime.now()
        db.commit()
        return len(rows)

    def total_rate(self, db: Session) -> float:
        """전체 개표율 = 구별 최신 개표수 합 / 구별 전체 투표수 추정 합."""
        latest: dict[str, CountRegion] = {}
        for cr in db.query(CountRegion).order_by(CountRegion.seq).all():
            latest[cr.region_code] = cr
        if not latest:
            return 0.0
        counted = sum(c.counted_votes for c in latest.values())
        ballots = sum(c.counted_votes / (c.counted_rate / 100) for c in latest.values() if c.counted_rate > 0)
        from .models import Region
        seen = set(latest)
        missing = db.query(Region).filter(~Region.region_code.in_(seen)).all()
        turnout = 0.65
        ballots += sum(r.electors * turnout for r in missing)
        return round(counted / ballots * 100, 2) if ballots else 0.0

    # ── 백그라운드 루프 ──
    async def run_forever(self):
        last = asyncio.get_event_loop().time()
        if config.DEMO_MODE:
            with SessionLocal() as db:
                self.reset(db)
                self.start(db)
                log.info("DEMO_MODE: 시뮬레이터 자동 시작")
        while True:
            await asyncio.sleep(config.TICK_SEC)
            now = asyncio.get_event_loop().time()
            dt, last = now - last, now
            try:
                with SessionLocal() as db:
                    self.step(db, dt)
                    if config.DEMO_MODE and self._done_at and \
                            (datetime.now() - self._done_at).total_seconds() >= config.DEMO_RESTART_SEC:
                        self.reset(db)
                        self.start(db)
                        log.info("DEMO_MODE: 처음부터 다시 재생")
            except Exception:  # 루프는 멈추지 않음
                log.exception("시뮬레이터 오류")

    def launch(self):
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self.run_forever())
        return self._task


sim = Simulator()
