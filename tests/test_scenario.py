"""시나리오 테스트 — FastAPI·DB 없이 돌아감 (python -m pytest tests/test_scenario.py)."""
import csv
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import scenario  # noqa: E402

CSV = ROOT / "scenario" / "hanbit_2026.csv"


def test_scenario_rules():
    """득표·개표율은 줄지 않고, 득표+무효 = 개표수, 모든 구가 100%로 끝남 (TC-DB-02의 원천 데이터)."""
    rows = scenario.load(CSV)
    assert len(rows) > 100
    assert scenario.check(rows) == []
    assert {r.region_code for r in rows} == {"STAR", "DEEP", "DUNE", "NEBULA", "ORBIT"}


def test_due_picks_rows_by_time():
    rows = scenario.load(CSV)
    first = scenario.due(rows, 0, 30)
    assert first and all(r.t_sec <= 30 for r in first)
    rest = scenario.due(rows, len(first), 10_000)
    assert len(first) + len(rest) == len(rows)
    assert scenario.due(rows, len(rows), 10_000) == []


def test_tc_sc_02_same_scenario_every_time():
    """TC-SC-02 / NFR-04: 시나리오를 다시 만들어도 같은 파일이 나와야 같은 리허설을 반복할 수 있음."""
    sys.path.insert(0, str(ROOT / "tools"))
    import make_scenario
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["t_sec", "region_code", "counted_votes", "invalid_votes", "counted_rate", "v1", "v2", "v3"])
    w.writerows(make_scenario.build())
    assert buf.getvalue().splitlines() == CSV.read_text(encoding="utf-8").splitlines()


def _story():
    """전체 1위가 바뀌는 시점과 당선 확정 시점 (방송 흐름 확인용)."""
    rows = scenario.load(CSV)
    ballots = {"STAR": 53300, "DEEP": 49400, "DUNE": 41600, "NEBULA": 46150, "ORBIT": 37700}
    last, lead, changes, elected = {}, None, [], None
    for r in rows:
        last[r.region_code] = r
        tot = {k: sum(x.votes[k] for x in last.values()) for k in (1, 2, 3)}
        counted = sum(x.counted_votes for x in last.values())
        est = sum(x.counted_votes / (x.counted_rate / 100) for x in last.values()) + \
            sum(v for k, v in ballots.items() if k not in last)
        order = sorted(tot, key=lambda k: -tot[k])
        if order[0] != lead:
            changes.append((r.t_sec, order[0]))
            lead = order[0]
        if elected is None and tot[order[0]] - tot[order[1]] > est - counted:
            elected = (r.t_sec, order[0])
    return changes, elected


def test_scenario_story_fits_broadcast():
    """초반 기호 2가 앞서다 기호 1이 역전, 당선 확정은 LIVE 11분(660초) 안 9~10분 무렵."""
    changes, elected = _story()
    assert changes[0][1] == 2 and changes[-1][1] == 1
    assert elected and elected[1] == 1 and 500 <= elected[0] <= 620
