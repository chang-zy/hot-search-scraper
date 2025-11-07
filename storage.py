# storage_history.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Iterable, Mapping, Any, Optional, Sequence
from datetime import datetime
import sqlite3
import json


class HotItemsHistoryDB:
    """
    仅负责对既有表 hot_items_history 的 CRUD 操作（不创建表）。
    - db_path 与 conn 任选其一；若都提供则优先使用 conn。
    - 自动开启事务批量写入；ON CONFLICT 覆盖更新同一天同链接的数据。
    """

    # 允许的排序白名单，防注入
    _ALLOWED_ORDERS = {
        "scraped_at DESC", "scraped_at ASC",
        "scraped_date DESC", "scraped_date ASC",
        "heat_value DESC", "heat_value ASC",
        "rank ASC", "rank DESC",
        "id DESC", "id ASC",
    }

    def __init__(self, db_path: Optional[str] = None, conn: Optional[sqlite3.Connection] = None,
                 *, apply_pragmas: bool = True) -> None:
        if conn is not None:
            self._conn = conn
            self._own_conn = False
        elif db_path is not None:
            self._conn = sqlite3.connect(db_path)
            self._own_conn = True
        else:
            raise ValueError("Either db_path or conn must be provided.")

        if apply_pragmas:
            # 更稳健的默认 PRAGMA（不涉及 DDL）
            self._conn.execute("PRAGMA journal_mode = WAL;")
            self._conn.execute("PRAGMA synchronous = NORMAL;")

    # ---------- lifecycle ----------
    @property
    def conn(self) -> sqlite3.Connection:
        return self._conn

    def close(self) -> None:
        if self._own_conn and self._conn:
            self._conn.close()

    # ---------- helpers ----------
    @staticmethod
    def _as_int(x) -> Optional[int]:
        if x is None or x == "":
            return None
        try:
            return int(x)
        except Exception:
            try:
                return int(float(x))
            except Exception:
                return None

    @staticmethod
    def _escape_like(s: str) -> str:
        # 转义 SQLite LIKE 特殊字符 % _
        return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    # ---------- writes ----------
    def upsert_history(
        self,
        platform: str,
        items: Iterable[Mapping[str, Any]],
        *,
        topic_key_field: str | None = None,
        tags_join_from: str | None = None,
        extra_fields: list[str] | None = None
    ) -> int:
        """
        items 中通用字段（能取到多少取多少）：
          title, url, image_url, excerpt, heat_text, heat_value/num, rank, spans, scraped_at, extra...
        """
        extra_fields = extra_fields or []

        sql = """
        INSERT INTO hot_items_history
          (platform, topic_key, title, url, image_url, excerpt,
           heat_text, heat_value, rank, tags_text, scraped_at, scraped_date, extra_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(platform, url, scraped_date) DO UPDATE SET
          topic_key=excluded.topic_key,
          title=excluded.title,
          image_url=excluded.image_url,
          excerpt=excluded.excerpt,
          heat_text=excluded.heat_text,
          heat_value=excluded.heat_value,
          rank=excluded.rank,
          tags_text=excluded.tags_text,
          scraped_at=excluded.scraped_at,
          extra_json=excluded.extra_json
        """

        rows: list[tuple[Any, ...]] = []
        for it in items:
            title = (it.get("title") or "").strip()
            url = (it.get("url") or "").strip()
            scraped_at = (it.get("scraped_at") or "").strip()
            if not (title and url):
                continue

            # scraped_at 若缺失则用当前时间
            if not scraped_at:
                scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            scraped_date = scraped_at.split(" ")[0]

            image_url = it.get("image_url")
            excerpt = it.get("excerpt")
            heat_text = it.get("heat_text")
            heat_value = self._as_int(it.get("heat_value", it.get("num")))
            rank = self._as_int(it.get("rank"))

            tags_text = None
            if tags_join_from and isinstance(it.get(tags_join_from), (list, tuple)):
                tags = [str(x).strip() for x in it[tags_join_from] if str(x).strip()]
                tags_text = "|".join(tags) if tags else None

            topic_key = it.get(topic_key_field) if topic_key_field else None

            extra = {}
            for k in extra_fields:
                if k in it:
                    extra[k] = it[k]
            extra_json = json.dumps(extra, ensure_ascii=False) if extra else None

            rows.append((
                platform, topic_key, title, url, image_url, excerpt,
                heat_text, heat_value, rank, tags_text, scraped_at, scraped_date, extra_json
            ))

        if not rows:
            return 0

        cur = self._conn.executemany(sql, rows)
        self._conn.commit()
        return cur.rowcount

    # ---------- reads ----------
    def list_platforms(self) -> list[str]:
        cur = self._conn.execute(
            "SELECT DISTINCT platform FROM hot_items_history ORDER BY platform;"
        )
        return [r[0] for r in cur.fetchall() if r and r[0]]

    def count_history(
        self,
        *,
        keyword: str | None = None,
        platforms: Sequence[str] | None = None,
        date_from: str | None = None,   # "YYYY-MM-DD"
        date_to: str | None = None      # "YYYY-MM-DD"
    ) -> int:
        sql = "SELECT COUNT(*) FROM hot_items_history WHERE 1=1"
        params: list[Any] = []

        if platforms:
            placeholders = ",".join("?" for _ in platforms)
            sql += f" AND platform IN ({placeholders})"
            params.extend(platforms)

        if keyword:
            kw = f"%{self._escape_like(keyword)}%"
            sql += " AND (title LIKE ? ESCAPE '\\' OR excerpt LIKE ? ESCAPE '\\' OR url LIKE ? ESCAPE '\\')"
            params.extend([kw, kw, kw])

        if date_from:
            sql += " AND scraped_date >= ?"
            params.append(date_from)
        if date_to:
            sql += " AND scraped_date <= ?"
            params.append(date_to)

        cur = self._conn.execute(sql, params)
        return int(cur.fetchone()[0])

    def query_history(
        self,
        *,
        keyword: str | None = None,
        platforms: Sequence[str] | None = None,
        date_from: str | None = None,   # "YYYY-MM-DD"
        date_to: str | None = None,     # "YYYY-MM-DD"
        order_by: str = "scraped_at DESC",   # 或 heat_value DESC / rank ASC 等
        limit: int = 50,
        offset: int = 0
    ) -> list[dict[str, Any]]:
        """
        返回列表，每条包含：
        id, platform, scraped_date, scraped_at, rank, title, url, heat_text, heat_value, excerpt, image_url, tags_text
        """
        if order_by not in self._ALLOWED_ORDERS:
            order_by = "scraped_at DESC"

        sql = """
        SELECT id, platform, scraped_date, scraped_at, rank, title, url,
               heat_text, heat_value, excerpt, image_url, tags_text
        FROM hot_items_history
        WHERE 1=1
        """
        params: list[Any] = []

        if platforms:
            placeholders = ",".join("?" for _ in platforms)
            sql += f" AND platform IN ({placeholders})"
            params.extend(platforms)

        if keyword:
            kw = f"%{self._escape_like(keyword)}%"
            sql += " AND (title LIKE ? ESCAPE '\\' OR excerpt LIKE ? ESCAPE '\\' OR url LIKE ? ESCAPE '\\')"
            params.extend([kw, kw, kw])

        if date_from:
            sql += " AND scraped_date >= ?"
            params.append(date_from)
        if date_to:
            sql += " AND scraped_date <= ?"
            params.append(date_to)

        sql += f" ORDER BY {order_by} LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cur = self._conn.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


