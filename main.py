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
    title: Optional[str] = None
    status: Optional[str] = None


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
def update_task(task_id: int, body: TaskUpdate):
    # 入口の検証（変な注文は、ここで止める）
    if body.title is None and body.status is None:
        raise HTTPException(status_code=422, detail="titleかstatusのどちらかは必要")
    if body.status is not None and body.status not in ("未完了", "完了"):
        raise HTTPException(status_code=422, detail="statusは未完了か完了")
    new_title = None
    if body.title is not None:
        new_title = body.title.strip()
        if new_title == "":
            raise HTTPException(status_code=422, detail="titleは空にできない")

    conn = get_conn()

    # 対象が存在するか確認し、親のidも控える
    row = conn.execute(
        "SELECT parent_id FROM tasks WHERE id = ?", (task_id,)
    ).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="そのidのタスクはない")
    parent_id = row["parent_id"]

    # titleが送られてきたときだけ、titleを変える
    if new_title is not None:
        conn.execute(
            "UPDATE tasks SET title = ? WHERE id = ?",
            (new_title, task_id),
        )

    # statusが送られてきたときだけ、statusを変え、親を見直す
    parent_changed = False
    if body.status is not None:
        conn.execute(
            "UPDATE tasks SET status = ? WHERE id = ?",
            (body.status, task_id),
        )
        if parent_id is not None:
            if body.status == "完了":
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
                conn.execute(
                    "UPDATE tasks SET status = '未完了' WHERE id = ?",
                    (parent_id,),
                )
                parent_changed = True

    conn.commit()
    conn.close()
    return {
        "id": task_id,
        "title": new_title,
        "status": body.status,
        "parent_changed": parent_changed,
    }


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    conn = get_conn()

    # 1. 消す対象が存在するか確認し、親のidも控えておく
    row = conn.execute(
        "SELECT parent_id FROM tasks WHERE id = ?", (task_id,)
    ).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="そのidのタスクはない")
    parent_id = row["parent_id"]

    # 2. 消す対象のid一覧を作る（自分 → 子 → 孫、の順に集める）
    ids = [task_id]
    i = 0
    while i < len(ids):
        children = conn.execute(
            "SELECT id FROM tasks WHERE parent_id = ?", (ids[i],)
        ).fetchall()
        for c in children:
            ids.append(c["id"])
        i += 1

    # 3. 集めたidを、まとめて消す
    conn.executemany("DELETE FROM tasks WHERE id = ?", [(x,) for x in ids])

    # 4. 消した子の親がいるなら、残った子を見て、親を見直す
    parent_changed = False
    if parent_id is not None:
        total = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE parent_id = ?", (parent_id,)
        ).fetchone()[0]
        remaining = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE parent_id = ? AND status != '完了'",
            (parent_id,),
        ).fetchone()[0]
        if total > 0 and remaining == 0:
            conn.execute(
                "UPDATE tasks SET status = '完了' WHERE id = ?",
                (parent_id,),
            )
            parent_changed = True

    # 5. 最後に1回、まとめて確定する
    conn.commit()
    conn.close()
    return {"deleted": ids, "parent_changed": parent_changed}