import sqlite3

conn = sqlite3.connect("todo.db")

conn.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    parent_id INTEGER,
    status TEXT NOT NULL DEFAULT '未完了',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()
conn.close()
print("tasksテーブルを作りました")

import sqlite3

conn = sqlite3.connect("todo.db")  # DBファイルに接続（なければ作られる）
conn.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,         -- 自動で増える番号
    title TEXT NOT NULL,                          -- 必須
    parent_id INTEGER,                            -- 親なしは空(NULL)
    status TEXT NOT NULL DEFAULT '未完了',        -- 初期値は未完了
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP  -- 作成日時が自動で入る
)
""")
conn.commit()  # 変更を確定
conn.close()   # 接続を閉じる