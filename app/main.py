"""FastAPI 应用入口"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.database import init_db

app = FastAPI(
    title="受试者随访提醒与访视窗口计算系统",
    description="轻量级临床试验受试者随访管理工具",
    version="0.1.0",
)

# 静态文件
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
def root():
    return {"message": "受试者随访提醒与访视窗口计算系统 v0.1.0", "status": "running"}
