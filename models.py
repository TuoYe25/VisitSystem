"""
数据库模型定义
"""
import hashlib
import secrets
from datetime import date, datetime
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, Integer, String, Date, DateTime, ForeignKey, Enum, Boolean, create_engine, Table
)
from sqlalchemy.orm import DeclarativeBase, relationship, Session


class Base(DeclarativeBase):
    pass


class SubjectStatus(str, PyEnum):
    ACTIVE = "active"       # 在组
    DROPOUT = "dropout"     # 脱落
    COMPLETED = "completed" # 完成


class UserRole(str, PyEnum):
    PI = "PI"    # 主要研究者，可查看全部
    CRC = "CRC"  # 临床研究协调员，只能看自己负责的受试者


class VisitType(str, PyEnum):
    SCREENING = "screening"  # 筛选期 D0
    TREATMENT = "treatment"  # 治疗期 C1-C6
    FOLLOWUP = "followup"    # 随访期 F1-F3


class VisitStatus(str, PyEnum):
    PENDING = "pending"           # 待访视
    COMPLETED = "completed"       # 已完成
    DEVIATION = "deviation"       # 方案偏离（超窗）
    SKIPPED = "skipped"           # 已跳过（受试者脱落/退出）


class Subject(Base):
    """受试者"""
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_code = Column(String(20), unique=True, nullable=False, comment="受试者编号")
    full_name = Column(String(20), nullable=False, comment="完整姓名")
    name_abbr = Column(String(10), nullable=False, comment="姓名拼音首字母")
    enrollment_date = Column(Date, nullable=False, comment="入组日期 D0")
    status = Column(Enum(SubjectStatus), default=SubjectStatus.ACTIVE, comment="当前状态")
    dropout_date = Column(Date, nullable=True, comment="脱落/退出日期")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    visits = relationship("Visit", back_populates="subject", order_by="Visit.visit_order")
    assigned_crcs = relationship("User", secondary="crc_subjects", back_populates="subjects")


# CRC-受试者 关联表
crc_subjects = Table(
    "crc_subjects", Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("subject_id", Integer, ForeignKey("subjects.id"), primary_key=True),
)


class User(Base):
    """系统用户"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    salt = Column(String(64), nullable=False)
    display_name = Column(String(50), nullable=False, comment="显示名称")
    role = Column(Enum(UserRole), nullable=False, comment="角色: PI / CRC")
    created_at = Column(DateTime, default=datetime.now)

    subjects = relationship("Subject", secondary="crc_subjects", back_populates="assigned_crcs")

    @staticmethod
    def hash_password(password: str, salt: str = None) -> tuple[str, str]:
        """哈希密码，返回 (hash, salt)"""
        if salt is None:
            salt = secrets.token_hex(32)
        h = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return h.hex(), salt

    def verify_password(self, password: str) -> bool:
        """验证密码"""
        h, _ = self.hash_password(password, self.salt)
        return h == self.password_hash


class Visit(Base):
    """访视记录"""
    __tablename__ = "visits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)

    visit_order = Column(Integer, nullable=False, comment="访视序号 0=筛选 1-6=治疗 7-9=随访")
    visit_label = Column(String(20), nullable=False, comment="访视标签: 筛选期/C1/C2/.../F1/F2/F3")
    visit_type = Column(Enum(VisitType), nullable=False, comment="访视类型")

    planned_date = Column(Date, nullable=False, comment="计划访视日期")
    window_start = Column(Date, nullable=False, comment="窗口开始日期")
    window_end = Column(Date, nullable=False, comment="窗口结束日期")

    actual_date = Column(Date, nullable=True, comment="实际访视日期")
    status = Column(Enum(VisitStatus), default=VisitStatus.PENDING, comment="访视状态")

    is_critical = Column(Boolean, default=True, comment="是否为关键节点")
    window_days = Column(Integer, default=3, comment="窗口天数(±)")

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    subject = relationship("Subject", back_populates="visits")


# 数据库引擎
DATABASE_URL = "sqlite:///./visitsystem.db"
engine = create_engine(DATABASE_URL, echo=False)


def init_db():
    """初始化数据库表"""
    Base.metadata.create_all(engine)


def get_session() -> Session:
    return Session(engine)