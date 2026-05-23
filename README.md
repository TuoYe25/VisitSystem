# 受试者随访提醒与访视窗口计算系统

## 项目简介

轻量级 Web 工具，用于管理临床试验受试者的随访提醒与访视窗口计算。支持约 120 名受试者规模。

## 功能特性

- 受试者信息管理（入组、状态跟踪）
- 访视计划与窗口计算（基于入组日期自动生成随访计划）
- 超窗检测（自动识别超窗/漏访）
- 随访提醒（短信/电话/微信/邮件等提醒方式）
- Excel 导入导出

## 技术栈

- **后端**：FastAPI (Python 3.10+)
- **数据库**：SQLite + SQLAlchemy ORM
- **前端**：Jinja2 模板 + 原生 JS（后续可升级为 Vue/React）
- **Excel**：openpyxl + pandas

## 项目结构

```
VisitSystem/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 应用入口
│   ├── config.py            # 配置管理
│   ├── database.py          # 数据库引擎与会话
│   ├── models/              # 数据模型
│   │   ├── subject.py       # 受试者
│   │   ├── visit.py         # 访视记录
│   │   └── reminder.py      # 随访提醒
│   ├── routers/             # API 路由
│   ├── templates/           # Jinja2 模板
│   └── static/              # 静态资源
│       ├── css/
│       └── js/
├── data/                    # SQLite 数据文件（gitignore）
├── tests/                   # 测试
├── requirements.txt
├── .gitignore
└── README.md
```

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 3. 访问
# API 文档: http://localhost:8000/docs
# 首页:     http://localhost:8000/
```

## 数据模型

| 表 | 说明 |
|---|---|
| `subjects` | 受试者基本信息（编号、姓名、性别、入组日期、状态等） |
| `visits` | 访视记录（计划日期、窗口起止、实际日期、状态） |
| `reminders` | 随访提醒（提醒时间、方式、发送状态） |

## 开发状态

- [x] F0: 项目初始化 - 技术栈选型与脚手架
- [ ] F1: 受试者管理 CRUD
- [ ] F2: 访视计划自动生成
- [ ] F3: 随访提醒规则引擎
- [ ] F4: Excel 导入导出
- [ ] F5: 前端页面
- [ ] F6: 统计报表
- [ ] F7: 通知发送

## 许可证

待定
