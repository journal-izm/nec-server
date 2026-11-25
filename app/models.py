"""선관위 DB 테이블 — 05 DB설계서 TBL-02-01 ~ TBL-02-07."""
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Election(Base):                       # TBL-02-01
    __tablename__ = "election"
    election_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    election_date: Mapped[date] = mapped_column(Date)
    total_electors: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(10), default="READY")   # READY / COUNTING / CLOSED


class Region(Base):                         # TBL-02-02
    __tablename__ = "region"
    region_code: Mapped[str] = mapped_column(String(10), primary_key=True)
    election_id: Mapped[str] = mapped_column(ForeignKey("election.election_id"))
    name: Mapped[str] = mapped_column(String(20))
    electors: Mapped[int] = mapped_column(Integer)
    sort_order: Mapped[int] = mapped_column(Integer)


class Candidate(Base):                      # TBL-02-03
    __tablename__ = "candidate"
    candidate_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    election_id: Mapped[str] = mapped_column(ForeignKey("election.election_id"))
    ballot_no: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(20))
    party: Mapped[str | None] = mapped_column(String(30), nullable=True)
    color: Mapped[str] = mapped_column(String(7))


class CountRegion(Base):                    # TBL-02-04  (seq마다 1행)
    __tablename__ = "count_region"
    seq: Mapped[int] = mapped_column(Integer, primary_key=True)
    region_code: Mapped[str] = mapped_column(ForeignKey("region.region_code"), primary_key=True)
    counted_votes: Mapped[int] = mapped_column(Integer)
    invalid_votes: Mapped[int] = mapped_column(Integer)
    counted_rate: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class CountCandidate(Base):                 # TBL-02-05
    __tablename__ = "count_candidate"
    seq: Mapped[int] = mapped_column(Integer, primary_key=True)
    region_code: Mapped[str] = mapped_column(ForeignKey("region.region_code"), primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate.candidate_id"), primary_key=True)
    votes: Mapped[int] = mapped_column(Integer)


class StationKey(Base):                     # TBL-02-06
    __tablename__ = "station_key"
    station_code: Mapped[str] = mapped_column(String(5), primary_key=True)
    station_name: Mapped[str] = mapped_column(String(30))
    api_key_hash: Mapped[str] = mapped_column(String(100))
    last_called_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class SimState(Base):                       # TBL-02-07  (항상 1행)
    __tablename__ = "sim_state"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    status: Mapped[str] = mapped_column(String(10), default="READY")   # READY / RUNNING / PAUSED / DONE
    speed: Mapped[int] = mapped_column(Integer, default=1)              # 1 · 2 · 5
    current_seq: Mapped[int] = mapped_column(Integer, default=0)
    scenario: Mapped[str] = mapped_column(String(30))
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # 설계 외 보조 칸: 다시 켜져도 이어서 재생하기 위한 위치
    elapsed_sec: Mapped[float] = mapped_column(Float, default=0.0)      # 1배속 환산 경과 초
    next_index: Mapped[int] = mapped_column(Integer, default=0)         # 다음에 발표할 시나리오 줄
