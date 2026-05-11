from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


REACTION_KINDS = ("yes", "no")


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    author_handle: Mapped[str] = mapped_column(String(64))
    text: Mapped[str] = mapped_column(Text)

    # LLM-extracted analysis. themes is JSON-encoded for SQLite portability.
    themes_json: Mapped[str] = mapped_column(Text, default="[]")
    emotional_register: Mapped[str] = mapped_column(String(32), default="")
    lesson: Mapped[str] = mapped_column(Text, default="")
    one_line_essence: Mapped[str] = mapped_column(Text, default="")

    # Cached echo so reloads / polling don't re-trigger LLM calls. The echo for
    # a given memory is frozen at submission time; if a better candidate joins
    # the system later, the existing memory is unaffected.
    echo_memory_id: Mapped[str | None] = mapped_column(
        ForeignKey("memories.id"), nullable=True, default=None
    )
    echo_resonance_reason: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    echo_overlap_themes_json: Mapped[str] = mapped_column(Text, default="[]")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    @property
    def themes(self) -> list[str]:
        try:
            return json.loads(self.themes_json) or []
        except (ValueError, TypeError):
            return []

    @themes.setter
    def themes(self, values: list[str]) -> None:
        self.themes_json = json.dumps(list(values or []))

    @property
    def echo_overlap_themes(self) -> list[str]:
        try:
            return json.loads(self.echo_overlap_themes_json or "[]") or []
        except (ValueError, TypeError):
            return []

    @echo_overlap_themes.setter
    def echo_overlap_themes(self, values: list[str]) -> None:
        self.echo_overlap_themes_json = json.dumps(list(values or []))


class Reaction(Base):
    __tablename__ = "reactions"
    __table_args__ = (
        # one (from, to) reaction max — decisions are one-shot.
        UniqueConstraint("from_memory_id", "to_memory_id", name="uq_reaction"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    from_memory_id: Mapped[str] = mapped_column(ForeignKey("memories.id"), index=True)
    to_memory_id: Mapped[str] = mapped_column(ForeignKey("memories.id"), index=True)
    kind: Mapped[str] = mapped_column(String(8))  # "yes" | "no"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
