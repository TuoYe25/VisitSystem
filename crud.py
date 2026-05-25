"""
数据库 CRUD 操作
"""
from datetime import date, datetime
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from pypinyin import lazy_pinyin

from models import (
    Subject, Visit, SubjectStatus, VisitStatus, VisitType,
    crc_subjects, init_db, get_session
)
from calculator import (
    calculate_visits, check_window_status, determine_deviation
)


def _get_pinyin_initials(name: str) -> str:
    """从中文姓名生成拼音首字母缩写，如 '欧阳修' → 'OYX'"""
    return ''.join(s[0].upper() for s in lazy_pinyin(name))


# ============ 受试者 CRUD ============

def create_subject(session: Session, subject_code: str, full_name: str,
                   enrollment_date: date, user_id: int = None) -> Subject:
    """创建受试者并自动生成访视计划，自动将当前用户设为负责人"""
    name_abbr = _get_pinyin_initials(full_name)
    subject = Subject(
        subject_code=subject_code,
        full_name=full_name,
        name_abbr=name_abbr,
        enrollment_date=enrollment_date,
    )
    session.add(subject)
    session.flush()  # 获取 subject.id

    # 自动将当前用户设为负责人
    if user_id:
        session.execute(
            crc_subjects.insert().values(user_id=user_id, subject_id=subject.id)
        )

    # 自动生成 10 个访视节点
    visits_data = calculate_visits(enrollment_date)
    for v in visits_data:
        visit = Visit(
            subject_id=subject.id,
            visit_order=v["visit_order"],
            visit_label=v["visit_label"],
            visit_type=VisitType(v["visit_type"]),
            planned_date=v["planned_date"],
            window_start=v["window_start"],
            window_end=v["window_end"],
            is_critical=v["is_critical"],
            window_days=v["window_days"],
        )
        session.add(visit)

    session.commit()
    session.refresh(subject)
    return subject


def get_subject(session: Session, subject_id: int) -> Optional[Subject]:
    return session.get(Subject, subject_id)


def get_subject_by_code(session: Session, code: str) -> Optional[Subject]:
    return session.query(Subject).filter(Subject.subject_code == code).first()


def get_all_subjects(session: Session, status: Optional[str] = None) -> List[Subject]:
    q = session.query(Subject)
    if status:
        q = q.filter(Subject.status == status)
    return q.order_by(Subject.subject_code).all()


def update_subject(session: Session, subject_id: int, **kwargs) -> Optional[Subject]:
    subject = session.get(Subject, subject_id)
    if not subject:
        return None

    crc_id = kwargs.pop("crc_id", None)

    for key, value in kwargs.items():
        if value is not None:
            if key == "status":
                value = SubjectStatus(value)
            setattr(subject, key, value)

    # 当完整姓名变更时，自动更新拼音首字母
    if kwargs.get("full_name"):
        subject.name_abbr = _get_pinyin_initials(subject.full_name)

    # 如果受试者脱落，将所有待访视节点标记为跳过
    if kwargs.get("status") == "dropout":
        session.query(Visit).filter(
            Visit.subject_id == subject_id,
            Visit.status == VisitStatus.PENDING
        ).update({Visit.status: VisitStatus.SKIPPED})

    # 更新负责人（CRC）
    if crc_id is not None:
        from crud_user import assign_subject_to_crc, unassign_subject_from_crc
        # 先移除所有现有 CRC
        for crc in list(subject.assigned_crcs):
            subject.assigned_crcs.remove(crc)
        # 分配新的 CRC
        if crc_id > 0:
            try:
                assign_subject_to_crc(session, subject_id, crc_id)
            except ValueError:
                pass

    session.commit()
    session.refresh(subject)
    return subject


def delete_subject(session: Session, subject_id: int) -> bool:
    subject = session.get(Subject, subject_id)
    if not subject:
        return False
    # 级联删除访视记录
    session.query(Visit).filter(Visit.subject_id == subject_id).delete()
    session.delete(subject)
    session.commit()
    return True


# ============ 访视 CRUD ============

def get_subject_visits(session: Session, subject_id: int) -> List[Visit]:
    """获取受试者全部访视，并自动将超窗未完成的 PENDING 节点标记为方案偏离"""
    visits = session.query(Visit).filter(
        Visit.subject_id == subject_id
    ).order_by(Visit.visit_order).all()

    today = date.today()
    updated = False
    for v in visits:
        if v.status == VisitStatus.PENDING and today > v.window_end:
            v.status = VisitStatus.DEVIATION
            updated = True
    if updated:
        session.commit()

    return visits


