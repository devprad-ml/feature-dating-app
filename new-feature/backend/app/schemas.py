from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ReactionKind = Literal["yes", "no"]


class MemoryCreateRequest(BaseModel):
    author_handle: str = Field(min_length=1, max_length=64)
    text: str = Field(min_length=80, max_length=1500)


class MemoryOut(BaseModel):
    id: str
    author_handle: str
    text: str
    themes: list[str]
    emotional_register: str
    lesson: str
    one_line_essence: str
    created_at: datetime


class EchoOut(BaseModel):
    """The other memory paired with the viewer, plus reaction state for both sides."""
    memory: MemoryOut
    resonance_reason: str
    overlap_themes: list[str]
    my_reaction: ReactionKind | None
    their_reaction: ReactionKind | None
    mutual: bool


class MemoryStateResponse(BaseModel):
    you: MemoryOut
    echo: EchoOut | None  # None only if the user is the very first memory in the system


class ReactionRequest(BaseModel):
    to_memory_id: str
    kind: ReactionKind
