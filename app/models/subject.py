"""数据模型 - 受试者"""

import uuid
from datetime import date, datetime

from sqlalchemy import String, Date, DateTime, Enum as SAEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

import enum


class SubjectStatus(str, enum.Enum):
    ACTIVE = "active"          # 在组
    INACTIVE = "inactive"      # 暂停
    COMPLETED = "completed"    # 完成
    DROPPED = "dropped"        # 脱落


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    subject_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True, comment="受试者编号"
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="姓名"
    )
    gender: Mapped[str] = mapped_column(
        String(1), nullable=False, comment="性别 (M/F)"
    )
    birth_date: Mapped[date] = mapped_column(
        Date, nullable=False, comment="出生日期"
    )
    enrollment_date: Mapped[date] = mapped_column(
        Date, nullable=False, comment="入组日期"
    )
    status: Mapped[SubjectStatus] = mapped_column(
        SAEnum(SubjectStatus), default=SubjectStatus.ACTIVE, nullable=False, comment="受试者状态"
    )
    contact_phone: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="联系电话"
    )
    notes: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="备注"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )

    # 关联
    visits: Mapped[list["Visit"]] = relationship(
        "Visit", back_populates="subject", cascade="all, delete-orphan"
    )
    reminders: Mapped[list["Reminder"]] = relationship(
        "Reminder", back_populates="subject", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Subject(id={self.id}, number={self.subject_number}, name={self.name})>"



