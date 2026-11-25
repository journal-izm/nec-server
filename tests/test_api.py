"""선관위 API 테스트 — 1차 확인 테스트케이스 번호와 같은 이름 (FastAPI·httpx 필요)."""
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

import seed  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Candidate, CountCandidate, CountRegion, Region, StationKey  # noqa: E402
from app.simulator import sim  # noqa: E402

EID = "HANBIT-2026"
M = {"X-API-KEY": "test-key-m"}
ADMIN = {"X-ADMIN-KEY": "test-admin"}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        seed.run(reset=True, quiet=True)
        yield c


def publish(seconds: float):
    """시뮬레이터를 시작해 1배속 기준 seconds초만큼 진행."""
    with SessionLocal() as db:
        sim.start(db)
        sim.step(db, seconds)


def test_tc_db_01_seed(client):
    with SessionLocal() as db:
        assert [r.region_code for r in db.query(Region).order_by(Region.sort_order)] == ["STAR", "DEEP", "DUNE", "NEBULA", "ORBIT"]
        assert [c.name for c in db.query(Candidate).order_by(Candidate.ballot_no)] == ["윤별하", "류해온", "오로라"]
        assert db.query(StationKey).count() == 2


def test_tc_rq_05_keys_are_hashed(client):
    with SessionLocal() as db:
        for s in db.query(StationKey):
            assert s.api_key_hash not in ("test-key-m", "test-key-k") and len(s.api_key_hash) == 64


def test_tc_api_01_station_key(client):
    url = f"/nec/v1/elections/{EID}"
    assert client.get(url).status_code == 401
    assert client.get(url, headers={"X-API-KEY": "wrong"}).status_code == 401
    assert client.get(url, headers=M).status_code == 200


def test_tc_api_02_election_contract(client):
    d = client.get(f"/nec/v1/elections/{EID}", headers=M).json()
    assert set(d) >= {"election", "regions", "candidates"}
    assert len(d["regions"]) == 5 and len(d["candidates"]) == 3
    assert set(d["regions"][0]) >= {"code", "name", "electors"}
    assert set(d["candidates"][0]) >= {"id", "ballot_no", "name", "color"}
    assert d["candidates"][0]["color"] == "#FF2BD6"


def test_tc_api_04_sim_control(client):
    assert client.post("/nec/v1/sim/control", json={"action": "start"}).status_code == 403
    r = client.post("/nec/v1/sim/control", json={"action": "reset", "speed": 5}, headers=ADMIN).json()
    assert r["status"] == "READY" and r["current_seq"] == 0 and r["speed"] == 5
    assert client.post("/nec/v1/sim/control", json={"action": "start"}, headers=ADMIN).json()["status"] == "RUNNING"
    assert client.post("/nec/v1/sim/control", json={"action": "pause"}, headers=ADMIN).json()["status"] == "PAUSED"
    assert client.post("/nec/v1/sim/control", json={"action": "speed", "speed": 3}, headers=ADMIN).status_code == 422
    assert client.get("/nec/v1/sim/status", headers=ADMIN).json()["status"] == "PAUSED"
    client.post("/nec/v1/sim/control", json={"action": "reset", "speed": 1}, headers=ADMIN)


def test_tc_fn_01_since_seq(client):
    publish(120)
    url = f"/nec/v1/elections/{EID}/results"
    d = client.get(url, params={"since_seq": 0}, headers=M).json()
    assert d["last_seq"] >= 10
    d2 = client.get(url, params={"since_seq": 10}, headers=M).json()
    assert d2["regions"] and all(r["seq"] > 10 for r in d2["regions"])
    d3 = client.get(url, params={"since_seq": d["last_seq"]}, headers=M).json()
    assert d3["regions"] == []


def test_tc_api_03_results_contract(client):
    d = client.get(f"/nec/v1/elections/{EID}/results", params={"since_seq": 0}, headers=M).json()
    assert set(d) >= {"last_seq", "status", "regions"}
    r = d["regions"][0]
    assert set(r) >= {"seq", "code", "counted_rate", "votes"}
    assert 0 <= r["counted_rate"] <= 100
    assert set(r["votes"]) == {"1", "2", "3"}


def test_tc_db_02_snapshots(client):
    publish(10_000)   # 끝까지
    with SessionLocal() as db:
        seqs = [c.seq for c in db.query(CountRegion).order_by(CountRegion.seq)]
        assert seqs == list(range(1, len(seqs) + 1))
        assert db.query(CountCandidate).count() == len(seqs) * 3
        assert sim.state(db).status == "DONE"


def test_tc_sc_02_reset_replays_same(client):
    def snapshot():
        with SessionLocal() as db:
            return [(c.seq, c.region_code, c.counted_votes) for c in db.query(CountRegion).order_by(CountRegion.seq)]
    first = snapshot()
    client.post("/nec/v1/sim/control", json={"action": "reset"}, headers=ADMIN)
    assert snapshot() == []
    publish(10_000)
    assert snapshot() == first
