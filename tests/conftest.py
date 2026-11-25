"""API 테스트 준비 — 임시 DB와 테스트용 키로 앱을 띄움."""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_tmp = tempfile.mkdtemp()
os.environ["NEC_DB_URL"] = f"sqlite:///{_tmp}/test_nec.db"
os.environ["ADMIN_KEY"] = "test-admin"
os.environ["STATION_KEY_M"] = "test-key-m"
os.environ["STATION_KEY_K"] = "test-key-k"
os.environ["DEMO_MODE"] = "false"
os.environ["SIM_TICK_SEC"] = "3600"   # 백그라운드 루프는 테스트 동안 사실상 멈춤 (테스트가 직접 step)
