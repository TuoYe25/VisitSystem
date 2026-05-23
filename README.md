# VisitSystem - 受试者随访提醒与访视窗口计算系统

## 项目简介

VisitSystem 是一个轻量级 Web 工具，用于管理临床试验受试者的随访提醒与访视窗口计算。适用于约 120 名受试者规模的小型临床研究。

## 功能特性

- **受试者管理**：登记、查询、状态跟踪
- **访视计划**：自动计算访视窗口（计划日期 ± N 天）
- **超窗检测**：实际访视日期与窗口比对，标记超窗完成
- **随访提醒**：定时提醒受试者按时访视
- **Excel 导入导出**：批量导入受试者数据，导出访视报表

## 技术栈

| 层级     | 技术                                      |
| -------- | ----------------------------------------- |
| 后端框架 | FastAPI 0.115                             |
| ORM      | SQLAlchemy 2.0                            |
| 数据库   | SQLite（WAL 模式）                        |
| 模板引擎 | Jinja2                                    |
| Excel    | openpyxl                                  |
| 前端     | 原生 HTML/CSS，预留 JavaScript 扩展接口   |

## 项目结构

```
VisitSystem/
├── app/
│   ├── main.py              # FastAPI 应用入口
│   ├── config.py            # 配置管理
│   ├── database.py          # 数据库引擎与会话管理
│   ├── models/
│   │   ├── subject.py       # 受试者模型
│   │   ├── visit.py         # 访视记录模型
│   │   └── reminder.py      # 随访提醒模型
│   ├── routers/             # API 路由（F1-F7 功能模块）
│   ├── templates/           # Jinja2 模板
│   └── static/              # 静态资源
├── data/                    # SQLite 数据库文件（自动生成）
├── requirements.txt         # Python 依赖
├── .gitignore               # Git 忽略规则
└── README.md                # 项目说明
```

## 快速开始

```bash
# 1. 克隆项目
git clone https://github.com/TuoYe25/VisitSystem.git
cd VisitSystem

# 2. 创建虚拟环境（推荐）
python -m venv venv
.\venv\Scripts\activate   # Windows
# source venv/bin/activate  # macOS/Linux

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动应用
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 5. 访问
# 首页:     http://localhost:8000
# API 文档: http://localhost:8000/docs
# 健康检查: http://localhost:8000/health
```

## 数据模型

### Subject（受试者）
| 字段            | 类型   | 说明             |
| --------------- | ------ | ---------------- |
| subject_number  | str    | 受试者编号（唯一） |
| name            | str    | 姓名             |
| gender          | str    | 性别 (M/F)       |
| birth_date      | date   | 出生日期         |
| enrollment_date | date   | 入组日期         |
| status          | enum   | 状态             |
| contact_phone   | str?   | 联系电话         |

### Visit（访视记录）
| 字段         | 类型 | 说明                          |
| ------------ | ---- | ----------------------------- |
| visit_number | int  | 第几次访视                    |
| planned_date | date | 计划访视日期                  |
| window_start | date | 窗口开始（planned_date - N天） |
| window_end   | date | 窗口结束（planned_date + N天） |
| actual_date  | date?| 实际访视日期                  |
| is_out_of_window | bool | 是否超窗                  |

### Reminder（随访提醒）
| 字段      | 类型     | 说明                     |
| --------- | -------- | ------------------------ |
| remind_at | datetime | 提醒时间                 |
| method    | enum     | 提醒方式 (sms/email/phone/wechat) |
| status    | enum     | 发送状态                 |

## 配置

通过环境变量配置（可选，均有默认值）：

| 变量          | 默认值                         | 说明         |
| ------------- | ------------------------------ | ------------ |
| `DATABASE_URL`| `sqlite:///data/visitsystem.db` | 数据库连接   |
| `DEBUG`       | `true`                         | 调试模式     |

## 开发指南

### 添加新路由

在 `app/routers/` 目录下创建路由模块，然后在 `app/main.py` 中注册：

```python
from app.routers import subjects
app.include_router(subjects.router, prefix="/api/subjects", tags=["受试者"])
```

### 运行测试

```bash
pytest
```

## 许可证

待定
