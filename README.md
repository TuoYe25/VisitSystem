# VisitSystem — 受试者随访提醒与访视窗口计算系统

面向三甲医院药物临床试验的受试者随访管理系统，支持120名受试者、10个访视节点的全流程管理。

## 功能特性

### 受试者管理
- 受试者 CRUD：编号、姓名、入组日期、状态（在组/脱落/完成）
- 批量导入：Excel 导入，兼容中英文列名，逐行校验
- 批量导出：导出受试者及访视数据，支持再导入
- 批量删除：勾选后一键移除
- 表格排序筛选：前端排序 + 关键词筛选
- 责任人：显示 CRC 负责人，PI 可重新分配

### 访视节点与日程
- 10 个访视节点：D0（筛选期）+ C1-C6（治疗期）+ F1-F3（随访期）
- 自动计算计划日期、窗口起止日期
- 日历视图：直观展示每日待办访视

### 回填与重算引擎
- 实际访视日期回填后，自动重算后续所有节点的计划日期
- 计划日期保持协议推算值不变，实际日期仅驱动当前基点
- 所有访视已填写实际日期后，受试者自动标记为"完成"

### 方案偏离检测
- 超窗未完成的 PENDING 访视自动标记为 DEVIATION
- 偏离列表页：集中查看、筛选、导出

### 权限控制
- PI（主要研究者）：查看全部受试者，管理 CRC 分配
- CRC（临床研究协调员）：仅查看自己负责的受试者
- JWT 认证 + Cookie 回退
- 默认账号：`admin` / `admin123`（PI）、`crc01` / `123456`（CRC）

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI 0.104 |
| 服务运行 | Uvicorn 0.24 |
| ORM | SQLAlchemy 2.0 |
| 数据库 | SQLite |
| 模板引擎 | Jinja2 |
| 数据校验 | Pydantic 2.5 |
| Excel 处理 | openpyxl + pandas |
| 拼音转换 | pypinyin |
| 认证 | JWT + Cookie |

## 项目结构

```
VisitSystem/
├── app.py                # FastAPI 主入口，路由定义
├── models.py             # 数据库模型（Subject / User / Visit）
├── schemas.py            # Pydantic 请求/响应模型
├── crud.py               # 受试者 & 访视 CRUD 逻辑
├── crud_user.py          # 用户 & 权限管理逻辑
├── calculator.py         # 访视日期计算引擎（回填重算）
├── auth.py               # JWT 认证与权限中间件
├── requirements.txt      # Python 依赖
├── visitsystem.db        # SQLite 数据库文件
├── .gitignore
├── templates/
│   ├── base.html         # 基础模板
│   ├── login.html        # 登录页
│   ├── index.html        # 仪表盘
│   ├── subjects.html     # 受试者列表
│   ├── subject_detail.html # 受试者详情（含编辑弹窗）
│   ├── calendar.html     # 日历视图
│   ├── deviations.html   # 方案偏离列表
│   └── users.html        # 用户管理
└── tests/                # 测试数据（Git 忽略）
```

## 快速开始

```bash
# 1. 克隆项目
git clone https://github.com/TuoYe25/VisitSystem.git
cd VisitSystem

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动服务
python app.py
```

服务启动后访问 http://127.0.0.1:5050，使用默认账号登录。

## 访视窗口规则

| 节点 | 标签 | 类型 | 窗口 |
|------|------|------|------|
| 0 | D0 / 筛选期 | screening | 入组日期 ±0天 |
| 1-6 | C1-C6 / 治疗期 | treatment | 计划日期 ±3天 |
| 7-9 | F1-F3 / 随访期 | followup | 计划日期 ±7天 |

回填实际日期后，系统自动以该实际日期为基点重新推算后续节点计划日期。

## 测试数据

`tests/` 目录内含两份测试 Excel：

| 文件 | 说明 |
|------|------|
| test_subjects_pi_60.xlsx | PI 权限测试（60 名） |
| test_subjects_crc_60.xlsx | CRC 权限测试（60 名） |

可通过受试者管理页的"导入"功能批量导入。

## 许可证

MIT License