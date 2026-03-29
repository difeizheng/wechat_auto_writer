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
        发布文章（需要先有永久素材权限）- 旧接口，兼容用
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

    def submit_publish(self, media_id: str) -> dict:
        """
        提交发布（正式版发布接口）
        参考：https://developers.weixin.qq.com/doc/offiaccount/Publish/Publish.html

        Args:
            media_id: 要发布的图文消息 media_id（来自草稿箱或素材库）

        Returns:
            {"publish_id": 12345, "errcode": 0, "errmsg": "ok"}
        """
        token = self._get_access_token()
        url = "https://api.weixin.qq.com/cgi-bin/freepublish/submit"

        params = {"access_token": token}
        data = {
            "media_id": media_id  # 草稿箱或素材库的 media_id
        }

        response = requests.post(url, json=data, params=params)
        result = response.json()

        if result.get("errcode", 0) == 0:
            return result
        else:
            raise Exception(f"提交发布失败：{result}")

    def get_publish_status(self, publish_id: int) -> dict:
        """
        查询发布状态
        参考：https://developers.weixin.qq.com/doc/offiaccount/Publish/Get_status.html

        Args:
            publish_id: 提交发布后返回的 publish_id

        Returns:
            发布状态信息
        """
        token = self._get_access_token()
        url = "https://api.weixin.qq.com/cgi-bin/freepublish/get"

        params = {"access_token": token}
        data = {"publish_id": publish_id}

        response = requests.post(url, json=data, params=params)
        return response.json()

    def add_draft(
        self,
        title: str,
        content: str,
        cover_media_id: Optional[str] = None,
        author: Optional[str] = None,
        digest: Optional[str] = None,
        show_cover: bool = True,
        thumb_media_id: Optional[str] = None
    ) -> dict:
        """
        保存到草稿箱
        参考：https://developers.weixin.qq.com/doc/offiaccount/Draft_Box/Add_draft.html

        Args:
            title: 文章标题
            content: 文章内容（HTML 格式）
            cover_media_id: 封面图片 media_id（可选）
            author: 作者（可选）
            digest: 摘要（可选）
            show_cover: 是否显示封面 (1/0)
            thumb_media_id: 缩略图 media_id（必填）

        Returns:
            {"media_id": "xxxxx", "errcode": 0, "errmsg": "ok"}
        """
        token = self._get_access_token()
        url = "https://api.weixin.qq.com/cgi-bin/draft/add"

        params = {"access_token": token}

        # 构建文章数据
        article_data = {
            "title": title,
            "author": author or "",
            "content": content,  # 已经是 HTML 格式
            "show_cover_pic": 1 if show_cover else 0,
            "thumb_media_id": thumb_media_id
        }

        # digest 字段可选，如果不传微信会自动抓取正文前 54 个字
        # 只有当 digest 不为空时才添加该字段
        if digest:
            article_data["digest"] = digest

        data = {
            "articles": [article_data]
        }

        import json as _json
        response = requests.post(
            url,
            data=_json.dumps(data, ensure_ascii=False).encode('utf-8'),
            params=params,
            headers={"Content-Type": "application/json; charset=utf-8"}
        )

        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}: {response.text}")

        result = response.json()

        if result.get("errcode", 0) == 0:
            return result
        else:
            raise Exception(f"保存到草稿箱失败：{result}")

    def update_draft(
        self,
        media_id: str,
        index: int = 0,
        title: Optional[str] = None,
        content: Optional[str] = None,
        author: Optional[str] = None,
        digest: Optional[str] = None,
        show_cover: Optional[int] = None
    ) -> dict:
        """
        修改草稿箱文章
        参考：https://developers.weixin.qq.com/doc/offiaccount/Draft_Box/Update_draft.html
        """
        token = self._get_access_token()
        url = "https://api.weixin.qq.com/cgi-bin/draft/update"

        params = {"access_token": token}

        data = {
            "media_id": media_id,
            "index": index  # 多篇图文时指定第几篇，从 0 开始
        }

        if title is not None:
            data["title"] = title
        if content is not None:
            data["content"] = content
        if author is not None:
            data["author"] = author
        if digest is not None:
            data["digest"] = digest
        if show_cover is not None:
            data["show_cover"] = show_cover

        response = requests.post(url, json=data, params=params)
        result = response.json()

        if result.get("errcode", 0) == 0:
            return result
        else:
            raise Exception(f"修改草稿失败：{result}")

    def delete_draft(self, media_id: str) -> dict:
        """
        删除草稿
        """
        token = self._get_access_token()
        url = "https://api.weixin.qq.com/cgi-bin/draft/delete"

        params = {
            "access_token": token,
            "media_id": media_id
        }

        response = requests.post(url, json={"media_id": media_id}, params=params)
        result = response.json()

        if result.get("errcode", 0) == 0:
            return result
        else:
            raise Exception(f"删除草稿失败：{result}")

    def get_draft_list(self, offset: int = 0, count: int = 20, no_content: int = 0) -> dict:
        """
        获取草稿列表
        """
        token = self._get_access_token()
        url = "https://api.weixin.qq.com/cgi-bin/draft/batchget"

        params = {"access_token": token}
        data = {
            "offset": offset,
            "count": count,
            "no_content": no_content  # 是否返回内容 (0/1)
        }

        response = requests.post(url, json=data, params=params)
        return response.json()


