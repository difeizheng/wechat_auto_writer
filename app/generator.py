"""
AI 文章生成核心逻辑
支持多平台 API（通义千问、OpenAI、DeepSeek 等）
"""
import os
from typing import Optional
from pathlib import Path
from datetime import datetime
import json

from openai import AsyncOpenAI
from pydantic import BaseModel


class ArticleOutline(BaseModel):
    """文章大纲"""
    title: str
    subtitle: Optional[str] = None
    sections: list[dict]  # [{title, content}]
    suggested_cover: str  # 封面图建议


class GeneratedArticle(BaseModel):
    """生成的文章"""
    title: str
    subtitle: Optional[str] = None
    content: str  # Markdown 格式
    outline: ArticleOutline
    created_at: str
    template_type: str


class ArticleGenerator:
    """文章生成器"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("需要配置 API Key")

        # API 地址
        self.base_url = base_url or "https://coding.dashscope.aliyuncs.com/v1"
        self.default_model = model or "qwen-plus"
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    async def generate_outline(
        self,
        topic: str,
        template_type: str = "general",
        custom_requirements: Optional[str] = None,
        model: str = "qwen-plus"
    ) -> ArticleOutline:
        """生成文章大纲"""

        templates = self._get_template_prompt(template_type)

        prompt = f"""请为以下主题生成一篇公众号文章的大纲：

**主题**: {topic}
**文章类型**: {template_type}
{f"**特殊要求**: {custom_requirements}" if custom_requirements else ""}

{templates}

请以 JSON 格式返回大纲，包含以下字段：
- title: 文章标题（吸引人，适合公众号风格）
- subtitle: 副标题（可选）
- sections: 文章章节列表，每个章节包含 title 和 content 描述
- suggested_cover: 封面图建议描述

只返回 JSON，不要其他内容。"""

        response = await self.client.chat.completions.create(
            model=model,
            max_tokens=2048,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # 解析 JSON 响应
        content_text = response.choices[0].message.content
        # 提取 JSON（可能包含在代码块中）
        if "```json" in content_text:
            content_text = content_text.split("```json")[1].split("```")[0]
        elif "```" in content_text:
            content_text = content_text.split("```")[1].split("```")[0]

        outline_data = json.loads(content_text.strip())

        return ArticleOutline(
            title=outline_data.get("title", ""),
            subtitle=outline_data.get("subtitle"),
            sections=outline_data.get("sections", []),
            suggested_cover=outline_data.get("suggested_cover", "")
        )

    async def write_article(
        self,
        topic: str,
        outline: ArticleOutline,
        template_type: str = "general",
        model: str = "qwen-plus"
    ) -> str:
        """根据大纲撰写全文"""

        templates = self._get_template_prompt(template_type)

        sections_prompt = "\n\n".join([
            f"### {s['title']}\n{s['content']}"
            for s in outline.sections
        ])

        prompt = f"""请根据以下大纲撰写一篇完整的公众号文章：

**主题**: {topic}
**标题**: {outline.title}
{f"**副标题**: {outline.subtitle}" if outline.subtitle else ""}

**文章大纲**:
{sections_prompt}

{templates}

**写作要求**:
1. 使用 Markdown 格式
2. 语言生动有趣，适合公众号阅读
3. 适当使用加粗、列表等格式增强可读性
4. 段落不要太长，便于手机阅读
5. 开头要吸引人，结尾要有互动或总结

请输出完整的文章内容（Markdown 格式）。"""

        response = await self.client.chat.completions.create(
            model=model,
            max_tokens=8192,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return response.choices[0].message.content

    async def generate_article(
        self,
        topic: str,
        template_type: str = "general",
        custom_requirements: Optional[str] = None,
        save: bool = True,
        model: str = "qwen-plus"
    ) -> GeneratedArticle:
        """完整流程：生成大纲 -> 撰写文章"""

        # 生成大纲
        outline = await self.generate_outline(
            topic,
            template_type,
            custom_requirements,
            model=model
        )

        # 撰写正文
        content = await self.write_article(topic, outline, template_type, model=model)

        # 组装文章
        article = GeneratedArticle(
            title=outline.title,
            subtitle=outline.subtitle,
            content=content,
            outline=outline,
            created_at=datetime.now().isoformat(),
            template_type=template_type
        )

        # 保存文章
        if save:
            self._save_article(article)

        return article

    def _get_template_prompt(self, template_type: str) -> str:
        """获取不同类型文章的提示词模板"""

        templates = {
            "techTutorial": """**技术教程类文章风格**:
- 结构清晰，步骤明确
- 包含代码示例（如有）
- 有前言、正文、总结
- 语言通俗易懂""",

            "newsAnalysis": """**资讯解读类文章风格**:
- 先介绍事件背景
- 分析核心要点
- 给出专业观点
- 预测未来趋势""",

            "opinion": """**观点评论类文章风格**:
- 观点鲜明，有个人特色
- 论证充分，有案例支撑
- 语言有感染力
- 引发读者思考""",

            "productPromo": """**产品推广类文章风格**:
- 突出产品亮点
- 解决用户痛点
- 有吸引力的标题
- 清晰的行动号召""",

            "general": """**通用公众号文章风格**:
- 语言通俗易懂
- 结构清晰
- 有吸引力
- 适合大众阅读"""
        }

        return templates.get(template_type, templates["general"])

    def _save_article(self, article: GeneratedArticle) -> Path:
        """保存文章到本地"""
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{article.title[:20]}.md"
        filepath = output_dir / filename

        # 保存 Markdown
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# {article.title}\n\n")
            if article.subtitle:
                f.write(f"## {article.subtitle}\n\n")
            f.write(f"*生成时间：{article.created_at}*\n\n")
            f.write(f"*文章类型：{article.template_type}*\n\n")
            f.write("---\n\n")
            f.write(article.content)

        # 保存元数据
        meta_path = output_dir / f"{filepath.stem}_meta.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({
                "title": article.title,
                "subtitle": article.subtitle,
                "template_type": article.template_type,
                "created_at": article.created_at,
                "outline": {
                    "sections": article.outline.sections,
                    "suggested_cover": article.outline.suggested_cover
                }
            }, f, ensure_ascii=False, indent=2)

        return filepath
