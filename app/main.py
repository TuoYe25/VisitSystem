"""FastAPI 应用入口"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from app.config import APP_NAME, APP_VERSION, DEBUG
from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库"""
    init_db()
    yield


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    debug=DEBUG,
    lifespan=lifespan,
)

# 静态文件
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """首页"""
    return f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{APP_NAME}</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                max-width: 800px;
                margin: 60px auto;
                padding: 0 20px;
                line-height: 1.8;
            }}
            h1 {{ color: #1a73e8; }}
            .status {{ color: #34a853; font-weight: bold; }}
            .info {{ background: #f8f9fa; padding: 16px; border-radius: 8px; margin-top: 16px; }}
        </style>
    </head>
    <body>
        <h1>{APP_NAME}</h1>
        <p>版本: {APP_VERSION} | 状态: <span class="status">运行中</span></p>
        <div class="info">
            <p>本系统用于管理临床试验受试者的随访提醒与访视窗口计算。</p>
            <p>核心功能：受试者管理、访视计划、窗口计算、随访提醒。</p>
            <p>API 文档: <a href="/docs">/docs</a></p>
        </div>
    </body>
    </html>
    """


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "app": APP_NAME, "version": APP_VERSION}
