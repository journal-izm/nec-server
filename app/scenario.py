"""개표 시나리오 (FN-02-04)

시나리오 파일(CSV) 한 줄 = 한 지역의 한 번 갱신.
  t_sec        : 1배속 기준, 개표 시작 후 몇 초에 발표되는지
  region_code  : STAR / DEEP / DUNE / NEBULA / ORBIT
  counted_votes: 지금까지 개표된 투표수 (무효표 포함)
  invalid_votes: 무효표
  counted_rate : 지역 개표율(%) = 개표된 투표수 / 전체 투표수 × 100
  v1, v2, v3   : 후보별 누적 득표 (기호 1·2·3)

이 파일은 FastAPI·DB 없이도 동작하도록 표준 라이브러리만 씁니다 (pytest로 바로 확인).
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Row:
    t_sec: float
    region_code: str
    counted_votes: int
    invalid_votes: int
    counted_rate: float
    votes: dict  # {후보번호(int): 누적 득표}


def load(path: str | Path) -> list[Row]:
    rows: list[Row] = []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            votes = {int(k[1:]): int(v) for k, v in r.items() if k.startswith("v") and k[1:].isdigit()}
            rows.append(Row(float(r["t_sec"]), r["region_code"], int(r["counted_votes"]),
                            int(r["invalid_votes"]), float(r["counted_rate"]), votes))
    rows.sort(key=lambda x: x.t_sec)
    return rows


def due(rows: list[Row], next_index: int, elapsed_sec: float) -> list[Row]:
    """아직 발표하지 않은 줄 중에서 elapsed_sec(1배속 환산)까지 발표할 줄."""
    out = []
    i = next_index
    while i < len(rows) and rows[i].t_sec <= elapsed_sec:
        out.append(rows[i])
        i += 1
    return out


def total_duration(rows: list[Row]) -> float:
    return rows[-1].t_sec if rows else 0.0


def check(rows: list[Row]) -> list[str]:
    """시나리오가 규칙을 지키는지 검사 — 문제 목록을 돌려줌 (빈 목록이면 통과)."""
    problems = []
    last: dict[str, Row] = {}
    for r in rows:
        p = last.get(r.region_code)
        if not 0 <= r.counted_rate <= 100:
            problems.append(f"{r.region_code} t={r.t_sec}: 개표율 범위 밖 {r.counted_rate}")
        if sum(r.votes.values()) + r.invalid_votes != r.counted_votes:
            problems.append(f"{r.region_code} t={r.t_sec}: 득표+무효 != 개표수")
        if p:
            if r.counted_votes < p.counted_votes or r.counted_rate < p.counted_rate:
                problems.append(f"{r.region_code} t={r.t_sec}: 개표수·개표율이 줄어듦")
            for k, v in r.votes.items():
                if v < p.votes.get(k, 0):
                    problems.append(f"{r.region_code} t={r.t_sec}: 후보 {k} 득표가 줄어듦")
        last[r.region_code] = r
    for code, r in last.items():
        if r.counted_rate != 100:
            problems.append(f"{code}: 마지막 개표율이 100이 아님 ({r.counted_rate})")
    return problems
