# -*- coding: utf-8 -*-
"""
init_db.py
用于初始化 SQLite 数据库 hot.db，创建表 hot_items_history 和必要索引。
可重复执行（不会重复建表）。
"""

from __future__ import annotations
import sqlite3
from pathlib import Path

DB_PATH = Path("hot.db")

DDL = """
CREATE TABLE IF NOT EXISTS hot_items_history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    platform     TEXT NOT NULL,      -- 平台名称，如 'baidu'、'weibo'、'zhihu'
    topic_key    TEXT,               -- 可选主题标识
    title        TEXT NOT NULL,      -- 标题
    url          TEXT NOT NULL,      -- 原文链接
    image_url    TEXT,               -- 封面图片
    excerpt      TEXT,               -- 简介
    heat_text    TEXT,               -- 热度文本（原始字符串）
    heat_value   INTEGER,            -- 热度数值
    rank         INTEGER,            -- 排名
    tags_text    TEXT,               -- 标签字符串，如 "娱乐|新闻"
    scraped_at   TEXT NOT NULL,      -- 抓取时间 YYYY-MM-DD HH:MM:SS
    scraped_date TEXT NOT NULL,      -- 抓取日期 YYYY-MM-DD
    extra_json   TEXT,               -- 额外字段（JSON）
    UNIQUE(platform, url, scraped_date) ON CONFLICT REPLACE
);
"""

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_hot_hist_platform_date ON hot_items_history(platform, scraped_date);",
    "CREATE INDEX IF NOT EXISTS idx_hot_hist_date ON hot_items_history(scraped_date);",
    "CREATE INDEX IF NOT EXISTS idx_hot_hist_heat_value ON hot_items_history(heat_value);",
    "CREATE INDEX IF NOT EXISTS idx_hot_hist_rank ON hot_items_history(rank);",
]

def init_db(db_path: Path = DB_PATH) -> None:
    """初始化数据库"""
    conn = sqlite3.connect(db_path)
    conn.executescript(DDL)
    for idx_sql in INDEXES:
        conn.execute(idx_sql)
    conn.commit()
    conn.close()
    print(f"✅ 数据库初始化完成：{db_path.resolve()}")

if __name__ == "__main__":
    init_db()