"""가상 개표 시나리오 만들기 → scenario/hanbit_2026.csv

python tools/make_scenario.py

- 1배속 기준 약 10분(600초) 안에 5개 구 개표가 모두 끝나도록 설계
- 초반에는 기호 2 류해온이 앞서다가, 개표율 70% 안팎에서 기호 1 윤별하가 역전
- 개표율 95% 이상에서 당선 유력·확실·확정이 이어서 나옴 (방송 LIVE 구간 10분 무렵)
- 난수 씨앗(2026)이 고정이라 언제 다시 만들어도 같은 파일이 나옴 (NFR-04)
"""
import csv
import random
from pathlib import Path

SEED = 2026
TURNOUT = 0.65          # 투표율
INVALID = 0.012         # 무효표 비율
EARLY_BIAS = 0.05       # 개표 초반 기호 2 쪽으로 기울어지는 정도 (개표가 끝날수록 0)

# 구 코드, 이름, 선거인 수, 개표 시작(초), 개표 끝(초), 최종 득표 비율(기호 1·2·3)
REGIONS = [
    ("STAR",   "별빛구", 82000,  5, 585, (0.52, 0.36, 0.12)),
    ("DEEP",   "심해구", 76000,  0, 560, (0.38, 0.50, 0.12)),
    ("DUNE",   "사막구", 64000, 25, 600, (0.40, 0.36, 0.24)),
    ("NEBULA", "성운구", 71000, 10, 590, (0.47, 0.41, 0.12)),
    ("ORBIT",  "궤도구", 58000,  0, 545, (0.44, 0.45, 0.11)),
]


def build():
    rnd = random.Random(SEED)
    rows = []
    for code, _name, electors, start, end, share in REGIONS:
        ballots = round(electors * TURNOUT)
        prev = None
        t = float(start)
        while True:
            frac = min(1.0, max(0.0, (t - start) / (end - start)) ** 0.9)
            if t >= end:
                frac = 1.0
            counted = round(ballots * frac)
            invalid = round(counted * INVALID)
            valid = counted - invalid
            bias = EARLY_BIAS * (1 - frac)
            s1 = share[0] - bias + rnd.uniform(-0.004, 0.004) * (1 - frac)
            s2 = share[1] + bias
            v1 = round(valid * s1)
            v2 = round(valid * s2)
            v3 = valid - v1 - v2
            if prev:  # 누적 득표는 줄지 않도록
                v1, v2, v3 = max(v1, prev[0]), max(v2, prev[1]), max(v3, prev[2])
                over = v1 + v2 + v3 - valid
                if over > 0:  # 반올림으로 넘친 만큼 개표수를 맞춤
                    counted += over
                    valid += over
            rate = 100.0 if frac >= 1.0 else round(min(99.99, counted / ballots * 100), 2)
            if counted > 0 and (prev is None or counted > prev[3]):
                rows.append([round(t, 1), code, counted, counted - (v1 + v2 + v3), rate, v1, v2, v3])
                prev = (v1, v2, v3, counted)
            if frac >= 1.0:
                break
            t = min(end, t + rnd.uniform(10, 20))
    rows.sort(key=lambda r: (r[0], r[1]))
    return rows


def main():
    out = Path(__file__).resolve().parent.parent / "scenario" / "hanbit_2026.csv"
    out.parent.mkdir(exist_ok=True)
    rows = build()
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["t_sec", "region_code", "counted_votes", "invalid_votes", "counted_rate", "v1", "v2", "v3"])
        w.writerows(rows)
    print(f"{out} — {len(rows)}줄")


if __name__ == "__main__":
    main()
