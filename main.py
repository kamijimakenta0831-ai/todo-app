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

    # 1. 押された子のstatusを変える
    cur = conn.execute(
        "UPDATE tasks SET status = ? WHERE id = ?",
        (body.status, task_id),
    )
    if cur.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="そのidのタスクはない")

    # 2. 押された子の、親のidを調べる
    row = conn.execute(
        "SELECT parent_id FROM tasks WHERE id = ?", (task_id,)
    ).fetchone()
    parent_id = row["parent_id"]

    parent_changed = False

    # 3. 親がいるときだけ、親のstatusを見直す
    if parent_id is not None:
        if body.status == "完了":
            # 完了にしたとき：未完了の子が0件なら、親も完了にする
            remaining = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE parent_id = ? AND status != '完了'",
                (parent_id,),
            ).fetchone()[0]
            if remaining == 0:
                conn.execute(
                    "UPDATE tasks SET status = '完了' WHERE id = ?",
                    (parent_id,),
                )
                parent_changed = True
        else:
            # 未完了に戻したとき：親も未完了に戻す
            conn.execute(
                "UPDATE tasks SET status = '未完了' WHERE id = ?",
                (parent_id,),
            )
            parent_changed = True

    conn.commit()
    conn.close()
    return {"id": task_id, "status": body.status, "parent_changed": parent_changed}