def recalculate_visits(session: Session, subject: Subject) -> List[Visit]:
    """
    以入组日期为基准 + 所有已完成访视的实际日期，重新计算全部访视计划。
    这是"实际访视日期回填后自动重算"的核心实现。
    """
    # 收集所有已有实际日期的访视
    completed_visits = session.query(Visit).filter(
        Visit.subject_id == subject.id,
        Visit.actual_date.isnot(None)
    ).order_by(Visit.visit_order).all()

    actual_dates = [(v.visit_order, v.actual_date) for v in completed_visits]

    # 重新计算
    visits_data = calculate_visits(subject.enrollment_date, actual_dates)

    # 删除旧的 PENDING 访视
    pending_visits = session.query(Visit).filter(
        Visit.subject_id == subject.id,
        Visit.status == VisitStatus.PENDING
    ).all()
    for v in pending_visits:
        session.delete(v)

    # 删除 DEVIATION 无实际日期的（有实际日期的保留）
    deviation_visits = session.query(Visit).filter(
        Visit.subject_id == subject.id,
        Visit.status == VisitStatus.DEVIATION,
        Visit.actual_date.is_(None)
    ).all()
    for v in deviation_visits:
        session.delete(v)

    session.flush()

    # 获取删除后仍保留的 visit_order（COMPLETED / SKIPPED / 有实际日期的 DEVIATION）
    existing_orders = {
        v.visit_order for v in session.query(Visit).filter(
            Visit.subject_id == subject.id
        ).all()
    }

    new_visits = []
    for v in visits_data:
        if v["visit_order"] in existing_orders:
            continue  # 该节点已有 COMPLETED/SKIPPED 记录，不重复创建
        visit = Visit(
            subject_id=subject.id,
            visit_order=v["visit_order"],
            visit_label=v["visit_label"],
            visit_type=VisitType(v["visit_type"]),
            planned_date=v["planned_date"],
            window_start=v["window_start"],
            window_end=v["window_end"],
            is_critical=v["is_critical"],
            window_days=v["window_days"],
        )
        session.add(visit)
        new_visits.append(visit)

    session.commit()
    return new_visits


def update_actual_date(session: Session, subject_id: int, visit_order: int,
                       actual_date: date) -> Optional[dict]:
    """
    回填实际访视日期，然后自动重算后续所有节点。
    若实际日期超出窗口范围，标记为方案偏离；否则标记为完成。
    返回更新后的该受试者全部访视。
    """
    subject = session.get(Subject, subject_id)
    if not subject:
        return None

    visit = session.query(Visit).filter(
        Visit.subject_id == subject_id,
        Visit.visit_order == visit_order
    ).first()

    if not visit:
        return None

    visit.actual_date = actual_date
    # 判断是否在窗口内
    if visit.window_start <= actual_date <= visit.window_end:
        visit.status = VisitStatus.COMPLETED
    else:
        visit.status = VisitStatus.DEVIATION
    session.commit()

    # 重新计算后续所有访视
    recalculate_visits(session, subject)

    # 检查所有访视是否都已填写实际日期，若是则自动标记为完成
    all_filled = session.query(Visit).filter(
        Visit.subject_id == subject_id,
        Visit.actual_date.is_(None)
    ).count() == 0
    if all_filled and subject.status == SubjectStatus.ACTIVE:
        subject.status = SubjectStatus.COMPLETED
        session.commit()

    # 刷新并返回
    return {
        "subject": subject,
        "visits": get_subject_visits(session, subject_id)
    }


# ============ 每日提醒 ============

