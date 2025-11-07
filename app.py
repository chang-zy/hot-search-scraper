# app/pages/热榜历史.py
# -*- coding: utf-8 -*-
from __future__ import annotations
import math
import os
import sqlite3
from datetime import date
from typing import Any, List

import streamlit as st
from storage import HotItemsHistoryDB

DEFAULT_DB_PATH = "hot.db"

st.set_page_config(page_title="🔥 热榜历史查询", layout="wide")
st.title("📚 热榜历史记录")


def get_db() -> HotItemsHistoryDB:
    if not os.path.exists(DEFAULT_DB_PATH):
        raise FileNotFoundError(f"未找到数据库文件：{DEFAULT_DB_PATH}")
    conn = sqlite3.connect(DEFAULT_DB_PATH, check_same_thread=False)
    return HotItemsHistoryDB(conn=conn)


db = get_db()

if "page_num" not in st.session_state:
    st.session_state.page_num = 1

# ================== 侧边栏筛选 ==================
st.sidebar.header("筛选条件")

try:
    platforms_all: List[str] = db.list_platforms()
except Exception as e:
    st.error(f"获取平台列表失败：{e}")
    platforms_all = []

# 英文 -> 中文
PLATFORM_LABELS = {
    "baidu": "百度",
    "weibo": "微博",
    "zhihu": "知乎",
    "douyin": "抖音",
}

plat_selected = st.sidebar.multiselect(
    "平台",
    options=platforms_all,
    default=platforms_all,
    format_func=lambda x: PLATFORM_LABELS.get(x, x),
)

keyword = st.sidebar.text_input("标题 / 摘要 / 链接包含", value="", placeholder="如：沙僧 僧人 去世…")

c1, c2 = st.sidebar.columns(2)
dfrom = c1.date_input("起始日期", value=None)
dto = c2.date_input("结束日期", value=None)
date_from = dfrom.isoformat() if isinstance(dfrom, date) else None
date_to = dto.isoformat() if isinstance(dto, date) else None

order_map = {
    "按抓取时间（最新→最旧）": "scraped_at DESC",
    "按抓取时间（最旧→最新）": "scraped_at ASC",
    "按热度（高→低）": "heat_value DESC",
    "按热度（低→高）": "heat_value ASC",
    "按排名（低→高）": "rank ASC",
    "按排名（高→低）": "rank DESC",
}
order_label = st.sidebar.selectbox("排序方式", list(order_map.keys()), index=0)
order_by = order_map[order_label]

page_size = st.sidebar.selectbox("每页条数", [20, 50, 100, 200], index=1)

# ================== 查询 ==================
try:
    total = db.count_history(
        keyword=keyword or None,
        platforms=plat_selected or None,
        date_from=date_from,
        date_to=date_to,
    )
except Exception as e:
    st.error(f"统计数据失败：{e}")
    total = 0

total_pages = max(1, math.ceil(total / page_size))
st.session_state.page_num = min(max(1, st.session_state.page_num), total_pages)
current_page = st.session_state.page_num
offset = (current_page - 1) * page_size

try:
    rows = db.query_history(
        keyword=keyword or None,
        platforms=plat_selected or None,
        date_from=date_from,
        date_to=date_to,
        order_by=order_by,
        limit=page_size,
        offset=offset,
    )
except Exception as e:
    st.error(f"查询数据失败：{e}")
    rows = []

st.caption(f"共查询到 **{total}** 条记录 · 第 **{current_page}/{total_pages}** 页")

# ================== 样式 ==================
st.markdown(
    """
<style>
.card-grid{
  display:flex;
  flex-direction:column;
  gap:16px;
}
.hot-card{
  border:1px solid rgba(0,0,0,0.05);
  border-radius:16px;
  padding:16px 18px;
  background:#fff;
  display:flex;
  gap:16px;
  align-items:flex-start;
}
.hot-card .card-left{
  flex:1 1 auto;
  min-width:0;
}
.hot-card .card-right{
  width:160px;
  text-align:right;
}
.hot-card .thumb{
  width:150px;
  height:auto;
  border-radius:10px;
  object-fit:cover;
}
.hot-card .title{
  font-size:1.15rem;
  font-weight:650;
  margin-bottom:8px;
  color:#134a8e;
}
.badges{
  display:flex;
  gap:8px;
  flex-wrap:wrap;
  margin-bottom:8px;
}
.badge{
  background:#f1f2f4;
  border-radius:999px;
  padding:3px 10px;
  font-size:12px;
  display:flex;
  gap:4px;
  align-items:center;
  color:#444;
}
.excerpt{
  font-size:13px;
  color:#333;
  line-height:1.55;
  margin-top:4px;
  word-break:break-word;
}
</style>
""",
    unsafe_allow_html=True,
)

