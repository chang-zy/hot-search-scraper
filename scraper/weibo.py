# -*- coding: utf-8 -*-
"""
weibo_spider.py
从 https://weibo.com/ajax/side/hotSearch 拉取热搜

用法：
    python weibo_spider.py

说明：
    - 直接在代码里设置 WEIBO_COOKIE 常量（不需要环境变量）
    - 可在其他脚本中：from weibo_spider import WeiboHotSpider
      然后 spider = WeiboHotSpider(); items = spider.run()
"""

from __future__ import annotations
import re
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import quote
import requests


# ✅ 直接在这里填写 Cookie 常量（复制自浏览器）
WEIBO_COOKIE = (
    "WBPSESS=_IPkQSuPgMknpTQxCFh5ac2xY-GhpLFcBl0EouAp1a3tIJwS-1Z4AYJrucDnyLEN_JfnM97TT0yhb6dZoKbWXqzqiby8oH8JhiLrk0gPnDnUn4_i62iQDfOT2bBSgYHfZ6XAl03S3THWVoC6K8gBCg==; "
    "ALF=02_1762235358; SCF=ApBqptKSk7uHkMYofrYqgudShO_zXbk77tj2V7cfgNQORSYIINlBZzAdVjbo17cgazBhDuxETu5-EbCnYq7Hs-w.; "
    "SUB=_2A25F5naMDeRhGeBP6FAQ8SjOzzWIHXVmmvZErDV8PUNbmtAbLWnlkW9NRX4hT38uQ5MBd6tVjLPSbByGzPHuDn1E; "
    "SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9Wh_SESzKucZOIurUnHJ5lij5NHD95QceKeEeK2ceoB4Ws4DqcjKi--Xi-ihiKLWi--ciK.Ni-zcHntt; "
    "Apache=6139712352594.591.1759643318001; SINAGLOBAL=6139712352594.591.1759643318001; "
    "ULV=1759643318011:1:1:1:6139712352594.591.1759643318001:; _s_tentry=-; XSRF-TOKEN=2I7o1hSFjckoUFVo4RDuOt3G"
)


class WeiboHotSpider:
    API_URL = "https://weibo.com/ajax/side/hotSearch"
    REFERER = "https://weibo.com/hot/search"
    UA = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/18.6 Safari/605.1.15"
    )

    def __init__(self, session: Optional[requests.Session] = None) -> None:
        if not WEIBO_COOKIE.strip():
            raise RuntimeError("❌ 请先在 weibo_spider.py 顶部填写 WEIBO_COOKIE 常量！")
        self.cookie = WEIBO_COOKIE.strip()
        self.session = session or requests.Session()

    # ========= 工具函数 =========
    @staticmethod
    def _parse_heat_value(num: Any) -> Optional[int]:
        if num is None:
            return None
        s = str(num).strip()
        if not s:
            return None

        m = re.match(r"^\s*([\d\.]+)\s*(万|亿)?\s*$", s)
        if not m:
            try:
                return int(float(s))
            except Exception:
                return None

        val = float(m.group(1))
        unit = m.group(2)
        if unit == "万":
            val *= 1e4
        elif unit == "亿":
            val *= 1e8
        return int(val)

    @staticmethod
    def _safe_q(word_scheme: str) -> str:
        if "%" in (word_scheme or ""):
            return word_scheme
        return quote(word_scheme or "", safe="")

    @staticmethod
    def _extract_xsrf_token(cookie: str) -> Optional[str]:
        m = re.search(r"\bXSRF-TOKEN=([^;]+)", cookie)
        return m.group(1) if m else None

    def _headers(self) -> Dict[str, str]:
        xsrf = self._extract_xsrf_token(self.cookie)
        h = {
            "User-Agent": self.UA,
            "Accept": "application/json, text/plain, */*",
            "Referer": self.REFERER,
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Cookie": self.cookie,
            "X-Requested-With": "XMLHttpRequest",
            "client-version": "v2.47.121",
            "server-version": "v2025.10.02.1",
        }
        if xsrf:
            h["X-XSRF-TOKEN"] = xsrf
        return h

    # ========= 核心逻辑 =========
    def fetch_json(self) -> Dict[str, Any]:
        headers = self._headers()
        r = self.session.get(self.API_URL, headers=headers, timeout=15)
        if r.status_code == 403:
            raise RuntimeError("403 Forbidden：Cookie 或 XSRF 头无效/过期。请从浏览器重新复制 Cookie。")
        r.raise_for_status()
        return r.json()

    def parse_items(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        realtime = (data or {}).get("data", {}).get("realtime", []) or []
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        out: List[Dict[str, Any]] = []

        for item in realtime:
            title = item.get("note", "") or ""
            num = item.get("num", "")
            heat_text = str(num) if num is not None else ""
            heat_value = self._parse_heat_value(num)
            word_scheme = item.get("word_scheme", "") or ""
            q = self._safe_q(word_scheme)
            url = f"https://s.weibo.com/weibo?q={q}&t=31"

            out.append(
                {
                    "title": title,
                    "url": url,
                    "heat_text": heat_text,
                    "heat_value": heat_value,
                    "scraped_at": now,
                    "word_scheme": word_scheme,
                }
            )
        return out

    # ========= 对外入口 =========
    def run(self) -> List[Dict[str, Any]]:
        js = self.fetch_json()
        return self.parse_items(js)


# ========== 命令行调试 ==========
def main():
    try:
        spider = WeiboHotSpider()
        items = spider.run()
    except Exception as e:
        sys.stderr.write(f"❌ 抓取失败：{e}\n")
        sys.exit(1)

    if not items:
        sys.stderr.write("⚠️ 接口返回为空，可能 Cookie 失效或被风控。\n")
        sys.exit(2)

    for it in items:
        print(f"{it['url']}\t{it['title']}\t{it['heat_text']}")


if __name__ == "__main__":
    main()