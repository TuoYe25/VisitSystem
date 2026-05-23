"""受试者模型"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Date, DateTime, Enum as SAEnum
from app.database import Base
import enum


class SubjectGender(str, enum.Enum):
    MALE = "男"
    FEMALE = "女"


class SubjectStatus(str, enum.Enum):
    ACTIVE = "在组"
    COMPLETED = "已出组"
    DROPOUT = "脱落"
    SCREEN_FAILED = "筛选失败"


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_code = Column(String(50), unique=True, nullable=False, index=True, comment="受试者编号")
    name = Column(String(100), nullable=False, comment="姓名")
    gender = Column(SAEnum(SubjectGender), nullable=False, comment="性别")
    birth_date = Column(Date, nullable=False, comment="出生日期")
    enrollment_date = Column(Date, nullable=False, comment="入组日期")
    phone = Column(String(20), nullable=True, comment="联系电话")
    status = Column(
        SAEnum(SubjectStatus),
        default=SubjectStatus.ACTIVE,
        nullable=False,
        comment="状态",
    )
    notes = Column(String(500), nullable=True, comment="备注")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def __repr__(self):
        return f"<Subject {self.subject_code} - {self.name}>"
