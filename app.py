"""
受试者随访提醒与访视窗口计算系统 - FastAPI 主入口
"""
import os
import tempfile
from datetime import date, datetime
from typing import Optional

from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException, Query, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import BaseModel

from models import init_db, get_session, SubjectStatus, VisitStatus, UserRole
from schemas import (
    SubjectCreate, SubjectUpdate, SubjectResponse,
    VisitResponse, VisitActualUpdate,
)
import crud
from auth import (
    get_current_user, require_pi, create_access_token, SECRET_KEY, ALGORITHM
)
from crud_user import (
    authenticate_user, create_user, get_viewable_subjects,
    assign_subject_to_crc, unassign_subject_from_crc,
    get_all_crcs, get_all_pis, get_crcs_for_subject,
    can_view_subject, can_edit_subject
)

# ============ 初始化 ============

app = FastAPI(title="受试者随访提醒与访视窗口计算系统", version="1.0.0")


# ============ 异常处理 ============

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """401 未认证时，非API路由重定向到登录页"""
    if exc.status_code == 401 and not request.url.path.startswith("/api/"):
        return RedirectResponse(url="/login", status_code=302)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

# 初始化数据库
init_db()
print("数据库初始化完成")

# 模板目录
os.makedirs("templates", exist_ok=True)
templates = Jinja2Templates(directory="templates")


# ============ 种子数据 ============

def seed_default_users():
    """创建默认用户（如果不存在）"""
    session = get_session()
    try:
        from models import User
        existing = session.query(User).first()
        if existing:
            return
        # 创建默认 PI
        pi_hash, pi_salt = User.hash_password("admin123")
        pi = User(
            username="admin",
            password_hash=pi_hash,
            salt=pi_salt,
            display_name="张主任",
            role=UserRole.PI
        )
        # 创建默认 CRC
        crc_hash, crc_salt = User.hash_password("123456")
        crc = User(
            username="crc01",
            password_hash=crc_hash,
            salt=crc_salt,
            display_name="李协调员",
            role=UserRole.CRC
        )
        session.add_all([pi, crc])
        session.commit()
        print("默认用户创建完成: admin(PI), crc01(CRC)")
    finally:
        session.close()


seed_default_users()


# ============ 认证 API ============

class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/api/auth/login")
async def api_login(data: LoginRequest):
    """用户登录"""
    session = get_session()
    try:
        user = authenticate_user(session, data.username, data.password)
        if not user:
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        token = create_access_token({"sub": str(user.id), "role": user.role.value})
        return {
            "token": token,
            "username": user.username,
            "display_name": user.display_name,
            "role": user.role.value,
        }
    finally:
        session.close()


@app.get("/api/auth/me")
async def api_me(user=Depends(get_current_user)):
    """获取当前用户信息"""
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role.value,
    }


# ============ 登录页面 ============

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """登录页面"""
    return templates.TemplateResponse(request, "login.html", {"request": request})


# ============ 页面路由 ============

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, user=Depends(get_current_user)):
    """首页 - 仪表盘"""
    session = get_session()
    try:
        all_subjects = get_viewable_subjects(session, user)
        alerts = crud.get_daily_alerts(session, all_subjects)
        deviations = crud.get_deviations(session, all_subjects)

        active_count = sum(1 for s in all_subjects if s.status == SubjectStatus.ACTIVE)
        dropout_count = sum(1 for s in all_subjects if s.status == SubjectStatus.DROPOUT)
        completed_count = sum(1 for s in all_subjects if s.status == SubjectStatus.COMPLETED)

        return templates.TemplateResponse(request, "index.html", {
            "request": request,
            "current_user": user,
            "alerts": alerts,
            "subjects": all_subjects,
            "deviations": deviations,
            "active_count": active_count,
            "dropout_count": dropout_count,
            "completed_count": completed_count,
        })
    finally:
        session.close()


@app.get("/subjects", response_class=HTMLResponse)
async def subjects_page(request: Request, status: Optional[str] = None, user=Depends(get_current_user)):
    """受试者管理页面"""
    session = get_session()
    try:
        all_subjects = get_viewable_subjects(session, user)
        if status:
            all_subjects = [s for s in all_subjects if s.status.value == status]
        # 获取所有CRC列表（用于PI分配）
        crcs = get_all_crcs(session) if user.role == UserRole.PI else []
        # 构建受试者→负责人映射
        subject_crc_map = {}
        for s in all_subjects:
            crc_list = get_crcs_for_subject(session, s.id)
            subject_crc_map[s.id] = crc_list[0].display_name if crc_list else '-'
        return templates.TemplateResponse(request, "subjects.html", {
            "request": request,
            "current_user": user,
            "subjects": all_subjects,
            "crcs": crcs,
            "subject_crc_map": subject_crc_map,
            "filter_status": status or "",
        })
    finally:
        session.close()


