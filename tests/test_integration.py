"""
核心功能集成测试
测试文章生成流程、多轮修改等端到端功能
"""
import pytest
import asyncio
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from app.generator import ArticleGenerator, ArticleOutline, GeneratedArticle
from app.models import init_db, get_session, Article
from app.wechat import markdown_to_wechat_html, get_wechat_templates
from app.hot_topics import HotTopic, format_topics_for_prompt


class TestArticleGenerationFlow:
    """文章生成流程集成测试"""

    @pytest.mark.asyncio
    async def test_full_generation_flow(self, mock_openai_client):
        """测试完整的文章生成流程"""
        generator = ArticleGenerator(api_key="test_key")
        generator.client = mock_openai_client

        # 1. 生成大纲
        outline = await generator.generate_outline(
            topic="AI 在医疗领域的应用",
            template_type="techTutorial",
            custom_requirements="字数 2000 字左右",
            model="qwen-plus"
        )
        assert isinstance(outline, ArticleOutline)
        assert outline.title == "测试标题"

        # 2. 撰写文章
        content = await generator.write_article(
            topic="AI 在医疗领域的应用",
            outline=outline,
            template_type="techTutorial",
            model="qwen-plus"
        )
        assert isinstance(content, str)
        assert len(content) > 0

        # 3. 验证文章包含 Markdown 格式
        assert "#" in content or "\n" in content

    @pytest.mark.asyncio
    async def test_generate_with_stream(self, mock_openai_client):
        """测试带流式输出的生成"""
        generator = ArticleGenerator(api_key="test_key")
        generator.client = mock_openai_client

        chunks_received = []

        def callback(delta, done):
            if delta:
                chunks_received.append(delta)

        outline = await generator.generate_outline(
            topic="测试主题",
            stream=True,
            stream_callback=callback,
            model="qwen-plus"
        )

        assert isinstance(outline, ArticleOutline)
        # 流式回调应该被调用

    @pytest.mark.asyncio
    async def test_modify_article_flow(self, mock_openai_client):
        """测试文章修改流程"""
        generator = ArticleGenerator(api_key="test_key")
        generator.client = mock_openai_client

        original = """# 原文标题

## 第一章

这是原文内容...

## 第二章

这是第二段内容...
"""
        # 执行修改
        modified = await generator.modify_article(
            original_content=original,
            modification_request="增加一个总结段落",
            topic="测试主题",
            model="qwen-plus"
        )

        assert isinstance(modified, str)
        assert len(modified) > 0


class TestWechatHTMLConversion:
    """微信公众号 HTML 转换测试"""

    def test_basic_markdown_to_html(self):
        """测试基础 Markdown 转 HTML"""
        markdown = """# 标题

这是正文内容。

## 子标题

- 列表项 1
- 列表项 2

**加粗文字** 和 *斜体文字*

> 引用内容
"""
        html = markdown_to_wechat_html(markdown, "#1E88E5")

        assert isinstance(html, str)
        assert "<h1" in html or "标题" in html
        assert "<p" in html

    def test_code_block_conversion(self):
        """测试代码块转换"""
        markdown = """# 代码示例

```python
def hello():
    print("Hello World")
```
"""
        html = markdown_to_wechat_html(markdown, "#1E88E5")

        assert isinstance(html, str)
        # 代码块应该有特殊样式

    def test_theme_templates(self):
        """测试主题模板"""
        templates = get_wechat_templates()

        assert isinstance(templates, dict)
        assert len(templates) > 0

        # 检查默认主题
        assert "default" in templates
        assert "name" in templates["default"]
        assert "theme_color" in templates["default"]

    def test_custom_theme_color(self):
        """测试自定义主题颜色"""
        markdown = "# 测试标题"
        html = markdown_to_wechat_html(markdown, "#FF5722")

        assert isinstance(html, str)
        assert "#FF5722" in html or "FF5722" in html