class _WeChatHTMLTransformer:
    """将 markdown 生成的 HTML 转换为带内联样式的微信公众号 HTML。

    微信公众号会剥离 <style> 标签，只保留元素上的 style 属性，
    因此必须把所有样式写成内联形式。
    """

    SELF_CLOSING = {'br', 'hr', 'img', 'input', 'meta', 'link'}

    def __init__(self, theme_color: str):
        self.theme_color = theme_color
        self._in_pre = False
        self._in_blockquote = False

    def _tag_style(self, tag: str) -> str:
        c = self.theme_color
        styles = {
            'h1': (
                f'display:block;font-size:22px;font-weight:700;color:{c};'
                f'text-align:center;border-bottom:2px solid {c};'
                'padding-bottom:12px;margin:32px 0 20px;line-height:1.4;letter-spacing:1px;'
            ),
            'h2': (
                f'display:block;font-size:18px;font-weight:600;color:{c};'
                f'border-left:4px solid {c};padding:8px 0 8px 14px;'
                'margin:28px 0 14px;line-height:1.4;background-color:#f8f9fa;'
            ),
            'h3': (
                f'display:block;font-size:16px;font-weight:600;color:{c};'
                f'border-left:2px solid {c};padding-left:10px;'
                'margin:22px 0 10px;line-height:1.4;'
            ),
            'h4': (
                'display:block;font-size:15px;font-weight:600;color:#34495e;'
                'margin:18px 0 8px;line-height:1.4;'
            ),
            'p': (
                'display:block;margin:16px 0;line-height:1.9;'
                'color:#333;text-align:justify;font-size:15px;'
            ),
            'blockquote': (
                f'display:block;margin:20px 0;padding:12px 20px;'
                f'border-left:4px solid {c};background-color:#f8f9fa;'
                'color:#666;border-radius:0 6px 6px 0;'
            ),
            'ul': 'display:block;padding-left:20px;margin:12px 0;',
            'ol': 'display:block;padding-left:20px;margin:12px 0;',
            'li': 'display:list-item;margin:8px 0;line-height:1.8;color:#333;font-size:15px;',
            'strong': f'color:{c};font-weight:700;',
            'b':      f'color:{c};font-weight:700;',
            'em': 'color:#888;font-style:italic;',
            'i':  'color:#888;font-style:italic;',
            'code': (
                'background-color:#f5f7f9;padding:2px 6px;border-radius:3px;'
                'font-size:13px;color:#e74c3c;border:1px solid #eaecef;'
            ),
            'pre': (
                'display:block;background-color:#282c34;padding:16px;'
                'border-radius:6px;font-size:13px;line-height:1.6;margin:16px 0;'
            ),
            'table': 'display:table;width:100%;border-collapse:collapse;margin:16px 0;font-size:14px;',
            'thead': 'display:table-header-group;',
            'tbody': 'display:table-row-group;',
            'tr':    'display:table-row;',
            'th': (
                f'display:table-cell;background-color:{c};color:white;'
                'padding:10px 8px;text-align:left;font-weight:600;'
            ),
            'td': 'display:table-cell;padding:8px;border-bottom:1px solid #e0e0e0;color:#333;',
            'hr': 'display:block;border:none;border-top:2px solid #eee;margin:24px 0;',
            'img': 'max-width:100%;height:auto;display:block;margin:16px auto;border-radius:4px;',
            'a':  f'color:{c};text-decoration:none;',
        }
        return styles.get(tag, '')

    def transform(self, html: str) -> str:
        """将 HTML 字符串转换为带内联样式的版本。"""
        from html.parser import HTMLParser

        result = []
        in_pre = [False]
        transformer = self

        class _Parser(HTMLParser):
            def handle_starttag(self, tag, attrs):
                if tag == 'pre':
                    in_pre[0] = True
                style = transformer._tag_style(tag)
                # code inside <pre>: 覆盖 inline code 样式，改用代码块配色
                if tag == 'code' and in_pre[0]:
                    style = (
                        'background-color:transparent;padding:0;border:none;'
                        'color:#abb2bf;font-size:13px;line-height:1.6;'
                    )
                attrs_dict = dict(attrs)
                existing = attrs_dict.pop('style', '') or ''
                if existing:
                    style = existing.rstrip(';') + ';' + style
                if style:
                    attrs_dict['style'] = style
                attrs_str = ''.join(
                    f' {k}="{v}"' if v is not None else f' {k}'
                    for k, v in attrs_dict.items()
                )
                result.append(f'<{tag}{attrs_str}>')

            def handle_endtag(self, tag):
                if tag == 'pre':
                    in_pre[0] = False
                if tag not in transformer.SELF_CLOSING:
                    result.append(f'</{tag}>')

            def handle_data(self, data):
                result.append(data)

            def handle_entityref(self, name):
                result.append(f'&{name};')

            def handle_charref(self, name):
                result.append(f'&#{name};')

        _Parser(convert_charrefs=False).feed(html)
        return ''.join(result)