@app.get("/subjects/{subject_id}", response_class=HTMLResponse)
async def subject_detail(request: Request, subject_id: int, user=Depends(get_current_user)):
    """受试者详情页"""
    session = get_session()
    try:
        subject = crud.get_subject(session, subject_id)
        if not subject:
            raise HTTPException(status_code=404, detail="受试者不存在")
        if not can_view_subject(user, subject):
            raise HTTPException(status_code=403, detail="无权限查看该受试者")
        visits = crud.get_subject_visits(session, subject_id)
        crcs = get_all_crcs(session) if user.role == UserRole.PI else []
        assigned_crc_ids = [c.id for c in get_crcs_for_subject(session, subject_id)]
        return templates.TemplateResponse(request, "subject_detail.html", {
            "request": request,
            "current_user": user,
            "subject": subject,
            "visits": visits,
            "crcs": crcs,
            "assigned_crc_ids": assigned_crc_ids,
        })
    finally:
        session.close()


@app.get("/calendar", response_class=HTMLResponse)
async def calendar_page(request: Request, user=Depends(get_current_user)):
    """访视日历视图"""
    session = get_session()
    try:
        subjects = get_viewable_subjects(session, user)
        return templates.TemplateResponse(request, "calendar.html", {
            "request": request,
            "current_user": user,
            "subjects": subjects,
        })
    finally:
        session.close()


@app.get("/deviations", response_class=HTMLResponse)
async def deviations_page(request: Request, user=Depends(get_current_user)):
    """方案偏离报表"""
    session = get_session()
    try:
        subjects = get_viewable_subjects(session, user)
        deviations = crud.get_deviations(session, subjects)
        return templates.TemplateResponse(request, "deviations.html", {
            "request": request,
            "current_user": user,
            "deviations": deviations,
        })
    finally:
        session.close()


@app.get("/users", response_class=HTMLResponse)
async def users_page(request: Request, user=Depends(get_current_user)):
    """用户管理页面（仅PI可访问）"""
    if user.role != UserRole.PI:
        raise HTTPException(status_code=403, detail="仅PI可管理用户")
    session = get_session()
    try:
        all_users = get_all_crcs(session) + get_all_pis(session)
        subjects = crud.get_all_subjects(session)
        # 每个受试者对应的CRC列表
        subject_crc_map = {}
        for s in subjects:
            crcs = get_crcs_for_subject(session, s.id)
            subject_crc_map[s.id] = [c.id for c in crcs]
        return templates.TemplateResponse(request, "users.html", {
            "request": request,
            "current_user": user,
            "all_users": all_users,
            "subjects": subjects,
            "subject_crc_map": subject_crc_map,
        })
    finally:
        session.close()


# ============ API 路由 ============

# --- 受试者 ---

@app.post("/api/subjects", response_model=SubjectResponse)
async def api_create_subject(data: SubjectCreate, user=Depends(get_current_user)):
    session = get_session()
    try:
        existing = crud.get_subject_by_code(session, data.subject_code)
        if existing:
            raise HTTPException(status_code=400, detail="受试者编号已存在")
        subject = crud.create_subject(session, data.subject_code, data.full_name, data.enrollment_date)
        return subject
    finally:
        session.close()


@app.get("/api/subjects")
async def api_list_subjects(status: Optional[str] = None, user=Depends(get_current_user)):
    session = get_session()
    try:
        subjects = get_viewable_subjects(session, user)
        if status:
            subjects = [s for s in subjects if s.status.value == status]
        return [
            {
                "id": s.id,
                "subject_code": s.subject_code,
                "full_name": s.full_name,
                "name_abbr": s.name_abbr,
                "enrollment_date": str(s.enrollment_date),
                "status": s.status.value if s.status else "",
                "dropout_date": str(s.dropout_date) if s.dropout_date else None,
            }
            for s in subjects
        ]
    finally:
        session.close()


@app.get("/api/subjects/{subject_id}")
async def api_get_subject(subject_id: int, user=Depends(get_current_user)):
    session = get_session()
    try:
        subject = crud.get_subject(session, subject_id)
        if not subject:
            raise HTTPException(status_code=404)
        if not can_view_subject(user, subject):
            raise HTTPException(status_code=403, detail="无权限")
        return {
            "id": subject.id,
            "subject_code": subject.subject_code,
            "full_name": subject.full_name,
            "name_abbr": subject.name_abbr,
            "enrollment_date": str(subject.enrollment_date),
            "status": subject.status.value,
        }
    finally:
        session.close()


