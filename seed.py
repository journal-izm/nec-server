"""선관위 초기 데이터 — 선거·지역 5개·후보 3명·방송국 키 2개 (TC-DB-01)

python seed.py          # 처음 한 번 (여러 번 실행해도 같은 결과)
python seed.py --reset  # 집계까지 모두 지우고 다시
"""
import secrets
import sys
from datetime import date

from app import config
from app.auth import hash_key
from app.db import SessionLocal, init_db
from app.models import Candidate, CountCandidate, CountRegion, Election, Region, SimState, StationKey

ELECTION = dict(election_id=config.ELECTION_ID, name="2026 한빛시장 모의선거", election_date=date(2026, 12, 3))
# 코드, 이름, 선거인 수 — tools/make_scenario.py와 같아야 함
REGIONS = [("STAR", "별빛구", 82000), ("DEEP", "심해구", 76000), ("DUNE", "사막구", 64000),
           ("NEBULA", "성운구", 71000), ("ORBIT", "궤도구", 58000)]
# 모두 가상 인물 (우주 SF 분위기, 실존 작품의 이름은 쓰지 않음)
CANDIDATES = [(1, "윤별하", "은하공화연합", "#FF2BD6"), (2, "류해온", "심해행성연맹", "#00E5FF"), (3, "오로라", "무소속", "#A6FF00")]
STATIONS = [("M", "M 방송국", "STATION_KEY_M"), ("K", "K 방송국", "STATION_KEY_K")]


def run(reset: bool = False, quiet: bool = False) -> dict:
    init_db()
    new_keys = {}
    with SessionLocal() as db:
        if reset:
            for t in (CountCandidate, CountRegion, SimState):
                db.query(t).delete()
        el = db.get(Election, ELECTION["election_id"]) or Election(**ELECTION, total_electors=0)
        el.name, el.election_date = ELECTION["name"], ELECTION["election_date"]
        el.total_electors = sum(r[2] for r in REGIONS)
        el.status = el.status or "READY"
        db.merge(el)
        for i, (code, name, electors) in enumerate(REGIONS, 1):
            db.merge(Region(region_code=code, election_id=el.election_id, name=name, electors=electors, sort_order=i))
        for cid, name, party, color in CANDIDATES:
            db.merge(Candidate(candidate_id=cid, election_id=el.election_id, ballot_no=cid, name=name, party=party, color=color))
        for code, name, env in STATIONS:
            key = getattr(config, env)
            row = db.get(StationKey, code)
            if key:                      # .env에 적힌 키 사용
                db.merge(StationKey(station_code=code, station_name=name, api_key_hash=hash_key(key), active=True,
                                    last_called_at=row.last_called_at if row else None))
            elif row is None:            # 키가 없으면 새로 만들어 한 번만 보여 줌
                key = secrets.token_urlsafe(24)
                new_keys[code] = key
                db.add(StationKey(station_code=code, station_name=name, api_key_hash=hash_key(key), active=True))
        db.commit()
    if not quiet:
        print("초기 데이터 완료: 선거 1 · 구 5 · 후보 3 · 방송국 키 2")
        for code, key in new_keys.items():
            print(f"  ★ {code} 방송국 API 키 (지금만 보임, station-onair의 .env NEC_API_KEY에 적기): {key}")
    return new_keys


if __name__ == "__main__":
    run(reset="--reset" in sys.argv)
