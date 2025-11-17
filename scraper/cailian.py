# scraper/cailian.py
# -*- coding: utf-8 -*-
from __future__ import annotations
import requests
from datetime import datetime
from typing import List, Dict, Any


class CailianHotSpider:
    """
    财联社电报爬虫（最简洁版本）。

    返回的字段完全适配 HotItemsHistoryDB：
      {
        "rank": None,
        "title": "...",
        "excerpt": "...",      # brief → excerpt
        "content": "...",
        "heat_text": "...",    # 字符串热度
        "heat_value": 12345,   # read_num → 数值热度
        "url": "...",
        "scraped_at": "YYYY-MM-DD HH:MM:SS",

        # 以下为 extra_json 字段
        "id": ...(int),
        "ctime": ...(int),
        "level": "...",
        "comment_num": ...,
      }
    """

    def __init__(self):
        self.url = "https://www.cls.cn/nodeapi/telegraphList?"
        self.headers = {
            "authority": "www.cls.cn",
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN,zh;q=0.9",
            "referer": "https://www.cls.cn/telegraph",
            "user-agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.6778.86 Safari/537.36"
            ),
        }

    # ----------------------------
    def fetch_page(self):
        try:
            resp = requests.get(self.url, headers=self.headers, timeout=10)
            data = resp.json()
        except Exception as e:
            print("❌ 财联社请求失败:", e)
            return []

        if data.get("error") != 0:
            print("❌ 财联社返回错误:", data)
            return []

        return data.get("data", {}).get("roll_data", [])

    # ----------------------------
    def normalize(self, it: Dict[str, Any], scraped_at: str) -> Dict[str, Any]:
        title = it.get("title") or ""
        brief = it.get("brief") or ""
        content = it.get("content") or ""

        # read_num 作为热度
        read_num = it.get("reading_num") or 0

        # URL
        url = it.get("shareurl") or ""
        if not url:
            aid = it.get("id")
            if aid:
                url = f"https://api3.cls.cn/share/article/{aid}?os=web&app=CailianpressWeb"

        return {
            # =========== 标准字段 ===========
            "rank": None,
            "title": title,
            "excerpt": brief,  # brief → excerpt
            "content": content,
            "heat_text": str(read_num),  # 字符串热度
            "heat_value": read_num,  # 数值热度 → read_num
            "url": url,
            "scraped_at": scraped_at,

            # =========== 财联社特有（入 extra_json） ===========
            "id": it.get("id"),
            "ctime": it.get("ctime"),
            "level": it.get("level"),
            "comment_num": it.get("comment_num"),
        }

    # ----------------------------
    def run(self) -> List[Dict[str, Any]]:
        raw_items = self.fetch_page()
        scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return [self.normalize(it, scraped_at) for it in raw_items]


if __name__ == "__main__":
    spider = CailianHotSpider()
    data = spider.run()
    print("抓取", len(data), "条")
    for d in data[:3]:
        print(d["title"], d["heat_value"], d["url"])