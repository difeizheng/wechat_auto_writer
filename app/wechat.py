"""
微信公众号 API 封装
"""
import os
import hashlib
import time
import requests
from typing import Optional
from pathlib import Path


class WeChatAPI:
    """微信公众号 API 封装"""

    def __init__(
        self,
        app_id: Optional[str] = None,
        app_secret: Optional[str] = None
    ):
        self.app_id = app_id or os.getenv("WECHAT_APP_ID")
        self.app_secret = app_secret or os.getenv("WECHAT_APP_SECRET")
        self._access_token = None
        self._token_expires_at = 0

    def _get_access_token(self) -> str:
        """获取 access_token"""
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        url = "https://api.weixin.qq.com/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": self.app_id,
            "secret": self.app_secret
        }

        response = requests.get(url, params=params)
        data = response.json()

        if "access_token" in data:
            self._access_token = data["access_token"]
            self._token_expires_at = time.time() + data["expires_in"] - 300
            return self._access_token
        else:
            raise Exception(f"获取 access_token 失败：{data}")

    def upload_temporary_media(
        self,
        file_path: str,
        media_type: str = "image"
    ) -> str:
        """
        上传临时素材（3 天有效期）
        返回 media_id
        """
        token = self._get_access_token()
        url = f"https://api.weixin.qq.com/cgi-bin/media/upload"

        files = {"media": open(file_path, "rb")}
        params = {
            "access_token": token,
            "type": media_type
        }

        response = requests.post(url, params=params, files=files)
        data = response.json()

        if "media_id" in data:
            return data["media_id"]
        else:
            raise Exception(f"上传素材失败：{data}")

    def upload_permanent_media(
        self,
        file_path: str,
        media_type: str = "image"
    ) -> dict:
        """
        上传永久素材（订阅号/服务号认证后可用）
        返回 {"media_id": ..., "url": ...}
        """
        token = self._get_access_token()
        url = f"https://api.weixin.qq.com/cgi-bin/material/add_material"

        files = {"media": open(file_path, "rb")}
        params = {
            "access_token": token,
            "type": media_type
        }

        response = requests.post(url, params=params, files=files)
        data = response.json()

        if "media_id" in data:
            return data
        else:
            raise Exception(f"上传永久素材失败：{data}")

    def publish_article(
        self,
        title: str,
        content: str,
        cover_media_id: Optional[str] = None,
        author: Optional[str] = None,
        digest: Optional[str] = None,
        show_cover: bool = True
    ) -> dict:
        """
        发布文章（需要先有永久素材权限）
        """
        token = self._get_access_token()
        url = f"https://api.weixin.qq.com/cgi-bin/material/add_news"

        # 将 Markdown 转换为 HTML（简单处理，实际可能需要更完善的转换）
        import markdown
        html_content = markdown.markdown(
            content,
            extensions=['extra', 'codehilite']
        )

        data = {
            "articles": [{
                "title": title,
                "content": html_content,
                "author": author or "",
                "digest": digest or "",
                "show_cover": 1 if show_cover else 0
            }]
        }

        if cover_media_id:
            data["articles"][0]["thumb_media_id"] = cover_media_id

        params = {"access_token": token}
        response = requests.post(url, json=data, params=params)
        result = response.json()

        if "media_id" in result:
            return result
        else:
            raise Exception(f"发布文章失败：{result}")

    def send_preview(
        self,
        media_id: str,
        to_user: str
    ) -> dict:
        """
        发送预览给用户
        """
        token = self._get_access_token()
        url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send"

        data = {
            "touser": to_user,
            "msgtype": "mpnews",
            "mpnews": {
                "media_id": media_id
            }
        }

        params = {"access_token": token}
        response = requests.post(url, json=data, params=params)
        return response.json()


def markdown_to_wechat_html(markdown_content: str) -> str:
    """
    将 Markdown 转换为微信公众号友好的 HTML
    可以自定义样式以符合公众号排版规范
    """
    import markdown

    # 自定义 CSS 样式
    css_style = """
    <style>
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        font-size: 16px;
        line-height: 1.75;
        color: #333;
        padding: 0 12px;
    }
    h1, h2, h3 {
        color: #1E88E5;
        margin-top: 24px;
        margin-bottom: 16px;
    }
    h1 { font-size: 20px; border-bottom: 2px solid #1E88E5; padding-bottom: 8px; }
    h2 { font-size: 18px; border-left: 4px solid #1E88E5; padding-left: 12px; }
    h3 { font-size: 16px; }
    p { margin: 16px 0; }
    code {
        background-color: #f5f5f5;
        padding: 2px 6px;
        border-radius: 4px;
        font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
        font-size: 14px;
    }
    pre {
        background-color: #f6f8fa;
        padding: 16px;
        border-radius: 6px;
        overflow-x: auto;
        font-size: 14px;
    }
    blockquote {
        border-left: 4px solid #ddd;
        padding-left: 16px;
        color: #666;
        margin: 16px 0;
    }
    ul, ol { padding-left: 24px; }
    li { margin: 8px 0; }
    a { color: #1E88E5; text-decoration: none; }
    strong { color: #000; }
    </style>
    """

    html_content = markdown.markdown(
        markdown_content,
        extensions=['extra', 'codehilite', 'tables']
    )

    return css_style + html_content