@app.put("/api/subjects/{subject_id}")
async def api_update_subject(subject_id: int, data: SubjectUpdate, user=Depends(get_current_user)):
    session = get_session()
    try:
        subject = crud.get_subject(session, subject_id)
        if not subject:
            raise HTTPException(status_code=404)
        if not can_edit_subject(user, subject):
            raise HTTPException(status_code=403, detail="无权限编辑该受试者")
        kwargs = {k: v for k, v in data.model_dump().items() if v is not None}
        subject = crud.update_subject(session, subject_id, **kwargs)
        return {"ok": True}
    finally:
        session.close()


@app.delete("/api/subjects/{subject_id}")
async def api_delete_subject(subject_id: int, user=Depends(get_current_user)):
    session = get_session()
    try:
        subject = crud.get_subject(session, subject_id)
        if not subject:
            raise HTTPException(status_code=404)
        if not can_edit_subject(user, subject):
            raise HTTPException(status_code=403, detail="无权限删除该受试者")
        ok = crud.delete_subject(session, subject_id)
        if not ok:
            raise HTTPException(status_code=404)
        return {"ok": True}
    finally:
        session.close()


# --- 访视 ---

@app.get("/api/subjects/{subject_id}/visits")
async def api_get_visits(subject_id: int, user=Depends(get_current_user)):
    session = get_session()
    try:
        subject = crud.get_subject(session, subject_id)
        if not subject or not can_view_subject(user, subject):
            raise HTTPException(status_code=403, detail="无权限")
        visits = crud.get_subject_visits(session, subject_id)
        return [
            {
                "id": v.id,
                "visit_order": v.visit_order,
                "visit_label": v.visit_label,
                "visit_type": v.visit_type.value if v.visit_type else "",
                "planned_date": str(v.planned_date),
                "window_start": str(v.window_start),
                "window_end": str(v.window_end),
                "actual_date": str(v.actual_date) if v.actual_date else None,
                "status": v.status.value if v.status else "",
                "is_critical": v.is_critical,
            }
            for v in visits
        ]
    finally:
        session.close()


@app.put("/api/subjects/{subject_id}/visits/{visit_order}")
async def api_update_actual_date(subject_id: int, visit_order: int, data: VisitActualUpdate, user=Depends(get_current_user)):
    """回填实际访视日期"""
    session = get_session()
    try:
        subject = crud.get_subject(session, subject_id)
        if not subject or not can_edit_subject(user, subject):
            raise HTTPException(status_code=403, detail="无权限")
        result = crud.update_actual_date(session, subject_id, visit_order, data.actual_date)
        if not result:
            raise HTTPException(status_code=404)
        return {"ok": True}
    finally:
        session.close()


# --- 每日提醒 ---

@app.get("/api/alerts")
async def api_alerts(user=Depends(get_current_user)):
    session = get_session()
    try:
        subjects = get_viewable_subjects(session, user)
        return crud.get_daily_alerts(session, subjects)
    finally:
        session.close()


# --- 方案偏离 ---

@app.get("/api/deviations")
async def api_deviations(user=Depends(get_current_user)):
    session = get_session()
    try:
        subjects = get_viewable_subjects(session, user)
        return crud.get_deviations(session, subjects)
    finally:
        session.close()


# --- 导出 ---

