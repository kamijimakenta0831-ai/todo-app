import sqlite3
from typing import Optional

from fastapi import FastAPI, HTTPException
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
    conn.row_factory = sqlite3.Row
    return conn


class TaskCreate(BaseModel):
    title: str
    parent_id: Optional[int] = None


class TaskUpdate(BaseModel):
    status: str


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
    new_id = cur.lastrowid
    conn.close()
    return {"id": new_id, "title": task.title, "parent_id": task.parent_id}


@app.patch("/tasks/{task_id}")
def update_status(task_id: int, body: TaskUpdate):
    if body.status not in ("未完了", "完了"):
        raise HTTPException(status_code=422, detail="statusは未完了か完了")
    conn = get_conn()
    cur = conn.execute(
        "UPDATE tasks SET status = ? WHERE id = ?",
        (body.status, task_id),
    )
    conn.commit()
    changed = cur.rowcount
    conn.close()
    if changed == 0:
        raise HTTPException(status_code=404, detail="そのidのタスクはない")
    return {"id": task_id, "status": body.status}