def get_daily_alerts(session: Session, subjects: List[Subject] = None) -> dict:
    """获取今日/明日/本周待访视列表"""
    import datetime as dt
    today = date.today()
    week_end = today + dt.timedelta(days=7)

    subject_ids = None
    if subjects is not None:
        subject_ids = [s.id for s in subjects if s.status == SubjectStatus.ACTIVE]
        if not subject_ids:
            return {"today": [], "tomorrow": [], "this_week": []}

    query = session.query(Visit).join(Subject).filter(
        Visit.status == VisitStatus.PENDING,
        Visit.window_end >= today,
    )
    if subject_ids:
        query = query.filter(Subject.id.in_(subject_ids))
    else:
        query = query.filter(Subject.status == SubjectStatus.ACTIVE)

    pending_visits = query.order_by(Visit.window_end).all()

    alerts = {"today": [], "tomorrow": [], "this_week": []}

    for v in pending_visits:
        ws = check_window_status(v.planned_date, v.window_end, v.window_days)
        item = {
            "subject_id": v.subject.id,
            "subject_code": v.subject.subject_code,
            "full_name": v.subject.full_name,
            "name_abbr": v.subject.name_abbr,
            "visit_order": v.visit_order,
            "visit_label": v.visit_label,
            "planned_date": v.planned_date,
            "window_start": v.window_start,
            "window_end": v.window_end,
            "days_remaining": ws["days_remaining"],
            "window_status": ws["status"],
            "is_critical": v.is_critical,
        }

        # 分类
        days_to_end = (v.window_end - today).days
        if days_to_end <= 1 and v.window_end >= today:
            alerts["today"].append(item)
        if 0 <= (v.window_end - (today + dt.timedelta(days=1))).days <= 1:
            alerts["tomorrow"].append(item)
        if today <= v.window_end <= week_end:
            if item not in alerts["this_week"]:
                alerts["this_week"].append(item)

    # 排序：按窗口结束日期、关键节点优先
    for key in alerts:
        alerts[key].sort(key=lambda x: (x["window_end"], not x["is_critical"]))

    return alerts


# ============ 方案偏离 ============

def get_deviations(session: Session, subjects: List[Subject] = None) -> List[dict]:
    """
    获取所有方案偏离记录。

    偏离类型：
    - overdue: PENDING 节点已超窗口期仍未完成（自动标记为 DEVIATION）
    - out_of_window: 实际日期不在窗口范围内
    - skipped: 受试者脱落后跳过的节点
    """
    # 先遍历所有待查受试者的 PENDING 访视，将超窗未完成的自动标为 DEVIATION
    today = date.today()
    subject_ids = None
    if subjects is not None:
        subject_ids = [s.id for s in subjects]
        if not subject_ids:
            return []

    # 自动标记超窗 PENDING → DEVIATION
    pending_query = session.query(Visit).join(Subject).filter(
        Visit.status == VisitStatus.PENDING,
        Visit.window_end < today,
    )
    if subject_ids:
        pending_query = pending_query.filter(Subject.id.in_(subject_ids))
    overdue_pending = pending_query.all()
    if overdue_pending:
        for v in overdue_pending:
            v.status = VisitStatus.DEVIATION
        session.commit()

    # 检查并修复超窗 COMPLETED → DEVIATION
    completed_visits = session.query(Visit).join(Subject).filter(
        Visit.status == VisitStatus.COMPLETED,
        Visit.actual_date.isnot(None),
    )
    if subject_ids:
        completed_visits = completed_visits.filter(Subject.id.in_(subject_ids))
    completed_visits = completed_visits.all()
    corrected = []
    for v in completed_visits:
        if v.window_start and v.window_end and (v.actual_date < v.window_start or v.actual_date > v.window_end):
            v.status = VisitStatus.DEVIATION
            corrected.append(v)
    if corrected:
        session.commit()

    # 查询所有偏离记录
    query = session.query(Visit).join(Subject).filter(
        Visit.status.in_([VisitStatus.DEVIATION, VisitStatus.SKIPPED])
    )
    if subject_ids:
        query = query.filter(Subject.id.in_(subject_ids))
    deviated = query.order_by(Subject.subject_code, Visit.visit_order).all()

    results = []
    for v in deviated:
        if v.status == VisitStatus.SKIPPED:
            deviation_type = "skipped"
        elif v.actual_date:
            deviation_type = "out_of_window"
        else:
            deviation_type = "overdue"
        results.append({
            "subject_id": v.subject.id,
            "subject_code": v.subject.subject_code,
            "full_name": v.subject.full_name,
            "name_abbr": v.subject.name_abbr,
            "visit_label": v.visit_label,
            "planned_date": v.planned_date,
            "window_start": v.window_start,
            "window_end": v.window_end,
            "actual_date": v.actual_date,
            "deviation_type": deviation_type,
        })

    return results


# ============ 批量导入 ============

