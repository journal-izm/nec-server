"""실행 설정 — .env 파일과 환경 변수에서 읽음 (08 개발환경 '실행 설정')."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """python-dotenv 없이 .env를 읽는 아주 작은 함수. 이미 있는 환경 변수는 덮어쓰지 않음."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.split(" #", 1)[0].strip().strip('"').strip("'")         # 값 뒤 주석은 버림
        os.environ.setdefault(k.strip(), v)


_load_dotenv(BASE_DIR / ".env")


def _env(name: str, default: str = "") -> str:
    """환경 변수 읽기. .env에 'NAME=' 처럼 값이 비어 있으면 기본값을 씀."""
    v = os.getenv(name)
    return v.strip() if v and v.strip() else default


def _bool(v: str) -> bool:
    return str(v).lower() in ("1", "true", "yes", "on")


NEC_DB_URL = _env("NEC_DB_URL", f"sqlite:///{(BASE_DIR / 'nec.db').as_posix()}")
ADMIN_KEY = _env("ADMIN_KEY", "")
SCENARIO = _env("SCENARIO", "hanbit_2026.csv")
SCENARIO_PATH = BASE_DIR / "scenario" / SCENARIO
ELECTION_ID = _env("ELECTION_ID", "HANBIT-2026")
DEMO_MODE = _bool(_env("DEMO_MODE", "false"))
DEMO_RESTART_SEC = int(_env("DEMO_RESTART_SEC", "30"))   # 시연 모드: 개표가 끝나고 다시 시작하기까지
TICK_SEC = float(_env("SIM_TICK_SEC", "0.5"))            # 시뮬레이터가 시계를 확인하는 간격
# 방송국 API 키 (seed.py가 해시로 저장). 비워 두면 seed가 새 키를 만들어 화면에 한 번 보여 줌
STATION_KEY_M = _env("STATION_KEY_M", "")
STATION_KEY_K = _env("STATION_KEY_K", "")


def require(*names: str) -> None:
    """꼭 필요한 값이 비어 있으면 무엇이 없는지 알려 주고 멈춤 (TC-ENV-02)."""
    missing = [n for n in names if not os.getenv(n)]
    if missing:
        raise SystemExit(f"[설정 오류] .env에 다음 값이 없습니다: {', '.join(missing)}  (.env.example 참고)")


if "://" not in NEC_DB_URL:
    raise SystemExit(f"[설정 오류] DB 주소가 이상합니다: {NEC_DB_URL!r} — .env의 DB 주소 칸을 비우거나 sqlite:///파일이름.db 형식으로 적으세요")
