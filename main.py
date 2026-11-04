import sqlite3
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_conn():
    conn = sqlite3.connect("todo.db")
    conn.row_factory = sqlite3.Row  # 行を列名で扱えるようにする
    return conn


class TaskCreate(BaseModel):
    title: str                       # 必須
    parent_id: Optional[int] = None  # 省略可（親なし）


@app.get("/")
def hello():
    return {"message": "hello"}


@app.get("/tasks")
def list_tasks():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/tasks")
def create_task(task: TaskCreate):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO tasks (title, parent_id) VALUES (?, ?)",
        (task.title, task.parent_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    return dict(row)