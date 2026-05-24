"""
Pydantic 数据模型（API 请求/响应）
"""
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


# ============ 受试者 ============

class SubjectCreate(BaseModel):
    subject_code: str = Field(..., min_length=1, max_length=20, description="受试者编号")
    full_name: str = Field(..., min_length=1, max_length=20, description="完整姓名")
    enrollment_date: date = Field(..., description="入组日期 D0")

    @field_validator('subject_code')
    def validate_subject_code(cls, v):
        import re
        if not re.match(r'^[A-Za-z0-9\-_]{2,20}$', v):
            raise ValueError('受试者编号格式不正确（仅允许字母、数字、连字符、下划线，2-20位）')
        return v

    @field_validator('full_name')
    def validate_full_name(cls, v):
        import re
        if not re.match(r'^[\u4e00-\u9fff]{2,4}$', v):
            raise ValueError('姓名格式不正确（仅允许中文，2-4字）')
        return v


class SubjectUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=20)
    enrollment_date: Optional[date] = None
    status: Optional[str] = Field(None, pattern="^(active|dropout|completed)$")
    dropout_date: Optional[date] = None
    crc_id: Optional[int] = Field(None, description="负责人CRC的ID，None表示不修改")


class SubjectResponse(BaseModel):
    id: int
    subject_code: str
    full_name: str
    name_abbr: str
    enrollment_date: date
    status: str
    dropout_date: Optional[date]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ 访视 ============

class VisitResponse(BaseModel):
    id: int
    subject_id: int
    visit_order: int
    visit_label: str
    visit_type: str
    planned_date: date
    window_start: date
    window_end: date
    actual_date: Optional[date]
    status: str
    is_critical: bool
    window_days: int

    # 计算字段
    days_remaining: Optional[int] = None
    window_status: Optional[str] = None  # normal / warning / overdue

    class Config:
        from_attributes = True


class VisitActualUpdate(BaseModel):
    """回填实际访视日期"""
    actual_date: date = Field(..., description="实际访视日期")


# ============ 每日提醒 ============

class DailyAlertItem(BaseModel):
    subject_id: int
    subject_code: str
    full_name: str
    name_abbr: str
    visit_order: int
    visit_label: str
    planned_date: date
    window_start: date
    window_end: date
    days_remaining: int
    window_status: str  # normal / warning / overdue
    is_critical: bool


class DailyAlertResponse(BaseModel):
    today: List[DailyAlertItem]
    tomorrow: List[DailyAlertItem]
    this_week: List[DailyAlertItem]


# ============ 方案偏离 ============

class DeviationItem(BaseModel):
    subject_id: int
    subject_code: str
    full_name: str
    name_abbr: str
    visit_label: str
    planned_date: date
    window_start: date
    window_end: date
    actual_date: Optional[date]
    deviation_type: str  # overdue / out_of_window / skipped


# ============ Excel 导入 ============

class ImportResult(BaseModel):
    total: int
    success: int
    failed: int
    errors: List[str]