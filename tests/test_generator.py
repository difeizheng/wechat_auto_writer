"""
generator.py 单元测试
测试文章生成器的核心功能
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from app.generator import ArticleGenerator, ArticleOutline, GeneratedArticle


class TestArticleGenerator:
    """文章生成器测试类"""

    def test_init_with_api_key(self):
        """测试初始化生成器"""
        generator = ArticleGenerator(
            api_key="test_key",
            base_url="https://test.api.com/v1",
            model="test-model"
        )
        assert generator.api_key == "test_key"
        assert generator.base_url == "https://test.api.com/v1"
        assert generator.default_model == "test-model"

    def test_init_without_api_key_raises_error(self, monkeypatch):
        """测试没有 API Key 时抛出错误"""
        # 清除环境变量
        monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
        with pytest.raises(ValueError, match="需要配置 API Key"):
            ArticleGenerator(api_key=None)

    def test_init_default_values(self):
        """测试默认参数"""
        generator = ArticleGenerator(api_key="test_key")
        assert generator.base_url == "https://coding.dashscope.aliyuncs.com/v1"
        assert generator.default_model == "qwen-plus"

    @pytest.mark.asyncio
    async def test_generate_outline(self, mock_openai_client):
        """测试生成大纲"""
        generator = ArticleGenerator(api_key="test_key")
        generator.client = mock_openai_client

        outline = await generator.generate_outline(
            topic="AI 测试",
            template_type="general",
            model="qwen-plus"
        )

        assert isinstance(outline, ArticleOutline)
        assert outline.title == "测试标题"
        assert len(outline.sections) > 0

    @pytest.mark.asyncio
    async def test_generate_outline_with_custom_requirements(self, mock_openai_client):
        """测试带特殊要求的大纲生成"""
        generator = ArticleGenerator(api_key="test_key")
        generator.client = mock_openai_client

        outline = await generator.generate_outline(
            topic="AI 测试",
            template_type="techTutorial",
            custom_requirements="字数控制在 2000 字以内",
            model="qwen-plus"
        )

        assert isinstance(outline, ArticleOutline)

    @pytest.mark.asyncio
    async def test_write_article(self, mock_openai_client, sample_article_outline):
        """测试撰写文章"""
        generator = ArticleGenerator(api_key="test_key")
        generator.client = mock_openai_client

        content = await generator.write_article(
            topic="AI 测试",
            outline=ArticleOutline(**sample_article_outline),
            template_type="general",
            model="qwen-plus"
        )

        assert isinstance(content, str)
        assert len(content) > 0

    @pytest.mark.asyncio
    async def test_generate_article_full_flow(self, mock_openai_client):
        """测试完整文章生成流程"""
        generator = ArticleGenerator(api_key="test_key")
        generator.client = mock_openai_client

        article = await generator.generate_article(
            topic="AI 测试",
            template_type="general",
            save=False,  # 测试时不保存
            model="qwen-plus"
        )

        assert isinstance(article, GeneratedArticle)
        assert article.title == "测试标题"
        assert article.template_type == "general"

    @pytest.mark.asyncio
    async def test_stream_outline_callback(self, mock_openai_client):
        """测试流式输出回调 - 大纲生成"""
        generator = ArticleGenerator(api_key="test_key")
        generator.client = mock_openai_client

        received_chunks = []
        done_flag = False

        def stream_callback(delta, done):
            nonlocal done_flag
            if delta:
                received_chunks.append(delta)
            if done:
                done_flag = True

        outline = await generator.generate_outline(
            topic="AI 测试",
            stream=True,
            stream_callback=stream_callback,
            model="qwen-plus"
        )

        assert done_flag is True
        assert isinstance(outline, ArticleOutline)

    @pytest.mark.asyncio
    async def test_stream_article_callback(self, mock_openai_client, sample_article_outline):
        """测试流式输出回调 - 文章撰写"""
        generator = ArticleGenerator(api_key="test_key")
        generator.client = mock_openai_client

        received_chunks = []
        done_flag = False

        def stream_callback(delta, done):
            nonlocal done_flag
            if delta:
                received_chunks.append(delta)
            if done:
                done_flag = True

        content = await generator.write_article(
            topic="AI 测试",
            outline=ArticleOutline(**sample_article_outline),
            stream=True,
            stream_callback=stream_callback,
            model="qwen-plus"
        )

        assert done_flag is True
        assert isinstance(content, str)

    @pytest.mark.asyncio
    async def test_modify_article(self, mock_openai_client, sample_article_content):
        """测试文章修改功能"""
        generator = ArticleGenerator(api_key="test_key")
        generator.client = mock_openai_client

        modified_content = await generator.modify_article(
            original_content=sample_article_content,
            modification_request="增加一个总结段落",
            topic="AI 医疗",
            template_type="techTutorial",
            model="qwen-plus"
        )

        assert isinstance(modified_content, str)
        assert len(modified_content) > 0

    @pytest.mark.asyncio
    async def test_modify_article_stream(self, mock_openai_client, sample_article_content):
        """测试流式文章修改"""
        generator = ArticleGenerator(api_key="test_key")
        generator.client = mock_openai_client

        done_flag = False

        def stream_callback(delta, done):
            nonlocal done_flag
            if done:
                done_flag = True

        modified_content = await generator.modify_article(
            original_content=sample_article_content,
            modification_request="简化语言",
            stream=True,
            stream_callback=stream_callback,
            model="qwen-plus"
        )

        assert done_flag is True
        assert isinstance(modified_content, str)

    def test_get_template_prompt(self):
        """测试模板提示词获取"""
        generator = ArticleGenerator(api_key="test_key")

        # 测试各种模板类型
        templates = ["techTutorial", "newsAnalysis", "opinion", "productPromo", "general"]
        for template in templates:
            prompt = generator._get_template_prompt(template)
            assert isinstance(prompt, str)
            assert len(prompt) > 0

        # 测试未知模板返回通用模板
        default_prompt = generator._get_template_prompt("unknown")
        assert "通用公众号文章风格" in default_prompt

    def test_save_article(self, sample_article_outline, temp_output_dir, monkeypatch):
        """测试保存文章"""
        monkeypatch.chdir(temp_output_dir)

        generator = ArticleGenerator(api_key="test_key")

        article = GeneratedArticle(
            title="测试文章",
            subtitle="测试副标题",
            content="# 测试内容\n\n这是测试文章正文...",
            outline=ArticleOutline(**sample_article_outline),
            created_at="2026-03-24T10:00:00",
            template_type="general"
        )

        filepath = generator._save_article(article)

        assert filepath.exists()
        assert filepath.suffix == ".md"

        # 检查元数据文件
        meta_path = filepath.parent / f"{filepath.stem}_meta.json"
        assert meta_path.exists()


# Mock 测试夹具
@pytest.fixture
def mock_openai_client():
    """模拟 OpenAI 客户端"""
    from unittest.mock import AsyncMock, MagicMock

    # 模拟响应
    mock_response = AsyncMock()
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

    # 模拟流式响应
    mock_stream_chunks = [
        MagicMock(choices=[MagicMock(delta=MagicMock(content=chunk))])
        for chunk in ["{", '"title"', ":", '"测试"', "}"]
    ]

    async def mock_stream_iter(*args, **kwargs):
        for chunk in mock_stream_chunks:
            yield chunk

    # 创建模拟客户端
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    # 添加流式支持
    mock_client.chat.completions.create.side_effect = lambda *args, **kwargs: (
        mock_stream_iter() if kwargs.get('stream') else mock_response
    )

    return mock_client
