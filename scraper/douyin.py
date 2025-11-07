# douyin_scraper.py
# 抖音热搜打开网站都没有图片的，因此不保存avatar
# -*- coding: utf-8 -*-
from __future__ import annotations
import os
from typing import Any, Dict, List, Optional
from urllib.parse import quote
from datetime import datetime

import requests


class DouyinHotSpider:
    """
    抖音热榜爬虫
    使用方式：
        spider = DouyinHotSpider()
        items = spider.run()
    每条 item 至少包含：
        title, url, heat_value, sentence_id, scraped_at
    """

    def __init__(
        self,
        url: Optional[str] = None,
        ua: Optional[str] = None,
        cookie: Optional[str] = None,
    ) -> None:
        # 支持从外面传，也支持读环境变量
        self.url = url or os.getenv(
            "DOUYIN_HOT_URL",
            "https://www.douyin.com/aweme/v1/web/hot/search/list/?device_platform=webapp&aid=6383&channel=channel_pc_web&detail_list=1&source=6&main_billboard_count=5&update_version_code=170400&pc_client_type=1&pc_libra_divert=Mac&support_h265=1&support_dash=1&cpu_core_num=8&version_code=170400&version_name=17.4.0&cookie_enabled=true&screen_width=1512&screen_height=982",
        )
        self.ua = ua or os.getenv(
            "DOUYIN_UA",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Safari/605.1.15",
        )
        self.cookie = cookie or os.getenv("DOUYIN_COOKIE", "")

    # ---------- 内部工具 ----------
    def _headers(self) -> Dict[str, str]:
        return {
            "User-Agent": self.ua,
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.douyin.com/hot",
            "Cookie": self.cookie,
        }

    def _proxies(self) -> Optional[Dict[str, str]]:
        # 环境变量控制是否走代理
        if os.getenv("USE_PROXY", "").lower() in ("1", "true", "yes"):
            proxy = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
            if proxy:
                return {"http": proxy, "https": proxy}
        return None

    @staticmethod
    def _build_url(sentence_id: str, word: str) -> str:
        """构造可点击的热榜详情地址"""
        return f"https://www.douyin.com/hot/{sentence_id}/{quote(word, safe='')}"

    # ---------- 核心步骤：请求 + 解析 ----------
    def fetch_json(self) -> Dict[str, Any]:
        """请求接口，拿到原始 JSON"""
        resp = requests.get(
            self.url,
            headers=self._headers(),
            timeout=20,
            proxies=self._proxies(),
        )
        resp.raise_for_status()
        return resp.json()

    def parse_items(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从 JSON 里抽出我们要的字段"""
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        word_list = data.get("word_list", []) or []

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        items: List[Dict[str, Any]] = []

        for item in word_list:
            word = item.get("word")
            sentence_id = item.get("sentence_id")
            if not (word and sentence_id):
                continue

            hot_value = item.get("hot_value")
            items.append(
                {
                    "title": str(word),
                    "url": self._build_url(str(sentence_id), str(word)),
                    "heat_value": hot_value,
                    "sentence_id": str(sentence_id),
                    "scraped_at": now,
                }
            )

        # 按热度从高到低
        items.sort(key=lambda x: (x.get("heat_value") or 0), reverse=True)
        return items

    # ---------- 对外入口 ----------
    def run(self) -> List[Dict[str, Any]]:
        """一键跑完"""
        payload = self.fetch_json()
        return self.parse_items(payload)


# 测试用
if __name__ == "__main__":
    spider = DouyinHotSpider()
    hot_items = spider.run()
    for i, item in enumerate(hot_items, 1):
        print(f"{i}. {item['title']}  🔥{item['heat_value']}")
        print(f"   id={item['sentence_id']}  url={item['url']}  at={item['scraped_at']}")