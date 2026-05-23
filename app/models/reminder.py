"""数据模型 - 随访提醒"""

import uuid
from datetime import date, datetime

from sqlalchemy import String, Date, DateTime, ForeignKey, Enum as SAEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

import enum


class ReminderMethod(str, enum.Enum):
    SMS = "sms"
    EMAIL = "email"
    PHONE = "phone"
    WECHAT = "wechat"


class ReminderStatus(str, enum.Enum):
    PENDING = "pending"    # 待发送
    SENT = "sent"          # 已发送
    FAILED = "failed"      # 发送失败
    CANCELLED = "cancelled"  # 已取消


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    visit_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("visits.id", ondelete="CASCADE"), nullable=False, index=True, comment="访视记录ID"
    )
    subject_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True, comment="受试者ID"
    )
    remind_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="提醒时间"
    )
    method: Mapped[ReminderMethod] = mapped_column(
        SAEnum(ReminderMethod), nullable=False, comment="提醒方式"
    )
    status: Mapped[ReminderStatus] = mapped_column(
        SAEnum(ReminderStatus), default=ReminderStatus.PENDING, nullable=False, comment="发送状态"
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="实际发送时间"
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
    visit: Mapped["Visit"] = relationship("Visit", back_populates="reminders")
    subject: Mapped["Subject"] = relationship("Subject", back_populates="reminders")

    def __repr__(self) -> str:
        return f"<Reminder(id={self.id}, visit={self.visit_id}, method={self.method}, status={self.status})>"



