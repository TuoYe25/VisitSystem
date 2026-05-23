"""随访提醒模型"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class ReminderMethod(str, enum.Enum):
    SMS = "短信"
    PHONE = "电话"
    WECHAT = "微信"
    EMAIL = "邮件"


class ReminderStatus(str, enum.Enum):
    PENDING = "待发送"
    SENT = "已发送"
    FAILED = "发送失败"


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    visit_id = Column(Integer, ForeignKey("visits.id"), nullable=False, comment="访视记录ID")
    remind_date = Column(DateTime, nullable=False, comment="计划提醒时间")
    method = Column(
        String(20),
        default=ReminderMethod.SMS.value,
        nullable=False,
        comment="提醒方式",
    )
    status = Column(
        String(20),
        default=ReminderStatus.PENDING.value,
        nullable=False,
        comment="发送状态",
    )
    sent_at = Column(DateTime, nullable=True, comment="实际发送时间")
    content = Column(String(500), nullable=True, comment="提醒内容")
    created_at = Column(DateTime, default=datetime.utcnow)

    visit = relationship("Visit", backref="reminders")

    def __repr__(self):
        return f"<Reminder for Visit {self.visit_id} at {self.remind_date}>"
