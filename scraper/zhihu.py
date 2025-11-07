# zhihu_scraper.py
# -*- coding: utf-8 -*-
from __future__ import annotations
import time
from typing import Any, Dict, List, Optional

import requests


class ZhihuHotSpider:
    """
    知乎热榜爬虫

    使用示例:
        spider = ZhihuHotSpider()
        items = spider.run()
    返回的每条 item:
        {
          "rank": 1,
          "title": "...",
          "answer_count": 123,
          "follower_count": 456,
          "heat_text": "23.00 万",
          "url": "https://www.zhihu.com/question/xxxxxx",
          "excerpt": "...",
          "scraped_at": "2025-10-18 23:00:00"
        }
    """

    def __init__(self, limit: int = 50) -> None:
        self.limit = limit
        # 两个 API 都保留，一条挂了换另一条
        self.candidate_endpoints = [
            ("https://api.zhihu.com/topstory/hot-list", {"limit": str(limit), "reverse_order": "0"}),
            ("https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total", {"limit": str(limit)}),
        ]
        self.headers = {
            "User-Agent": (
                "osee2unifiedRelease/4318 osee2unifiedReleaseVersion/7.7.0 "
                "Mozilla/5.0 (iPhone; CPU iPhone OS 14_4_2 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
            )
        }

    # ===== 工具 =====
    @staticmethod
    def _now(fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
        return time.strftime(fmt, time.localtime())

    @staticmethod
    def _parse_heat_to_wan(detail_text: str) -> Optional[str]:
        """
        将“123 万热度”/“8.5万”/“热度 45 万”等解析为字符串“xx.xx 万”
        若原文不含“万”，自动除以10000后加“万”
        """
        if not detail_text:
            return None
        s = detail_text.replace(",", "").replace(" ", "")
        num = ""
        for ch in s:
            if ch.isdigit() or ch == ".":
                num += ch
        if not num:
            return None
        val = float(num)
        # 如果原文不含“万”，按数量除以10000再加“万”
        if "万" not in s:
            val = val / 10000
        return f"{val:.2f} 万"

    # ===== 核心步骤 =====
    def fetch_json(self) -> Dict[str, Any] | None:
        """
        轮询两个知乎热榜接口，返回第一个成功的 json
        """
        for url, params in self.candidate_endpoints:
            try:
                resp = requests.get(url, headers=self.headers, params=params, timeout=12)
                resp.raise_for_status()
                return resp.json()
            except Exception:
                continue
        return None

    def parse_items(self, js: Dict[str, Any]) -> List[Dict[str, Any]]:
        data = js.get("data", [])
        now = self._now()
        items: List[Dict[str, Any]] = []

        for rank, item in enumerate(data, start=1):
            if not isinstance(item, dict):
                continue

            # 有的在 item["target"] 里，有的直接在 item 里
            target = item.get("target")
            if not isinstance(target, dict):
                target = item

            title = target.get("title")
            if not title:
                continue

            answer_count = target.get("answer_count")
            follower_count = target.get("follower_count")
            excerpt = target.get("excerpt")

            # question url 处理
            raw_url = target.get("url") or ""
            if raw_url:
                # api -> www
                question_url = raw_url.replace("api", "www").replace("questions", "question")
            else:
                qid = target.get("id")
                question_url = f"https://www.zhihu.com/question/{qid}" if qid else None

            # 热度
            heat_text_raw = item.get("detail_text") or item.get("detail_texts") or ""
            heat_text = self._parse_heat_to_wan(str(heat_text_raw))

            items.append(
                {
                    "rank": rank,
                    "title": title,
                    "answer_count": answer_count,
                    "follower_count": follower_count,
                    "heat_text": heat_text,
                    "url": question_url,
                    "excerpt": excerpt,
                    "scraped_at": now,
                }
            )

        return items

    # ===== 对外 =====
    def run(self) -> List[Dict[str, Any]]:
        js = self.fetch_json()
        if js is None:
            print("[zhihu] 抓取失败，返回空列表")
            return []
        items = self.parse_items(js)
        # 如果调用时 limit 比 50 小，就截一下
        if self.limit and len(items) > self.limit:
            items = items[: self.limit]
        return items


# quick test
if __name__ == "__main__":
    spider = ZhihuHotSpider(limit=30)
    items = spider.run()
    print(f"共抓取 {len(items)} 条热榜")
    if items:
        for i in items[:5]:
            print(i["rank"], i["title"], i["heat_text"], i["url"])