@app.get("/api/export/subjects")
async def api_export_subjects(user=Depends(get_current_user)):
    """导出全部数据（受试者 + 访视记录）为 Excel"""
    session = get_session()
    try:
        subjects = get_viewable_subjects(session, user)
        df = crud.export_all_data_to_dataframe(session, subjects)
        col_map = {
            "subject_code": "受试者编号",
            "full_name": "姓名",
            "name_abbr": "姓名缩写",
            "enrollment_date": "入组日期",
            "visit_name": "访视节点",
            "target_date": "计划日期",
            "window_start": "窗口开始",
            "window_end": "窗口结束",
            "actual_date": "实际日期",
            "status": "状态",
            "deviation_days": "偏离天数",
            "is_deviated": "是否偏离",
            "deviation_reason": "偏离原因",
        }
        rename = {k: v for k, v in col_map.items() if k in df.columns}
        df = df.rename(columns=rename)
        path = os.path.join(tempfile.gettempdir(), "temp_export_full.xlsx")
        df.to_excel(path, index=False)
        return FileResponse(path, filename="全部数据.xlsx",
                           media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    finally:
        session.close()


@app.post("/api/subjects/batch-delete")
async def api_batch_delete(data: dict, user=Depends(get_current_user)):
    """批量删除受试者"""
    subject_ids = data.get("ids", [])
    if not subject_ids:
        raise HTTPException(status_code=400, detail="请提供要删除的受试者ID列表")
    session = get_session()
    try:
        # 检查权限
        for sid in subject_ids:
            s = crud.get_subject(session, sid)
            if s and not can_edit_subject(user, s):
                raise HTTPException(status_code=403, detail=f"无权限删除受试者 {s.subject_code}")
        deleted = crud.batch_delete_subjects(session, subject_ids)
        return {"deleted": deleted}
    finally:
        session.close()


@app.get("/api/export/deviations")
async def api_export_deviations(user=Depends(get_current_user)):
    """导出方案偏离报表"""
    import pandas as pd
    session = get_session()
    try:
        subjects = get_viewable_subjects(session, user)
        deviations = crud.get_deviations(session, subjects)
        data = [{
            "受试者编号": d["subject_code"],
            "姓名": d["full_name"],
            "姓名缩写": d["name_abbr"],
            "访视节点": d["visit_label"],
            "计划日期": d["planned_date"],
            "窗口开始": d["window_start"],
            "窗口结束": d["window_end"],
            "实际日期": d["actual_date"] or "未完成",
            "偏离类型": d["deviation_type"],
        } for d in deviations]
        df = pd.DataFrame(data)
        path = "temp_export_deviations.xlsx"
        df.to_excel(path, index=False)
        return FileResponse(path, filename="方案偏离报表.xlsx",
                           media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    finally:
        session.close()


# --- Excel 批量导入 ---

@app.post("/api/import")
async def api_import(file: UploadFile = File(...), user=Depends(get_current_user)):
    """Excel 批量导入受试者"""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    tmp.write(await file.read())
    tmp.close()

    session = get_session()
    try:
        result = crud.import_subjects_from_excel(session, tmp.name)
        return result
    finally:
        session.close()
        os.unlink(tmp.name)


# --- 用户管理 API（仅PI） ---

@app.get("/api/users")
async def api_list_users(user=Depends(require_pi)):
    """获取所有用户列表"""
    session = get_session()
    try:
        users = get_all_crcs(session) + get_all_pis(session)
        # 按角色排序，PI在前
        users.sort(key=lambda u: (u.role.value != "PI", u.username))
        return [
            {
                "id": u.id,
                "username": u.username,
                "display_name": u.display_name,
                "role": u.role.value,
                "subject_count": len(u.subjects) if u.role == UserRole.CRC else -1,
            }
            for u in users
        ]
    finally:
        session.close()


class CreateUserRequest(BaseModel):
    username: str
    password: str
    display_name: str
    role: str


@app.post("/api/users")
async def api_create_user(data: CreateUserRequest, user=Depends(require_pi)):
    """创建新用户"""
    session = get_session()
    try:
        role = UserRole(data.role)
        new_user = create_user(session, data.username, data.password, data.display_name, role)
        return {"id": new_user.id, "username": new_user.username, "ok": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        session.close()


@app.post("/api/subjects/{subject_id}/assign-crc")
async def api_assign_crc(subject_id: int, data: dict, user=Depends(require_pi)):
    """为受试者分配CRC"""
    crc_id = data.get("crc_id")
    if not crc_id:
        raise HTTPException(status_code=400, detail="请提供CRC ID")
    session = get_session()
    try:
        assign_subject_to_crc(session, subject_id, crc_id)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        session.close()


@app.post("/api/subjects/{subject_id}/unassign-crc")
async def api_unassign_crc(subject_id: int, data: dict, user=Depends(require_pi)):
    """取消CRC对受试者的负责"""
    crc_id = data.get("crc_id")
    if not crc_id:
        raise HTTPException(status_code=400, detail="请提供CRC ID")
    session = get_session()
    try:
        unassign_subject_from_crc(session, subject_id, crc_id)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        session.close()


@app.get("/api/subjects/{subject_id}/crcs")
async def api_get_subject_crcs(subject_id: int, user=Depends(get_current_user)):
    """获取受试者负责的CRC列表"""
    session = get_session()
    try:
        crcs = get_crcs_for_subject(session, subject_id)
        return [{"id": c.id, "username": c.username, "display_name": c.display_name} for c in crcs]
    finally:
        session.close()


# ============ 启动 ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5050)