# ================== 渲染卡片 ==================
def _fmt(v, default="—"):
    return v if (v is not None and str(v).strip()) else default

def render_cards(data: list[dict[str, Any]]):
    if not data:
        st.info("暂无数据，换个条件试试。")
        return

    st.markdown('<div class="card-grid">', unsafe_allow_html=True)
    for r in data:
        platform_en = _fmt(r.get("platform"))
        platform = PLATFORM_LABELS.get(platform_en, platform_en)

        title = _fmt(r.get("title"), "无标题")
        url = r.get("url") or ""
        rank = _fmt(r.get("rank"))
        scraped_date = _fmt(r.get("scraped_date"))
        scraped_at = _fmt(r.get("scraped_at"))
        excerpt = _fmt(r.get("excerpt"), "")
        image_url = _fmt(r.get("image_url"), "")
        heat_text = _fmt(r.get("heat_text"))
        hv_raw = r.get("heat_value")

        # 热度数值 -> “万”
        heat_display = heat_text
        try:
            hv = float(hv_raw)
            heat_display = f"{hv/10000:.0f}万" if hv >= 10000 else f"{hv:.0f}"
        except Exception:
            pass

        # 标题可点击
        if url:
            title_html = f'<a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a>'
        else:
            title_html = title

        # 左半部分
        left_html = (
            f'<div class="card-left">'
            f'<div class="title">{title_html}</div>'
            f'<div class="badges">'
            f'<div class="badge">📌 {platform}</div>'
            f'<div class="badge">🏷 排名 {rank}</div>'
            f'<div class="badge">🔥 {heat_display}</div>'
            f'<div class="badge">📅 {scraped_date}</div>'
            f'<div class="badge">⏱ {scraped_at}</div>'
            f'</div>'
        )
        if excerpt and excerpt != "—":
            left_html += f'<div class="excerpt">{excerpt}</div>'
        left_html += '</div>'

        # 右半部分（图片可选）
        if image_url and image_url != "—":
            right_html = f'<div class="card-right"><img src="{image_url}" class="thumb"></div>'
        else:
            right_html = '<div class="card-right"></div>'

        card_html = f'<div class="hot-card">{left_html}{right_html}</div>'
        st.markdown(card_html, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


render_cards(rows)

# ================== 分页 ==================
st.markdown("---")
c1, c2, c3, c4, c5, c6 = st.columns([1, 1, 2, 1, 1, 3])

with c1:
    if st.button("« 首页", use_container_width=True, disabled=(current_page <= 1)):
        st.session_state.page_num = 1
        st.rerun()

with c2:
    if st.button("‹ 上一页", use_container_width=True, disabled=(current_page <= 1)):
        st.session_state.page_num = current_page - 1
        st.rerun()

with c3:
    st.write(f"第 **{current_page} / {total_pages}** 页 · 每页 **{page_size}** 条 · 共 **{total}** 条")

with c4:
    if st.button("下一页 ›", use_container_width=True, disabled=(current_page >= total_pages)):
        st.session_state.page_num = current_page + 1
        st.rerun()

with c5:
    if st.button("末页 »", use_container_width=True, disabled=(current_page >= total_pages)):
        st.session_state.page_num = total_pages
        st.rerun()

with c6:
    jump = st.number_input("跳转页码", min_value=1, max_value=total_pages, value=current_page, step=1, label_visibility="collapsed")
    if jump != current_page:
        st.session_state.page_num = int(jump)
        st.rerun()

st.caption("💡 左侧可以选择平台（百度/微博/知乎/抖音），卡片右侧有图的会自动显示。")

db.close()