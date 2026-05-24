"""
访视日期计算引擎 —— 整个系统的核心业务逻辑
"""
from datetime import date, timedelta
from typing import List, Optional, Tuple

# ============ 访视方案定义 ============

# 每个访视节点的定义
VISIT_SCHEMA = [
    # (order, label, type, interval_days_from_prev, window_days, is_critical)
    (0,  "筛选期", "screening", 0,   0,  True),   # 入组当天 D0
    (1,  "C1",     "treatment", 21,  3,  True),
    (2,  "C2",     "treatment", 21,  3,  True),
    (3,  "C3",     "treatment", 21,  3,  True),
    (4,  "C4",     "treatment", 21,  3,  True),
    (5,  "C5",     "treatment", 21,  3,  True),
    (6,  "C6",     "treatment", 21,  3,  True),
    (7,  "F1",     "followup",  28,  7,  True),
    (8,  "F2",     "followup",  28,  7,  True),
    (9,  "F3",     "followup",  28,  7,  True),
]


def calculate_visits(
    enrollment_date: date,
    actual_dates: Optional[List[Tuple[int, date]]] = None
) -> List[dict]:
    """
    根据入组日期和实际访视日期，计算所有访视节点的计划日期和窗口期。

    核心规则：
    - 筛选期为 D0（入组当天），±0天窗口
    - 治疗期每21天一周期，±3天窗口
    - 随访期每28天一周期，±7天窗口
    - 若某个访视有实际发生日期，后续节点以实际日期重新推算

    Args:
        enrollment_date: 入组日期 D0
        actual_dates: 实际访视日期列表 [(visit_order, actual_date), ...]

    Returns:
        [{
            "visit_order": int,
            "visit_label": str,
            "visit_type": str,
            "planned_date": date,
            "window_start": date,
            "window_end": date,
            "is_critical": bool,
            "window_days": int,
        }, ...]
    """
    if actual_dates is None:
        actual_dates = []

    actual_map = {order: d for order, d in actual_dates}
    visits = []

    # 当前计算基准日期：上一节点的计划日期或实际日期
    current_base = enrollment_date

    for order, label, vtype, interval, window_days, is_critical in VISIT_SCHEMA:
        if order == 0:
            # 筛选期：就是入组当天
            planned = enrollment_date
        else:
            planned = current_base + timedelta(days=interval)

        # 检查是否有实际日期，若有则以实际日期为基准推算后续节点
        actual = actual_map.get(order)
        if actual is not None:
            # 后续节点的基准从实际日期开始算（计划日期保持协议推算值不变）
            current_base = actual
        else:
            current_base = planned

        visits.append({
            "visit_order": order,
            "visit_label": label,
            "visit_type": vtype,
            "planned_date": planned,
            "window_start": planned - timedelta(days=window_days),
            "window_end": planned + timedelta(days=window_days),
            "is_critical": is_critical,
            "window_days": window_days,
        })

    return visits


def check_window_status(planned_date: date, window_end: date, window_days: int) -> dict:
    """
    判断访视窗口状态。

    Returns:
        {
            "days_remaining": int,    # 剩余天数（负数表示已超）
            "status": str,            # "normal" / "warning" / "overdue"
        }
    """
    today = date.today()
    days_until_end = (window_end - today).days

    if days_until_end < 0:
        return {"days_remaining": days_until_end, "status": "overdue"}
    elif days_until_end <= 2:
        return {"days_remaining": days_until_end, "status": "warning"}
    else:
        return {"days_remaining": days_until_end, "status": "normal"}


def determine_deviation(
    planned_date: date,
    window_start: date,
    window_end: date,
    actual_date: Optional[date],
    subject_status: str
) -> Tuple[str, bool]:
    """
    判断访视是否构成方案偏离。

    - 受试者脱落/退出 → 跳过
    - 无实际日期 + 已超窗口 → 方案偏离
    - 实际日期在窗口外 → 方案偏离
    - 实际日期在窗口内 → 正常完成

    Returns:
        (visit_status, is_deviated)
    """
    if subject_status == "dropout":
        return "skipped", True

    if actual_date is None:
        # 未完成访视，检查是否已超窗
        if date.today() > window_end:
            return "deviation", True
        return "pending", False

    # 有实际日期，判断是否在窗口内
    if window_start <= actual_date <= window_end:
        return "completed", False
    else:
        return "deviation", True