"""API-02-01 · API-02-02 — 방송국(M·K)이 부르는 API. 두 저장소의 약속이므로 형식을 바꾸지 않습니다."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..auth import station_auth
from ..db import get_db
from ..models import Candidate, CountCandidate, CountRegion, Election, Region

router = APIRouter(prefix="/nec/v1", tags=["방송국용 (X-API-KEY)"])


@router.get("/elections/{election_id}", summary="API-02-01 선거 기본정보")
def election_info(election_id: str, db: Session = Depends(get_db), _=Depends(station_auth)):
    el = db.get(Election, election_id)
    if not el:
        raise HTTPException(404, "선거를 찾을 수 없습니다")
    regions = db.query(Region).filter_by(election_id=election_id).order_by(Region.sort_order).all()
    cands = db.query(Candidate).filter_by(election_id=election_id).order_by(Candidate.ballot_no).all()
    return {
        "election": {"id": el.election_id, "name": el.name, "date": el.election_date.isoformat(),
                     "total_electors": el.total_electors, "status": el.status},
        "regions": [{"code": r.region_code, "name": r.name, "electors": r.electors, "sort_order": r.sort_order} for r in regions],
        "candidates": [{"id": c.candidate_id, "ballot_no": c.ballot_no, "name": c.name, "party": c.party, "color": c.color}
                       for c in cands],
    }


@router.get("/elections/{election_id}/results", summary="API-02-02 개표 집계 변경분")
def results(election_id: str, since_seq: int = Query(0, ge=0), limit: int = Query(500, ge=1, le=2000),
            db: Session = Depends(get_db), _=Depends(station_auth)):
    """since_seq 이후에 발표된 지역별 집계만 돌려줌 (FN-02-02). 처음에는 since_seq=0."""
    el = db.get(Election, election_id)
    if not el:
        raise HTTPException(404, "선거를 찾을 수 없습니다")
    rows = (db.query(CountRegion).filter(CountRegion.seq > since_seq)
            .order_by(CountRegion.seq).limit(limit).all())
    seqs = [r.seq for r in rows]
    votes: dict[int, dict[str, int]] = {}
    if seqs:
        for cc in db.query(CountCandidate).filter(CountCandidate.seq.in_(seqs)).all():
            votes.setdefault(cc.seq, {})[str(cc.candidate_id)] = cc.votes
    last_seq = db.query(CountRegion.seq).order_by(CountRegion.seq.desc()).limit(1).scalar() or 0
    return {
        "last_seq": last_seq,
        "status": el.status,
        "has_more": bool(rows) and rows[-1].seq < last_seq,
        "regions": [{"seq": r.seq, "code": r.region_code, "counted_rate": r.counted_rate,
                     "counted_votes": r.counted_votes, "invalid_votes": r.invalid_votes,
                     "votes": votes.get(r.seq, {}), "created_at": r.created_at.strftime("%H:%M:%S")} for r in rows],
    }
