"""访视记录模型"""

from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class VisitStatus(str, enum.Enum):
    PENDING = "待访视"
    COMPLETED = "已完成"
    MISSED = "超窗/漏访"
    RESCHEDULED = "已改期"


class Visit(Base):
    __tablename__ = "visits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, index=True, comment="受试者ID")
    visit_number = Column(Integer, nullable=False, comment="访视序号（第几次随访）")
    planned_date = Column(Date, nullable=False, comment="计划访视日期")
    window_start = Column(Date, nullable=False, comment="窗口起始日期")
    window_end = Column(Date, nullable=False, comment="窗口结束日期")
    actual_date = Column(Date, nullable=True, comment="实际访视日期")
    status = Column(
        String(20),
        default=VisitStatus.PENDING.value,
        nullable=False,
        comment="访视状态",
    )
    notes = Column(String(500), nullable=True, comment="备注")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    subject = relationship("Subject", backref="visits")

    @property
    def is_overdue(self) -> bool:
        """是否已超窗（已过窗口结束日期但未完成）"""
        if self.status == VisitStatus.COMPLETED.value:
            return False
        return date.today() > self.window_end

    def __repr__(self):
        return f"<Visit #{self.visit_number} for Subject {self.subject_id}>"
