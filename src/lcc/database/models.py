# Copyright 2025 Ajay Pundhir
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
SQLAlchemy models for the persistence layer.
"""
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    project_name: Mapped[str] = mapped_column(String, index=True)
    status: Mapped[str] = mapped_column(String, default="queued")  # queued, running, complete, failed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), onupdate=lambda: datetime.now(UTC).replace(tzinfo=None))
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Summary statistics
    components_count: Mapped[int] = mapped_column(default=0)
    violations_count: Mapped[int] = mapped_column(default=0)
    warnings_count: Mapped[int] = mapped_column(default=0)

    # JSON blobs for detailed report and context
    context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    report: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Relationships
    components: Mapped[list["Component"]] = relationship(back_populates="scan", cascade="all, delete-orphan")


class Component(Base):
    __tablename__ = "components"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    scan_id: Mapped[str] = mapped_column(ForeignKey("scans.id"))

    type: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String, index=True)
    version: Mapped[str] = mapped_column(String)
    purl: Mapped[str | None] = mapped_column(String, nullable=True)

    license_expression: Mapped[str | None] = mapped_column(String, nullable=True)
    license_confidence: Mapped[float] = mapped_column(Float, default=0.0)

    # Policy evaluation result for this component
    policy_status: Mapped[str | None] = mapped_column(String, nullable=True)  # pass, warning, violation
    policy_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # JSON blobs for metadata and evidence
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    scan: Mapped["Scan"] = relationship(back_populates="components")
