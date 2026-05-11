from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import llm, models, schemas
from ..database import get_db

router = APIRouter(prefix="/memory", tags=["memory"])


# ---------- helpers ----------

def _serialize(mem: models.Memory) -> schemas.MemoryOut:
    return schemas.MemoryOut(
        id=mem.id,
        author_handle=mem.author_handle,
        text=mem.text,
        themes=mem.themes,
        emotional_register=mem.emotional_register,
        lesson=mem.lesson,
        one_line_essence=mem.one_line_essence,
        created_at=mem.created_at,
    )


def _find_echo_for(db: Session, viewer: models.Memory) -> tuple[models.Memory, list[str]] | None:
    """Pick the most resonant other memory by theme overlap.

    Deterministic ordering (oldest first) so the same input gives the same echo.
    """
    candidates = (
        db.query(models.Memory)
        .filter(models.Memory.id != viewer.id)
        .filter(models.Memory.author_handle != viewer.author_handle)
        .order_by(models.Memory.created_at.asc())
        .all()
    )
    if not candidates:
        return None

    viewer_themes = {t.lower() for t in viewer.themes}
    best_score = -1
    best: tuple[models.Memory, list[str]] | None = None
    for c in candidates:
        cand_themes = {t.lower() for t in c.themes}
        overlap = sorted(viewer_themes & cand_themes)
        score = len(overlap) + (1 if c.emotional_register == viewer.emotional_register else 0)
        if score > best_score:
            best_score = score
            best = (c, overlap)
    return best


def _get_reaction(db: Session, from_id: str, to_id: str) -> models.Reaction | None:
    return (
        db.query(models.Reaction)
        .filter(models.Reaction.from_memory_id == from_id)
        .filter(models.Reaction.to_memory_id == to_id)
        .one_or_none()
    )


def _state_response(db: Session, mem: models.Memory) -> schemas.MemoryStateResponse:
    echo: schemas.EchoOut | None = None
    if mem.echo_memory_id:
        echo_mem = db.get(models.Memory, mem.echo_memory_id)
        if echo_mem:
            mine = _get_reaction(db, mem.id, echo_mem.id)
            theirs = _get_reaction(db, echo_mem.id, mem.id)
            mutual = bool(
                mine and mine.kind == "yes" and theirs and theirs.kind == "yes"
            )
            echo = schemas.EchoOut(
                memory=_serialize(echo_mem),
                resonance_reason=mem.echo_resonance_reason or "",
                overlap_themes=mem.echo_overlap_themes,
                my_reaction=mine.kind if mine else None,  # type: ignore[arg-type]
                their_reaction=theirs.kind if theirs else None,  # type: ignore[arg-type]
                mutual=mutual,
            )
    return schemas.MemoryStateResponse(you=_serialize(mem), echo=echo)


# ---------- endpoints ----------

@router.post("", response_model=schemas.MemoryStateResponse)
def create_memory(
    body: schemas.MemoryCreateRequest, db: Session = Depends(get_db)
) -> schemas.MemoryStateResponse:
    # 1. Analyze with Claude
    try:
        analysis = llm.analyze_memory(body.text)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=f"LLM analyze error: {exc}") from exc

    # 2. Persist (without echo info yet)
    mem = models.Memory(
        author_handle=body.author_handle.strip(),
        text=body.text.strip(),
        emotional_register=analysis["emotional_register"],
        lesson=analysis["lesson"],
        one_line_essence=analysis["one_line_essence"],
    )
    mem.themes = analysis["themes"]
    db.add(mem)
    db.flush()  # get mem.id without committing

    # 3. Find + cache the echo (and the resonance reason)
    pick = _find_echo_for(db, mem)
    if pick is not None:
        candidate, overlap = pick
        viewer_dict = {
            "themes": mem.themes,
            "emotional_register": mem.emotional_register,
            "lesson": mem.lesson,
            "one_line_essence": mem.one_line_essence,
        }
        candidate_dict = {
            "themes": candidate.themes,
            "emotional_register": candidate.emotional_register,
            "lesson": candidate.lesson,
            "one_line_essence": candidate.one_line_essence,
        }
        reason = llm.resonance_reason(viewer_dict, candidate_dict)
        mem.echo_memory_id = candidate.id
        mem.echo_resonance_reason = reason
        mem.echo_overlap_themes = overlap

    db.commit()
    db.refresh(mem)
    return _state_response(db, mem)


@router.get("/{memory_id}", response_model=schemas.MemoryStateResponse)
def get_memory(memory_id: str, db: Session = Depends(get_db)) -> schemas.MemoryStateResponse:
    mem = db.get(models.Memory, memory_id)
    if not mem:
        raise HTTPException(status_code=404, detail="memory not found")
    return _state_response(db, mem)


@router.post("/{from_id}/react", response_model=schemas.MemoryStateResponse)
def react(
    from_id: str, body: schemas.ReactionRequest, db: Session = Depends(get_db)
) -> schemas.MemoryStateResponse:
    mem = db.get(models.Memory, from_id)
    if not mem:
        raise HTTPException(status_code=404, detail="memory not found")
    target = db.get(models.Memory, body.to_memory_id)
    if not target:
        raise HTTPException(status_code=404, detail="target memory not found")
    if mem.id == target.id:
        raise HTTPException(status_code=400, detail="cannot react to your own memory")

    existing = _get_reaction(db, mem.id, target.id)
    if existing is not None:
        raise HTTPException(status_code=409, detail="already reacted — decisions are one-shot")

    db.add(models.Reaction(from_memory_id=mem.id, to_memory_id=target.id, kind=body.kind))
    db.commit()
    db.refresh(mem)
    return _state_response(db, mem)
