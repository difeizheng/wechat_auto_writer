"""
热点追踪模块
从多个平台获取热门话题/热搜榜单
"""
import requests
import re
from typing import Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class HotTopic:
    """热点话题数据结构"""
    title: str
    rank: int
    hot_value: str  # 热度值，如 "1234567" 或 "328.5 万"
    url: str
    platform: str  # 来源平台
    summary: Optional[str] = None  # 话题摘要


class HotTopicTracker:
    """热点追踪器"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    def get_weibo_hot_search(self, limit: int = 10) -> list[HotTopic]:
        """
        获取微博热搜榜
        使用第三方 API 获取（不需要登录）
        """
        topics = []
        try:
            # 方案一：使用微博官方 API
            url = "https://weibo.com/ajax/side/hotSearch"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "Referer": "https://weibo.com/"
            }
            response = self.session.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("data") and data["data"].get("realtime"):
                    realtime_list = data["data"]["realtime"]
                    for i, item in enumerate(realtime_list[:limit], 1):
                        word = item.get("word", "")
                        if not word or "广告" in word:
                            continue
                        num = item.get("num", 0)
                        hot_value = f"{num // 10000}万" if num > 10000 else str(num)
                        topics.append(HotTopic(
                            title=word,
                            rank=i,
                            hot_value=hot_value,
                            url=f"https://s.weibo.com/weibo?q={word}",
                            platform="微博",
                            summary=item.get("note", "")[:100] if item.get("note") else None
                        ))
        except Exception as e:
            print(f"获取微博热搜失败（方案一）：{e}")

        # 方案一失败，使用备用方案
        if not topics:
            topics = self._get_weibo_hot_search_backup(limit)

        return topics[:limit]

    def _get_weibo_hot_search_backup(self, limit: int = 10) -> list[HotTopic]:
        """微博热搜备用获取方案 - 使用第三方 API"""
        topics = []
        try:
            # 方案二：使用第三方聚合 API
            url = "https://api.tophub.today/v1/weibo"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json"
            }
            response = self.session.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("data") and data["data"].get("list"):
                    for i, item in enumerate(data["data"]["list"][:limit], 1):
                        topics.append(HotTopic(
                            title=item.get("title", ""),
                            rank=i,
                            hot_value=item.get("hot", ""),
                            url=item.get("url", ""),
                            platform="微博"
                        ))
                return topics
        except Exception as e:
            print(f"获取微博热搜失败（方案二）：{e}")

        # 方案二也失败，使用方案三
        return self._get_weibo_hot_search_backup_v2(limit)

    def _get_weibo_hot_search_backup_v2(self, limit: int = 10) -> list[HotTopic]:
        """微博热搜备用方案二 - 使用另一第三方 API"""
        topics = []
        try:
            # 方案三：使用 another 第三方 API
            url = "https://tophub.today/api/v2/weibo/real-time"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json"
            }
            response = self.session.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("data") and data["data"].get("list"):
                    for i, item in enumerate(data["data"]["list"][:limit], 1):
                        topics.append(HotTopic(
                            title=item.get("title", ""),
                            rank=i,
                            hot_value=item.get("hot", ""),
                            url=item.get("url", ""),
                            platform="微博"
                        ))
        except Exception as e:
            print(f"获取微博热搜失败（方案三）：{e}")

        return topics[:limit]

    def get_zhihu_hot(self, limit: int = 10) -> list[HotTopic]:
        """
        获取知乎热榜
        使用公开 API（不需要认证）
        """
        topics = []
        try:
            # 方案一：使用知乎热榜官方 API
            url = "https://api.zhihu.com/topstory/hot-lists/total"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json"
            }
            response = self.session.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("data"):
                    for i, item in enumerate(data["data"][:limit], 1):
                        target = item.get("target", {})
                        topics.append(HotTopic(
                            title=target.get("title", ""),
                            rank=i,
                            hot_value=str(target.get("hot", 0)),
                            url=target.get("url", ""),
                            platform="知乎",
                            summary=target.get("excerpt", "")[:100] if target.get("excerpt") else None
                        ))
                return topics
        except Exception as e:
            print(f"获取知乎热榜失败（方案一）：{e}")

        # 方案一失败，使用备用方案
        return self._get_zhihu_hot_backup(limit)

    def _get_zhihu_hot_backup(self, limit: int = 10) -> list[HotTopic]:
        """知乎热榜备用方案 - 使用第三方 API"""
        topics = []
        try:
            # 方案二：使用第三方聚合 API
            url = "https://api.tophub.today/v1/zhihu"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json"
            }
            response = self.session.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("data") and data["data"].get("list"):
                    for i, item in enumerate(data["data"]["list"][:limit], 1):
                        topics.append(HotTopic(
                            title=item.get("title", ""),
                            rank=i,
                            hot_value=item.get("hot", ""),
                            url=item.get("url", ""),
                            platform="知乎"
                        ))
        except Exception as e:
            print(f"获取知乎热榜失败（方案二）：{e}")

        return topics[:limit]

    def get_baidu_hot(self, limit: int = 10) -> list[HotTopic]:
        """
        获取百度热搜榜
        使用第三方 API 获取
        """
        topics = []
        try:
            # 方案一：尝试使用百度热榜官方 API
            url = "https://top.baidu.com/api/boarddata"
            params = {
                "boardId": "1",
                "timestamp": int(datetime.now().timestamp())
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "Referer": "https://top.baidu.com/board"
            }
            response = self.session.get(url, params=params, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("data") and data["data"].get("items"):
                    items = data["data"]["items"]
                    for i, item in enumerate(items[:limit], 1):
                        topics.append(HotTopic(
                            title=item.get("word", item.get("query", "")),
                            rank=item.get("rank", i),
                            hot_value=item.get("hotScore", item.get("num", "")),
                            url=item.get("url", f"https://www.baidu.com/s?wd={item.get('word', '')}"),
                            platform="百度"
                        ))
                return topics[:limit]
        except Exception as e:
            print(f"获取百度热搜失败（方案一）：{e}")

        # 方案一失败，使用备用方案
        return self._get_baidu_hot_backup(limit)

    def _get_baidu_hot_backup(self, limit: int = 10) -> list[HotTopic]:
        """百度热搜备用方案 - 使用第三方 API"""
        topics = []
        try:
            # 方案二：使用第三方聚合 API
            url = "https://api.tophub.today/v1/baidu"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json"
            }
            response = self.session.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("data") and data["data"].get("list"):
                    for i, item in enumerate(data["data"]["list"][:limit], 1):
                        topics.append(HotTopic(
                            title=item.get("title", ""),
                            rank=i,
                            hot_value=item.get("hot", ""),
                            url=item.get("url", ""),
                            platform="百度"
                        ))
                return topics
        except Exception as e:
            print(f"获取百度热搜失败（方案二）：{e}")

        # 方案二也失败，使用知乎热榜作为替代
        print("百度热搜不可用，使用知乎热榜替代...")
        return self._get_alternative_hot_topics(limit)

    def _get_alternative_hot_topics(self, limit: int = 10) -> list[HotTopic]:
        """获取替代热点（当主要平台不可用时）"""
        topics = []
        try:
            # 尝试获取 36 氪热点（科技类）
            url = "https://api.36kr.com/w/api/article/recommend"
            data = self.session.post(
                url,
                json={"partner_id": "wap", "siteId": "1", "page": 1},
                timeout=10
            ).json()

            if data.get("data") and data["data"].get("hotRankList"):
                for item in data["data"]["hotRankList"][:limit]:
                    topics.append(HotTopic(
                        title=item.get("templateTitle", ""),
                        rank=item.get("rank", len(topics) + 1),
                        hot_value="",
                        url=f"https://36kr.com/p/{item.get('itemId', '')}",
                        platform="36 氪"
                    ))
        except:
            pass

        return topics

    def _get_baidu_hot_backup(self, limit: int = 10) -> list[HotTopic]:
        """百度热搜备用方案"""
        return []

    def get_douyin_hot(self, limit: int = 10) -> list[HotTopic]:
        """
        获取抖音热榜
        """
        topics = []
        try:
            # 方案一：使用抖音热榜 API
            url = "https://aweme.snssdk.com/aweme/v1/hot/search/list"
            params = {
                "aid": "1128",
                "version_code": "27.0.0"
            }
            headers = {
                "User-Agent": "com.ss.android.ugc.aweme",
                "Accept": "application/json"
            }
            response = self.session.get(url, params=params, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("data") and data["data"].get("word_list"):
                    for i, item in enumerate(data["data"]["word_list"][:limit], 1):
                        hot_words = item.get("word", "")
                        hot_value = item.get("hot_value", "")
                        if hot_value:
                            hot_value = f"{hot_value // 10000}万" if hot_value > 10000 else str(hot_value)
                        topics.append(HotTopic(
                            title=hot_words,
                            rank=item.get("rank", i),
                            hot_value=str(hot_value) if hot_value else "",
                            url=f"https://www.douyin.com/search/{hot_words}",
                            platform="抖音"
                        ))
                return topics
        except Exception as e:
            print(f"获取抖音热榜失败（方案一）：{e}")

        # 方案一失败，使用备用方案
        return self._get_douyin_hot_backup(limit)

    def _get_douyin_hot_backup(self, limit: int = 10) -> list[HotTopic]:
        """抖音热榜备用方案 - 使用第三方 API"""
        topics = []
        try:
            # 方案二：使用第三方聚合 API
            url = "https://api.tophub.today/v1/douyin"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json"
            }
            response = self.session.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("data") and data["data"].get("list"):
                    for i, item in enumerate(data["data"]["list"][:limit], 1):
                        topics.append(HotTopic(
                            title=item.get("title", ""),
                            rank=i,
                            hot_value=item.get("hot", ""),
                            url=item.get("url", ""),
                            platform="抖音"
                        ))
        except Exception as e:
            print(f"获取抖音热榜失败（方案二）：{e}")

        return topics[:limit]

    def get_36kr_hot(self, limit: int = 10) -> list[HotTopic]:
        """
        获取 36 氪热榜（科技类）
        """
        topics = []
        try:
            # 方案一：使用 36 氪官方 API
            url = "https://gateway.36kr.com/api/mis/nav/home/t/rank/hot"
            headers = {
                "Content-Type": "application/json",
                "User-Agent": self.session.headers["User-Agent"]
            }
            response = self.session.post(
                url,
                json={"partner_id": "wap", "siteId": "1"},
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("data") and data["data"].get("hotRankList"):
                    for i, item in enumerate(data["data"]["hotRankList"][:limit], 1):
                        topics.append(HotTopic(
                            title=item.get("templateTitle", ""),
                            rank=i,
                            hot_value="",
                            url=f"https://36kr.com/p/{item.get('itemId', '')}",
                            platform="36 氪"
                        ))
                return topics
        except Exception as e:
            print(f"获取 36 氪热榜失败（方案一）：{e}")

        # 方案一失败，使用备用方案
        return self._get_36kr_hot_backup(limit)

    def _get_36kr_hot_backup(self, limit: int = 10) -> list[HotTopic]:
        """36 氪热榜备用方案"""
        topics = []
        try:
            # 方案二：使用另一 API 端点
            url = "https://api.36kr.com/w/api/article/recommend"
            data = self.session.post(
                url,
                json={"partner_id": "wap", "siteId": "1", "page": 1},
                timeout=10
            ).json()

            if data.get("data") and data["data"].get("hotRankList"):
                for item in data["data"]["hotRankList"][:limit]:
                    topics.append(HotTopic(
                        title=item.get("templateTitle", ""),
                        rank=item.get("rank", len(topics) + 1),
                        hot_value="",
                        url=f"https://36kr.com/p/{item.get('itemId', '')}",
                        platform="36 氪"
                    ))
        except Exception as e:
            print(f"获取 36 氪热榜失败（方案二）：{e}")

        return topics[:limit]

    def get_all_hot_topics(self, limit_per_platform: int = 5) -> dict[str, list[HotTopic]]:
        """
        获取所有平台的热榜
        返回：{platform_name: [topics]}
        """
        results = {}

        # 微博热搜（最可靠）
        weibo = self.get_weibo_hot_search(limit_per_platform)
        if weibo:
            results["微博"] = weibo

        # 抖音热榜
        douyin = self.get_douyin_hot(limit_per_platform)
        if douyin:
            results["抖音"] = douyin

        # 知乎热榜
        zhihu = self.get_zhihu_hot(limit_per_platform)
        if zhihu:
            results["知乎"] = zhihu

        # 百度热搜
        baidu = self.get_baidu_hot(limit_per_platform)
        if baidu:
            results["百度"] = baidu

        # 36 氪（科技类）
        _36kr = self.get_36kr_hot(limit_per_platform)
        if _36kr:
            results["36 氪"] = _36kr

        return results

    def get_recommended_topics(self, limit: int = 5) -> list[HotTopic]:
        """
        获取推荐热点（综合各平台热度排序）
        """
        all_topics = self.get_all_hot_topics(limit_per_platform=10)

        # 合并所有平台的热点
        merged = []
        for platform, topics in all_topics.items():
            merged.extend(topics)

        # 按 rank 排序，取前 N 个
        merged.sort(key=lambda x: x.rank)
        return merged[:limit]


def format_topics_for_prompt(topics: dict[str, list[HotTopic]], max_per_platform: int = 3) -> str:
    """
    将热点话题格式化为 AI 提示词
    """
    if not topics:
        return "当前暂无热点数据"

    lines = ["以下是当前各平台的热门话题：\n"]

    for platform, platform_topics in topics.items():
        lines.append(f"【{platform}】")
        for topic in platform_topics[:max_per_platform]:
            hot_text = f" (🔥 {topic.hot_value})" if topic.hot_value else ""
            lines.append(f"  {topic.rank}. {topic.title}{hot_text}")
        lines.append("")

    return "\n".join(lines)


# 单例
_tracker_instance = None

def get_tracker() -> HotTopicTracker:
    """获取热点追踪器单例"""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = HotTopicTracker()
    return _tracker_instance