def import_subjects_from_excel(session: Session, file_path: str, user_id: int = None) -> dict:
    """从 Excel 批量导入受试者，自动将当前用户设为负责人"""
    import pandas as pd

    try:
        df = pd.read_excel(file_path)
        import re
        # 列名映射：支持中英文列名
        col_map = {
            "subject_code": "subject_code", "受试者编号": "subject_code",
            "full_name": "full_name", "姓名": "full_name",
            "name_abbr": "name_abbr", "姓名缩写": "name_abbr",
            "enrollment_date": "enrollment_date", "入组日期": "enrollment_date",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

        # 兼容旧格式 name_abbr 和新格式 full_name
        name_col = None
        if "full_name" in df.columns:
            name_col = "full_name"
        elif "name_abbr" in df.columns:
            name_col = "name_abbr"
        if name_col is None:
            return {"total": len(df), "success": 0, "failed": len(df),
                    "errors": ["缺少必要列: 姓名 或 姓名缩写"]}

        required_cols = ["subject_code", "enrollment_date"]
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            return {"total": len(df), "success": 0, "failed": len(df),
                    "errors": [f"缺少必要列: {missing}"]}

        total = len(df)
        success = 0
        errors = []

        for _, row in df.iterrows():
            try:
                # NaN 检查（在 str 转换之前）
                if pd.isna(row["subject_code"]):
                    errors.append(f"第{_+1}行：受试者编号为空，已跳过")
                    continue
                code = str(row["subject_code"]).strip()

                # 合法性检查
                if not code:
                    errors.append(f"第{_+1}行：受试者编号为空，已跳过")
                    continue
                if pd.isna(row[name_col]) or not str(row[name_col]).strip():
                    errors.append(f"第{_+1}行：姓名为空，已跳过")
                    continue
                name = str(row[name_col]).strip()

                # 编号格式校验
                if not re.match(r'^[A-Za-z0-9\-_]{2,20}$', code):
                    errors.append(f"第{_+1}行：受试者编号「{code}」格式不正确（仅允许字母、数字、连字符、下划线，2-20位），已跳过")
                    continue

                # 姓名格式校验
                if not re.match(r'^[\u4e00-\u9fff]{2,4}$', name):
                    errors.append(f"第{_+1}行：姓名「{name}」格式不正确（仅允许中文，2-4字），已跳过")
                    continue

                enroll = pd.to_datetime(row["enrollment_date"]).date()

                existing = get_subject_by_code(session, code)
                if existing:
                    errors.append(f"受试者 {code} 已存在，已跳过")
                    continue

                create_subject(session, code, name, enroll, user_id)
                success += 1
            except Exception as e:
                errors.append(f"导入 {row.get('subject_code', '未知')} 失败: {str(e)}")

        return {"total": total, "success": success, "failed": total - success, "errors": errors}
    except Exception as e:
        return {"total": 0, "success": 0, "failed": 0, "errors": [f"文件读取失败: {str(e)}"]}


def batch_delete_subjects(session: Session, subject_ids: list[int]) -> int:
    """批量删除受试者及其所有访视记录"""
    deleted = 0
    for sid in subject_ids:
        subject = session.get(Subject, sid)
        if subject:
            # 先删除关联的 CRC 分配记录
            session.execute(
                crc_subjects.delete().where(crc_subjects.c.subject_id == sid)
            )
            # 再删除所有访视记录
            session.query(Visit).filter(Visit.subject_id == sid).delete()
            # 最后删除受试者
            session.delete(subject)
            deleted += 1
    session.commit()
    return deleted


def export_all_data_to_dataframe(session: Session, subjects: List[Subject] = None):
    """导出受试者及访视数据为 DataFrame（用于 Excel 导出和批量导入）"""
    import pandas as pd
    if subjects is None:
        subjects = session.query(Subject).order_by(Subject.subject_code).all()
    rows = []
    for s in subjects:
        visits = session.query(Visit).filter(Visit.subject_id == s.id).order_by(Visit.planned_date).all()
        if not visits:
            rows.append({
                "subject_code": s.subject_code,
                "full_name": s.full_name,
                "name_abbr": s.name_abbr,
                "enrollment_date": s.enrollment_date,
            })
        else:
            for v in visits:
                rows.append({
                    "subject_code": s.subject_code,
                    "full_name": s.full_name,
                    "name_abbr": s.name_abbr,
                    "enrollment_date": s.enrollment_date,
                    "visit_name": v.visit_label,
                    "target_date": v.planned_date,
                    "window_start": v.window_start,
                    "window_end": v.window_end,
                    "actual_date": v.actual_date,
                    "status": v.status.value if v.status else "",
                    "deviation_days": "",
                    "is_deviated": "是" if v.status == VisitStatus.DEVIATION else "否",
                    "deviation_reason": "",
                })
    return pd.DataFrame(rows)