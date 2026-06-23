from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def new_uuid() -> str:
    return str(uuid4())


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    platform: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    stage: Mapped[str | None] = mapped_column(String(64), default="created")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    voice_id: Mapped[str | None] = mapped_column(String(128))
    burn_subtitle: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    mix_original_audio: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    task_id: Mapped[str | None] = mapped_column(String(64))
    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    storage_dir: Mapped[str | None] = mapped_column(Text)
    input_video_path: Mapped[str | None] = mapped_column(Text)
    audio_path: Mapped[str | None] = mapped_column(Text)
    transcript_zh_path: Mapped[str | None] = mapped_column(Text)
    transcript_vi_path: Mapped[str | None] = mapped_column(Text)
    subtitle_path: Mapped[str | None] = mapped_column(Text)
    tts_audio_path: Mapped[str | None] = mapped_column(Text)
    output_video_path: Mapped[str | None] = mapped_column(Text)
    final_config_json: Mapped[dict | None] = mapped_column(JSON)
    result_url: Mapped[str | None] = mapped_column(Text)
    subtitle_url: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    logs: Mapped[list["JobLog"]] = relationship(back_populates="job")
    edits: Mapped[list["JobEdit"]] = relationship(back_populates="job")


class JobLog(Base):
    __tablename__ = "job_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"), nullable=False)
    level: Mapped[str] = mapped_column(String(16), nullable=False)
    stage: Mapped[str | None] = mapped_column(String(64))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job: Mapped[Job] = relationship(back_populates="logs")


class JobEdit(Base):
    __tablename__ = "job_edits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"), nullable=False)
    version_number: Mapped[int | None] = mapped_column(Integer)
    tool_summary: Mapped[str] = mapped_column(String(128), nullable=False)
    is_draft: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    config_json: Mapped[dict | None] = mapped_column(JSON)
    output_video_path: Mapped[str | None] = mapped_column(Text)
    result_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    job: Mapped[Job] = relationship(back_populates="edits")