def markdown_to_wechat_html(markdown_content: str, theme_color: str = "#1E88E5", include_style: bool = True) -> str:
    """
    将 Markdown 转换为微信公众号友好的 HTML

    Args:
        markdown_content: Markdown 内容
        theme_color: 主题颜色
        include_style: True=<style>标签（本地预览用）；False=内联样式（微信 API 用）
    """
    import markdown

    # include_style=False：用于微信 API，生成内联样式 HTML
    if not include_style:
        html_body = markdown.markdown(
            markdown_content,
            extensions=['extra', 'tables', 'nl2br']
        )
        body = _WeChatHTMLTransformer(theme_color).transform(html_body)
        wrapper = (
            'font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",'
            '"Hiragino Sans GB","Microsoft YaHei",sans-serif;'
            'font-size:15px;line-height:1.8;color:#333;word-wrap:break-word;padding:0 4px;'
        )
        return f'<section style="{wrapper}">{body}</section>'

    # include_style=True：用于 Streamlit 本地预览，保留 <style> 标签
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
        },
        "teal": {
            "name": "文艺青",
            "theme_color": "#00897B",
            "description": "青绿色主题，适合文艺、情感类文章"
        },
        "pink": {
            "name": "甜美粉",
            "theme_color": "#E91E63",
            "description": "粉色主题，适合女性、生活类文章"
        },
        "indigo": {
            "name": "科技蓝",
            "theme_color": "#3F51B5",
            "description": "深蓝色主题，适合科技、互联网类文章"
        },
        "brown": {
            "name": "复古棕",
            "theme_color": "#795548",
            "description": "棕色主题，适合历史、文化类文章"
        },
        "golden": {
            "name": "高端金",
            "theme_color": "#FF8F00",
            "description": "金色主题，适合高端、奢华类文章"
        },
        "minimal": {
            "name": "极简灰",
            "theme_color": "#616161",
            "description": "极简灰色主题，适合简约风格文章"
        }
    }
