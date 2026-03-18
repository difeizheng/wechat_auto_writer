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


def markdown_to_wechat_html(markdown_content: str, theme_color: str = "#1E88E5") -> str:
    """
    将 Markdown 转换为微信公众号友好的 HTML
    支持多种主题颜色和精美排版样式
    """
    import markdown

    # 自定义 CSS 样式 - 优化版微信公众号排版
    css_style = f"""
    <style>
    /* 全局设置 */
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
        font-size: 16px;
        line-height: 1.8;
        color: #333;
        padding: 0 16px;
        max-width: 672px;
        margin: 0 auto;
        word-wrap: break-word;
    }}

    /* 标题样式 */
    h1 {{
        font-size: 22px;
        font-weight: 700;
        color: {theme_color};
        text-align: center;
        margin: 32px 0 20px;
        padding-bottom: 12px;
        border-bottom: 2px solid {theme_color};
        line-height: 1.4;
    }}

    h2 {{
        font-size: 18px;
        font-weight: 600;
        color: {theme_color};
        margin: 28px 0 14px;
        padding: 8px 0 8px 14px;
        border-left: 4px solid {theme_color};
        background: linear-gradient(to right, rgba(30,136,229,0.05), transparent);
        line-height: 1.4;
    }}

    h3 {{
        font-size: 16px;
        font-weight: 600;
        color: #2c3e50;
        margin: 24px 0 12px;
        padding-left: 12px;
        line-height: 1.4;
    }}

    h4 {{
        font-size: 15px;
        font-weight: 600;
        color: #34495e;
        margin: 20px 0 10px;
        line-height: 1.4;
    }}

    /* 段落样式 */
    p {{
        margin: 18px 0;
        text-align: justify;
        line-height: 1.9;
        color: #333;
    }}

    /* 引用块样式 */
    blockquote {{
        margin: 24px 0;
        padding: 16px 20px;
        border-left: none;
        border-radius: 8px;
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        position: relative;
        color: #555;
        font-style: normal;
    }}
    blockquote::before {{
        content: "\\201C";
        font-size: 48px;
        color: {theme_color};
        opacity: 0.2;
        position: absolute;
        top: -8px;
        left: 12px;
        font-family: Georgia, serif;
    }}

    /* 行内代码样式 */
    code {{
        background: #f5f7f9;
        padding: 3px 8px;
        border-radius: 4px;
        font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
        font-size: 14px;
        color: #e74c3c;
        border: 1px solid #e8ecef;
    }}

    /* 代码块样式 */
    pre {{
        background: #282c34;
        padding: 16px;
        border-radius: 8px;
        overflow-x: auto;
        font-size: 13px;
        line-height: 1.6;
        margin: 20px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }}
    pre code {{
        background: transparent;
        padding: 0;
        color: #abb2bf;
        border: none;
    }}

    /* 列表样式 */
    ul, ol {{
        padding-left: 24px;
        margin: 16px 0;
    }}
    li {{
        margin: 10px 0;
        line-height: 1.8;
        text-align: justify;
    }}
    ul > li::marker {{
        color: {theme_color};
    }}

    /* 链接样式 */
    a {{
        color: {theme_color};
        text-decoration: none;
        border-bottom: 1px dashed {theme_color};
        padding-bottom: 2px;
    }}
    a:hover {{
        opacity: 0.8;
    }}

    /* 强调文本样式 */
    strong, b {{
        color: {theme_color};
        font-weight: 600;
    }}

    /* 表格样式 */
    table {{
        width: 100%;
        border-collapse: collapse;
        margin: 20px 0;
        font-size: 14px;
    }}
    th {{
        background: {theme_color};
        color: white;
        padding: 12px 8px;
        text-align: left;
        font-weight: 600;
    }}
    td {{
        padding: 10px 8px;
        border-bottom: 1px solid #e0e0e0;
    }}
    tr:nth-child(even) {{
        background: #f8f9fa;
    }}

    /* 分割线样式 */
    hr {{
        border: none;
        height: 2px;
        background: linear-gradient(to right, transparent, {theme_color}, transparent);
        margin: 32px 0;
    }}

    /* 图片样式 */
    img {{
        max-width: 100%;
        height: auto;
        display: block;
        margin: 20px auto;
        border-radius: 8px;
    }}

    /* 重点框样式 */
    .highlight-box {{
        border: 2px solid {theme_color};
        border-radius: 8px;
        padding: 16px;
        margin: 20px 0;
        background: rgba(30,136,229,0.03);
    }}

    /* 提示框样式 */
    .tip-box {{
        background: linear-gradient(135deg, #fff3cd 0%, #ffe69c 100%);
        border-left: 4px solid #ffc107;
        border-radius: 6px;
        padding: 14px 16px;
        margin: 20px 0;
    }}

    /* 成功框样式 */
    .success-box {{
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        border-left: 4px solid #28a745;
        border-radius: 6px;
        padding: 14px 16px;
        margin: 20px 0;
    }}

    /* 警告框样式 */
    .warning-box {{
        background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
        border-left: 4px solid #dc3545;
        border-radius: 6px;
        padding: 14px 16px;
        margin: 20px 0;
    }}

    /* 底部关注引导样式 */
    .footer-guide {{
        text-align: center;
        margin-top: 40px;
        padding: 20px;
        background: linear-gradient(135deg, #f5f7fa 0%, #e4e8eb 100%);
        border-radius: 12px;
    }}
    </style>
    """

    html_content = markdown.markdown(
        markdown_content,
        extensions=['extra', 'codehilite', 'tables', 'nl2br']
    )

    # 添加一些自动美化处理
    # 将普通的 blockquote 转换为带样式的引用
    html_content = html_content.replace(
        '<blockquote>',
        '<blockquote>'
    )

    return css_style + html_content


def get_wechat_templates():
    """
    获取微信公众号排版模板
    返回多种预设样式模板
    """
    return {
        "default": {
            "name": "默认蓝",
            "theme_color": "#1E88E5",
            "description": "清爽蓝色主题，适合大多数场景"
        },
        "green": {
            "name": "清新绿",
            "theme_color": "#2E7D32",
            "description": "清新绿色主题，适合环保、健康类文章"
        },
        "orange": {
            "name": "活力橙",
            "theme_color": "#EF6C00",
            "description": "活力橙色主题，适合资讯、热点类文章"
        },
        "purple": {
            "name": "优雅紫",
            "theme_color": "#7B1FA2",
            "description": "优雅紫色主题，适合艺术、设计类文章"
        },
        "red": {
            "name": "中国红",
            "theme_color": "#C62828",
            "description": "中国红主题，适合节日、庆典类文章"
        },
        "dark": {
            "name": "商务黑",
            "theme_color": "#424242",
            "description": "深色商务主题，适合专业、严肃类文章"
        }
    }
