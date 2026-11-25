"""선관위 서버 (포트 8000)

uvicorn app.main:app --port 8000
  - 관리 화면: http://localhost:8000/admin   (SCR-02-01)
  - API 문서: http://localhost:8000/docs
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from . import config
from .db import init_db
from .routers import elections, sim as sim_router
from .simulator import sim

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if config.DEMO_MODE:          # 클라우드 시연 모드: 켜질 때 초기 데이터부터 (REQ-02-05)
        import seed
        seed.run(quiet=True)
    sim.launch()
    yield


app = FastAPI(title="nec-server · 선관위 개표 데이터", version="1.0", lifespan=lifespan,
              description="2026 한빛시장 모의선거(가상) 개표 데이터와 시뮬레이터. 방송국은 X-API-KEY로 호출합니다.")
app.include_router(elections.router)
app.include_router(sim_router.router)


@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse("/admin")


@app.get("/admin", response_class=HTMLResponse, include_in_schema=False)
def admin(request: Request):
    """SCR-02-01 선관위 개표 시뮬레이터 화면. 관리 키는 화면에서 입력 (브라우저 탭에만 보관)."""
    return templates.TemplateResponse(request, "admin.html", {"election_id": config.ELECTION_ID, "demo": config.DEMO_MODE})


@app.get("/health", include_in_schema=False)
def health():
    return {"ok": True}
