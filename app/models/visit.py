"""数据模型 - 访视记录"""

import uuid
from datetime import date, datetime

from sqlalchemy import String, Date, DateTime, ForeignKey, Integer, Enum as SAEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.config import DEFAULT_WINDOW_DAYS

import enum


class VisitStatus(str, enum.Enum):
    SCHEDULED = "scheduled"        # 已排期
    COMPLETED = "completed"        # 已完成
    MISSED = "missed"              # 已错过
    OUT_OF_WINDOW = "out_of_window"  # 超窗完成


class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    subject_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True, comment="受试者ID"
    )
    visit_number: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="访视编号（第几次访视）"
    )
    planned_date: Mapped[date] = mapped_column(
        Date, nullable=False, comment="计划访视日期"
    )
    window_start: Mapped[date] = mapped_column(
        Date, nullable=False, comment="窗口开始日期"
    )
    window_end: Mapped[date] = mapped_column(
        Date, nullable=False, comment="窗口结束日期"
    )
    actual_date: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment="实际访视日期"
    )
    status: Mapped[VisitStatus] = mapped_column(
        SAEnum(VisitStatus), default=VisitStatus.SCHEDULED, nullable=False, comment="访视状态"
    )
    is_out_of_window: Mapped[bool] = mapped_column(
        default=False, comment="是否超窗"
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
    subject: Mapped["Subject"] = relationship("Subject", back_populates="visits")
    reminders: Mapped[list["Reminder"]] = relationship(
        "Reminder", back_populates="visit", cascade="all, delete-orphan"
    )

    @classmethod
    def calculate_window(cls, planned_date: date, window_days: int = DEFAULT_WINDOW_DAYS) -> tuple[date, date]:
        """计算访视窗口的起止日期"""
        from datetime import timedelta
        return (
            planned_date - timedelta(days=window_days),
            planned_date + timedelta(days=window_days),
        )

    def check_out_of_window(self) -> bool:
        """检查实际访视日期是否在窗口内"""
        if self.actual_date is None:
            return False
        return self.actual_date < self.window_start or self.actual_date > self.window_end

    def __repr__(self) -> str:
        return f"<Visit(id={self.id}, subject={self.subject_id}, number={self.visit_number}, status={self.status})>"