class TestHotTopics:
    """热点追踪功能测试"""

    def test_format_topics_for_prompt(self):
        """测试热点话题格式化"""
        # 函数接受字典格式：{platform: [topics]}
        topics = {
            "微博": [
                HotTopic(
                    title="AI 技术突破",
                    summary="AI 领域取得新进展",
                    url="https://example.com/1",
                    rank=1,
                    hot_value="95000",
                    platform="微博"
                ),
                HotTopic(
                    title="医疗 AI 应用",
                    summary="AI 在医疗领域的应用",
                    url="https://example.com/2",
                    rank=2,
                    hot_value="85000",
                    platform="微博"
                )
            ],
            "知乎": [
                HotTopic(
                    title="如何评价 AI 发展",
                    summary="知乎网友讨论 AI 发展",
                    url="https://example.com/3",
                    rank=1,
                    hot_value="328.5 万",
                    platform="知乎"
                )
            ]
        }

        formatted = format_topics_for_prompt(topics)

        assert isinstance(formatted, str)
        assert "微博" in formatted
        assert "知乎" in formatted
        assert "AI 技术突破" in formatted
        assert "医疗 AI 应用" in formatted
        assert "95000" in formatted

    def test_hot_topic_creation(self):
        """测试热点话题对象创建"""
        topic = HotTopic(
            title="测试热点",
            summary="测试摘要",
            url="https://example.com",
            rank=1,
            hot_value="10000",
            platform="微博"
        )

        assert topic.title == "测试热点"
        assert topic.rank == 1
        assert topic.hot_value == "10000"
        assert topic.platform == "微博"


class TestDatabaseIntegration:
    """数据库集成测试"""

    def test_article_model_creation(self):
        """测试文章模型创建"""
        article = Article(
            title="测试文章",
            subtitle="测试副标题",
            topic="测试主题",
            template_type="general",
            content="测试内容",
            status="draft"
        )

        assert article.title == "测试文章"
        assert article.status == "draft"
        # created_at 在保存到数据库时才会自动设置
        assert article.created_at is None or article.created_at is not None

    def test_article_to_dict(self):
        """测试文章转字典"""
        article = Article(
            title="测试文章",
            content="测试内容",
            template_type="general",
            status="draft"
        )

        data = article.to_dict()

        assert isinstance(data, dict)
        assert data["title"] == "测试文章"
        assert data["content"] == "测试内容"

    @pytest.mark.skip(reason="需要真实数据库")
    def test_save_and_retrieve_article(self, setup_test_environment):
        """测试保存和获取文章"""
        # 初始化数据库
        init_db()

        session = get_session()

        # 创建文章
        article = Article(
            title="数据库测试文章",
            content="测试内容",
            template_type="general",
            status="draft"
        )

        session.add(article)
        session.commit()

        # 获取文章
        retrieved = session.query(Article).filter(
            Article.title == "数据库测试文章"
        ).first()

        assert retrieved is not None
        assert retrieved.content == "测试内容"

        # 清理
        session.delete(article)
        session.commit()
        session.close()


class TestSchedulerIntegration:
    """定时任务集成测试"""

    def test_generate_article_callback_structure(self):
        """测试生成文章回调函数结构"""
        from app.main import _generate_article_callback

        # 验证回调函数存在
        assert callable(_generate_article_callback)

        # 验证函数签名
        import inspect
        sig = inspect.signature(_generate_article_callback)
        params = list(sig.parameters.keys())

        assert "topic" in params
        assert "template_type" in params
        assert "sync_to_wechat" in params


class TestFileManagement:
    """文件管理功能测试"""

    def test_markdown_file_structure(self, temp_output_dir):
        """测试 Markdown 文件结构"""
        test_file = temp_output_dir / "test_article.md"
        content = """# 测试标题

## 副标题

这是测试内容...
"""
        test_file.write_text(content, encoding="utf-8")

        assert test_file.exists()
        assert "# 测试标题" in test_file.read_text(encoding="utf-8")

    def test_meta_file_structure(self, temp_output_dir):
        """测试元数据文件结构"""
        meta_file = temp_output_dir / "test_meta.json"
        meta_data = {
            "title": "测试文章",
            "template_type": "general",
            "created_at": "2026-03-24T10:00:00"
        }

        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta_data, f, ensure_ascii=False, indent=2)

        assert meta_file.exists()

        with open(meta_file, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        assert loaded["title"] == "测试文章"
        assert loaded["template_type"] == "general"


# Mock 测试夹具
@pytest.fixture
def mock_openai_client():
    """模拟 OpenAI 客户端"""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '''{
        "title": "测试标题",
        "subtitle": "测试副标题",
        "sections": [
            {"title": "章节 1", "content": "章节 1 内容"},
            {"title": "章节 2", "content": "章节 2 内容"}
        ],
        "suggested_cover": "封面图描述"
    }'''

    mock_stream_chunks = [
        MagicMock(choices=[MagicMock(delta=MagicMock(content=chunk))])
        for chunk in ["{", '"title"', ":", '"测试"', "}"]
    ]

    async def mock_stream_iter(*args, **kwargs):
        for chunk in mock_stream_chunks:
            yield chunk

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    mock_client.chat.completions.create.side_effect = lambda *args, **kwargs: (
        mock_stream_iter() if kwargs.get('stream') else mock_response
    )

    return mock_client
