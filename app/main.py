"""
Streamlit 管理界面
"""
import os
import sys
import asyncio
import streamlit as st
from pathlib import Path
from datetime import datetime
import json

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.generator import ArticleGenerator, GeneratedArticle, ArticleOutline
from app.models import init_db, get_session, Article
from app.wechat import markdown_to_wechat_html, get_wechat_templates, WeChatAPI
from app.hot_topics import get_tracker, format_topics_for_prompt, HotTopic
from app.scheduler import get_scheduler, init_scheduler
from app.file_manager import get_file_manager, FileManager


# 页面配置
st.set_page_config(
    page_title="公众号文章自动生成器",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化数据库
init_db()

# 配置文件路径
CONFIG_FILE = Path("data") / "config.json"


# 预设平台配置
PRESET_PLATFORMS = {
    "通义千问": {
        "base_url": "https://coding.dashscope.aliyuncs.com/v1",
        "models": ["qwen-plus", "qwen-turbo", "qwen-max", "qwen-max-longcontext", "qwen-long"]
    },
    "OpenAI": {
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
    },
    "DeepSeek": {
        "base_url": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-coder"]
    },
    "智谱 AI": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "models": ["glm-4", "glm-4-air", "glm-3-turbo"]
    },
    "自定义平台": {
        "base_url": "",
        "models": []
    }
}


def load_config() -> dict:
    """从配置文件加载配置"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}


def save_config(config: dict):
    """保存配置到文件"""
    CONFIG_FILE.parent.mkdir(exist_ok=True)
    existing_config = load_config()
    existing_config.update(config)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(existing_config, f, ensure_ascii=False, indent=2)


def get_platform_config(platform_name: str) -> dict:
    """获取指定平台的配置"""
    config = load_config()
    platforms = config.get("platforms", {})
    return platforms.get(platform_name, {})


def save_platform_config(platform_name: str, platform_config: dict):
    """保存平台配置"""
    config = load_config()
    if "platforms" not in config:
        config["platforms"] = {}
    config["platforms"][platform_name] = platform_config
    save_config(config)


def get_current_platform() -> str:
    """获取当前选中的平台"""
    config = load_config()
    return config.get("current_platform", "通义千问")


def set_current_platform(platform_name: str):
    """设置当前平台"""
    save_config({"current_platform": platform_name})


def load_model_name(platform: str = None) -> str:
    """从配置文件加载模型名称"""
    if platform is None:
        platform = get_current_platform()
    platform_config = get_platform_config(platform)
    saved_model = platform_config.get("model_name")
    if saved_model:
        return saved_model
    # 返回平台默认模型，如果没有则返回空字符串
    preset_models = PRESET_PLATFORMS.get(platform, {}).get("models", [])
    return preset_models[0] if preset_models else ""


def save_model_name(model_name: str, platform: str = None):
    """保存模型名称到配置文件"""
    if platform is None:
        platform = get_current_platform()
    platform_config = get_platform_config(platform)
    platform_config["model_name"] = model_name
    save_platform_config(platform, platform_config)


def load_api_key(platform: str = None) -> str:
    """从配置文件加载 API Key"""
    if platform is None:
        platform = get_current_platform()
    platform_config = get_platform_config(platform)
    return platform_config.get("api_key", "")


def save_api_key(api_key: str, platform: str = None):
    """保存 API Key 到配置文件"""
    if platform is None:
        platform = get_current_platform()
    platform_config = get_platform_config(platform)
    platform_config["api_key"] = api_key
    save_platform_config(platform, platform_config)


def load_base_url(platform: str = None) -> str:
    """从配置文件加载 Base URL"""
    if platform is None:
        platform = get_current_platform()
    platform_config = get_platform_config(platform)
    preset = PRESET_PLATFORMS.get(platform, {})
    return platform_config.get("base_url", preset.get("base_url", ""))


def save_base_url(base_url: str, platform: str = None):
    """保存 Base URL 到配置文件"""
    if platform is None:
        platform = get_current_platform()
    platform_config = get_platform_config(platform)
    platform_config["base_url"] = base_url
    save_platform_config(platform, platform_config)


def get_custom_models(platform: str = None) -> list:
    """获取自定义模型列表"""
    if platform is None:
        platform = get_current_platform()
    platform_config = get_platform_config(platform)
    return platform_config.get("custom_models", [])


def get_removed_models(platform: str = None) -> list:
    """获取被移除的模型列表"""
    if platform is None:
        platform = get_current_platform()
    platform_config = get_platform_config(platform)
    return platform_config.get("removed_models", [])


def save_custom_models(models: list, platform: str = None):
    """保存自定义模型列表"""
    if platform is None:
        platform = get_current_platform()
    platform_config = get_platform_config(platform)
    platform_config["custom_models"] = models
    save_platform_config(platform, platform_config)


def save_removed_models(models: list, platform: str = None):
    """保存被移除的模型列表"""
    if platform is None:
        platform = get_current_platform()
    platform_config = get_platform_config(platform)
    platform_config["removed_models"] = models
    save_platform_config(platform, platform_config)


def load_wechat_config() -> dict:
    """从配置文件加载微信公众号配置"""
    config = load_config()
    return config.get("wechat", {})


def save_wechat_config(app_id: str = None, app_secret: str = None):
    """保存微信公众号配置"""
    config = load_config()
    if "wechat" not in config:
        config["wechat"] = {}
    if app_id is not None:
        config["wechat"]["app_id"] = app_id
    if app_secret is not None:
        config["wechat"]["app_secret"] = app_secret
    save_config(config)


def get_available_models(platform: str = None) -> tuple:
    """获取可用模型列表"""
    if platform is None:
        platform = get_current_platform()

    preset = PRESET_PLATFORMS.get(platform, {})
    base_models = preset.get("models", [])
    platform_config = get_platform_config(platform)
    removed_models = platform_config.get("removed_models", [])
    custom_models = platform_config.get("custom_models", [])

    # 过滤掉被移除的默认模型
    available_base = [m for m in base_models if m not in removed_models]
    return available_base, custom_models, removed_models

# 自定义 CSS
st.markdown("""
<style>
.main-title {
    font-size: 2.5rem;
    font-weight: bold;
    color: #1E88E5;
    text-align: center;
    margin-bottom: 1rem;
}
.section-title {
    font-size: 1.5rem;
    font-weight: bold;
    margin-top: 1.5rem;
}
.markdown-preview {
    background-color: #f5f5f5;
    padding: 1rem;
    border-radius: 0.5rem;
    border: 1px solid #e0e0e0;
}
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """初始化会话状态"""
    # 当前平台
    if "current_platform" not in st.session_state:
        st.session_state.current_platform = get_current_platform()

    # 加载当前平台的配置
    platform = st.session_state.current_platform
    if "api_key" not in st.session_state:
        loaded_key = load_api_key(platform)
        st.session_state.api_key = loaded_key or os.getenv("DASHSCOPE_API_KEY", "")
    if "generated_article" not in st.session_state:
        st.session_state.generated_article = None
    if "outline" not in st.session_state:
        st.session_state.outline = None
    if "current_step" not in st.session_state:
        st.session_state.current_step = 1

    # 加载模型名称，确保有默认值
    if "model_name" not in st.session_state:
        available_base, custom_models, _ = get_available_models(platform)
        saved_model = load_model_name(platform)
        all_available = available_base + custom_models
        if saved_model and saved_model in all_available:
            st.session_state.model_name = saved_model
        elif available_base:
            st.session_state.model_name = available_base[0]
        elif custom_models:
            st.session_state.model_name = custom_models[0]
        else:
            # 如果平台没有任何模型，使用默认值
            st.session_state.model_name = "qwen-plus"

    if "base_url" not in st.session_state:
        st.session_state.base_url = load_base_url(platform)
    if "show_add_model" not in st.session_state:
        st.session_state.show_add_model = False
    if "show_manage_models" not in st.session_state:
        st.session_state.show_manage_models = False

    # 排版主题配置
    if "wechat_theme" not in st.session_state:
        st.session_state.wechat_theme = "default"

    # 微信公众号配置
    if "wechat_app_id" not in st.session_state:
        st.session_state.wechat_app_id = load_wechat_config().get("app_id", "")
    if "wechat_app_secret" not in st.session_state:
        st.session_state.wechat_app_secret = load_wechat_config().get("app_secret", "")
    if "sync_to_wechat" not in st.session_state:
        st.session_state.sync_to_wechat = False

    # 热点话题缓存
    if "hot_topics" not in st.session_state:
        st.session_state.hot_topics = None
    if "hot_topics_last_fetch" not in st.session_state:
        st.session_state.hot_topics_last_fetch = None

    # 初始化调度器
    if "scheduler_initialized" not in st.session_state:
        init_scheduler()
        st.session_state.scheduler_initialized = True


def sidebar_config():
    """侧边栏配置"""
    with st.sidebar:
        st.header("⚙️ 配置")

        # 平台选择
        st.subheader("🌐 AI 平台")
        platform_options = list(PRESET_PLATFORMS.keys())
        current_platform = st.session_state.get("current_platform", "通义千问")
        selected_platform = st.selectbox(
            "选择平台",
            options=platform_options,
            index=platform_options.index(current_platform) if current_platform in platform_options else 0
        )

        # 检测平台切换
        if selected_platform != st.session_state.current_platform:
            st.session_state.current_platform = selected_platform
            set_current_platform(selected_platform)
            # 加载新平台的配置
            st.session_state.api_key = load_api_key(selected_platform)
            st.session_state.model_name = load_model_name(selected_platform)
            st.session_state.base_url = load_base_url(selected_platform)
            st.rerun()

        # 显示当前平台信息
        preset = PRESET_PLATFORMS.get(selected_platform, {})
        st.caption(f"Base URL: {preset.get('base_url', '自定义')}")

        st.divider()

        # API Key 配置 - 持久化保存
        api_key = st.text_input(
            "API Key",
            value=st.session_state.api_key,
            type="password",
            help=f"{selected_platform} API Key"
        )
        if api_key:
            st.session_state.api_key = api_key
            os.environ["DASHSCOPE_API_KEY"] = api_key
            save_api_key(api_key, selected_platform)

        # 清除 API Key 按钮
        if st.session_state.api_key:
            if st.button("🗑️ 清除 API Key", use_container_width=True):
                st.session_state.api_key = ""
                save_api_key("", selected_platform)
                st.rerun()

        st.divider()

        # Base URL 配置（自定义平台可编辑）
        st.subheader("🔗 Base URL")
        if selected_platform == "自定义平台":
            base_url = st.text_input(
                "自定义 Base URL",
                value=st.session_state.base_url,
                placeholder="https://api.example.com/v1"
            )
            if base_url:
                st.session_state.base_url = base_url
                save_base_url(base_url, selected_platform)
        else:
            st.info(f"`{st.session_state.base_url}`")

        st.divider()

        # 模型名称配置 - 下拉选择 + 自定义
        st.subheader("模型名称")

        # 获取可用模型
        available_base, custom_models, removed_models = get_available_models(selected_platform)
        all_models = available_base + custom_models

        # 确保当前模型在选项中
        current_model = st.session_state.model_name
        if all_models and current_model in all_models:
            default_index = all_models.index(current_model)
        else:
            default_index = 0  # 默认为第一个选项（add_new）

        # 如果没有模型，显示提示信息
        if not all_models:
            st.warning(f"⚠️ {selected_platform} 暂无可用模型，请点击上方'➕ 添加新模型'添加")

        selected_model = st.selectbox(
            "选择模型",
            options=all_models + ["add_new", "manage_models"],
            format_func=lambda x: "➕ 添加新模型" if x == "add_new" else "⚙️ 管理模型列表" if x == "manage_models" else x,
            index=min(default_index, len(all_models)),  # 确保索引不越界
            key="model_selectbox"
        )

        # 检测是否更改了选择
        if "last_selected_model" not in st.session_state:
            st.session_state.last_selected_model = selected_model

        # 处理添加新模型
        if st.session_state.get("show_add_model", False):
            st.markdown("---")
            st.markdown("**➕ 添加新模型**")
            new_model = st.text_input(
                "新模型名称",
                placeholder="例如：qwen-2.5-72b-instruct",
                key="new_model_input"
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("添加", use_container_width=True, key="btn_add_model"):
                    if new_model and new_model not in all_models:
                        custom_models.append(new_model)
                        save_custom_models(custom_models, selected_platform)
                        st.session_state.model_name = new_model
                        st.session_state.show_add_model = False
                        st.session_state.last_selected_model = new_model
                        st.rerun()
                    elif new_model in all_models:
                        st.warning("该模型已存在")
            with col2:
                if st.button("取消", use_container_width=True, key="btn_cancel_add"):
                    st.session_state.show_add_model = False
                    st.rerun()
            return  # 提前返回，不执行下面的逻辑

        # 处理管理模型列表
        if st.session_state.get("show_manage_models", False):
            st.markdown("---")
            st.markdown("**⚙️ 管理模型**")
            st.caption("点击 🗑️ 可以从列表中移除模型（可恢复）")

            # 显示默认模型（可删除/恢复）
            st.markdown("**默认模型**")
            preset = PRESET_PLATFORMS.get(selected_platform, {})
            base_models = preset.get("models", [])
            if not base_models:
                st.info("该平台暂无默认模型")
            else:
                for model in base_models:
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        is_removed = model in removed_models
                        status = "❌ 已隐藏" if is_removed else "✅ 可用"
                        st.text(f"• {model} - {status}")
                    with col2:
                        btn_text = "🔙 恢复" if model in removed_models else "🗑️ 隐藏"
                        if st.button(btn_text, key=f"toggle_base_{model}"):
                            if model in removed_models:
                                removed_models.remove(model)
                            else:
                                removed_models.append(model)
                                if st.session_state.model_name == model:
                                    remaining = [m for m in available_base if m != model]
                                    if remaining:
                                        st.session_state.model_name = remaining[0]
                                    elif custom_models:
                                        st.session_state.model_name = custom_models[0]
                                    save_model_name(st.session_state.model_name, selected_platform)
                            save_removed_models(removed_models, selected_platform)
                            st.rerun()

            # 显示自定义模型（可删除）
            st.markdown("**自定义模型**")
            if custom_models:
                for i, model in enumerate(custom_models):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.text(f"• {model}")
                    with col2:
                        if st.button("🗑️ 删除", key=f"del_custom_{i}"):
                            custom_models.pop(i)
                            save_custom_models(custom_models, selected_platform)
                            if st.session_state.model_name == model:
                                st.session_state.model_name = available_base[0] if available_base else "qwen-plus"
                                save_model_name(st.session_state.model_name, selected_platform)
                            st.rerun()
            else:
                st.info("暂无自定义模型")

            if st.button("✅ 完成", key="close_manage", use_container_width=True):
                st.session_state.show_manage_models = False
                st.rerun()
            return  # 提前返回，不执行下面的逻辑

        # 检测是否点击了特殊选项
        if st.session_state.last_selected_model != st.session_state.model_selectbox:
            if st.session_state.model_selectbox == "add_new":
                st.session_state.show_add_model = True
                st.session_state.show_manage_models = False
                st.session_state.last_selected_model = "add_new"
                st.rerun()
            elif st.session_state.model_selectbox == "manage_models":
                st.session_state.show_manage_models = True
                st.session_state.show_add_model = False
                st.session_state.last_selected_model = "manage_models"
                st.rerun()
            else:
                # 普通模型选择
                st.session_state.model_name = st.session_state.model_selectbox
                save_model_name(st.session_state.model_name, selected_platform)
                st.session_state.last_selected_model = st.session_state.model_selectbox

        st.info(f"当前使用：**{st.session_state.model_name}**")

        st.divider()

        # 排版主题设置
        st.subheader("🎨 排版主题")
        templates = get_wechat_templates()
        template_options = list(templates.keys())
        template_labels = [f"{templates[k]['name']}" for k in template_options]

        selected_theme = st.selectbox(
            "选择主题",
            options=template_options,
            format_func=lambda x: templates[x]["name"],
            index=template_options.index(st.session_state.wechat_theme) if st.session_state.wechat_theme in template_options else 0
        )
        st.session_state.wechat_theme = selected_theme
        st.caption(templates[selected_theme]["description"])

        st.divider()

        # 微信公众号配置
        st.subheader("📱 公众号配置")

        # AppID 配置
        wechat_app_id = st.text_input(
            "公众号 AppID",
            value=st.session_state.wechat_app_id,
            placeholder="wx...",
            help="微信公众号后台获取 AppID"
        )
        if wechat_app_id:
            st.session_state.wechat_app_id = wechat_app_id
            save_wechat_config(app_id=wechat_app_id)

        # AppSecret 配置
        wechat_app_secret = st.text_input(
            "公众号 AppSecret",
            value=st.session_state.wechat_app_secret,
            type="password",
            placeholder="API 密钥",
            help="微信公众号后台获取 AppSecret"
        )
        if wechat_app_secret:
            st.session_state.wechat_app_secret = wechat_app_secret
            save_wechat_config(app_secret=wechat_app_secret)

        # 清除配置按钮
        if st.session_state.wechat_app_id or st.session_state.wechat_app_secret:
            if st.button("🗑️ 清除公众号配置", use_container_width=True):
                st.session_state.wechat_app_id = ""
                st.session_state.wechat_app_secret = ""
                save_wechat_config(app_id="", app_secret="")
                st.rerun()

        st.divider()

        # 快捷操作
        st.header("📁 快捷操作")

        if st.button("📂 查看输出目录", use_container_width=True):
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            st.info(f"输出目录：`{output_dir.absolute()}`")

        # 显示历史记录数量
        try:
            session = get_session()
            count = session.query(Article).count()
            session.close()
            st.metric("📄 历史文章", count)
        except:
            pass

        st.divider()

        # 关于
        st.markdown("""
        ### 关于
        公众号文章自动生成系统 v1.0

        使用 AI 自动生成高质量公众号文章
        """)


def step1_input_topic():
    """第一步：输入主题和要求"""
    st.markdown('<p class="main-title">📝 公众号文章自动生成器</p>', unsafe_allow_html=True)
    st.markdown("---")

    col1, col2 = st.columns([2, 1])

    # 获取预设主题（从热点追踪跳转）
    preset_topic = st.session_state.get('topic', '')
    preset_template = st.session_state.get('template_type', 'newsAnalysis')
    preset_requirements = st.session_state.get('custom_requirements', '')

    with col1:
        topic = st.text_area(
            "🎯 文章主题/关键词",
            value=preset_topic,
            placeholder="例如：如何使用 Python 进行数据分析、2024 年 AI 发展趋势、微信小程序开发指南...",
            height=100,
            key="topic_input"
        )

    with col2:
        # 根据预设主题自动选择文章类型
        template_options = [
            ("general", "通用文章"),
            ("techTutorial", "技术教程"),
            ("newsAnalysis", "资讯解读"),
            ("opinion", "观点评论"),
            ("productPromo", "产品推广")
        ]
        default_index = next((i for i, (val, _) in enumerate(template_options) if val == preset_template), 0)
        template_type = st.selectbox(
            "📋 文章类型",
            options=template_options,
            format_func=lambda x: x[1],
            index=default_index,
            key="template_input"
        )

    custom_requirements = st.text_area(
        "💡 特殊要求（可选）",
        value=preset_requirements,
        placeholder="例如：字数控制在 2000 字以内、需要包含代码示例、语气要幽默风趣...",
        height=80,
        key="requirements_input"
    )

    return topic, template_type[0], custom_requirements


def step2_preview_outline(outline: ArticleOutline) -> bool:
    """第二步：预览和修改大纲"""
    st.markdown("## 📑 文章大纲预览")

    # 显示标题
    st.text_input("文章标题", value=outline.title, key="edit_title")
    if outline.subtitle:
        st.text_input("副标题", value=outline.subtitle, key="edit_subtitle")

    # 显示章节
    st.markdown("### 章节结构")
    edited_sections = []
    for i, section in enumerate(outline.sections):
        with st.expander(f"📌 {section['title']}", expanded=True):
            col1, col2 = st.columns([1, 3])
            with col1:
                section_title = st.text_input(
                    "章节标题",
                    value=section["title"],
                    key=f"section_{i}_title",
                    label_visibility="collapsed"
                )
            with col2:
                section_content = st.text_area(
                    "内容描述",
                    value=section["content"],
                    key=f"section_{i}_content",
                    height=80,
                    label_visibility="collapsed"
                )
            edited_sections.append({
                "title": section_title,
                "content": section_content
            })

    # 封面建议
    st.markdown("### 🖼️ 封面图建议")
    st.info(outline.suggested_cover)

    return edited_sections


def step3_preview_article(article: GeneratedArticle):
    """第三步：预览完整文章"""
    st.markdown("## 📄 文章预览")

    # 文章元信息
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("文章类型", article.template_type)
    with col2:
        st.metric("生成时间", article.created_at[:10])
    with col3:
        word_count = len(article.content)
        st.metric("字数", f"约{word_count}字")

    # Markdown 预览
    st.markdown("### 预览")
    st.markdown(article.content)

    # 操作按钮
    st.markdown("### 操作")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        download_markdown(article)

    with col2:
        download_html(article)

    with col3:
        if st.button("📋 复制全文", use_container_width=True):
            st.code(article.content, language="markdown")
            st.success("已复制到代码块，请手动复制")

    with col4:
        if st.button("🔄 重新生成", use_container_width=True):
            st.session_state.generated_article = None
            st.session_state.current_step = 1
            st.rerun()

    with col5:
        # 同步到公众号草稿箱按钮
        if st.button("📱 同步到草稿箱", use_container_width=True, help="需要配置公众号 AppID 和 AppSecret"):
            sync_to_wechat_draft(article)

    # 保存到数据库
    if st.button("💾 保存到历史记录"):
        try:
            session = get_session()
            db_article = Article(
                title=article.title,
                subtitle=article.subtitle,
                topic=st.session_state.get("topic", ""),
                template_type=article.template_type,
                content=article.content,
                outline={
                    "sections": article.outline.sections,
                    "suggested_cover": article.outline.suggested_cover
                },
                status="draft"
            )
            session.add(db_article)
            session.commit()
            session.close()
            st.success("已保存到历史记录")
        except Exception as e:
            st.error(f"保存失败：{str(e)}")


def download_markdown(article: GeneratedArticle):
    """提供 Markdown 下载"""
    content = f"# {article.title}\n\n"
    if article.subtitle:
        content += f"## {article.subtitle}\n\n"
    content += article.content

    st.download_button(
        label="⬇️ 下载 Markdown",
        data=content,
        file_name=f"{article.title}.md",
        mime="text/markdown"
    )


def download_html(article: GeneratedArticle):
    """提供 HTML 下载（微信公众号格式）"""
    theme_color = get_wechat_templates().get(st.session_state.wechat_theme, {}).get("theme_color", "#1E88E5")
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{article.title}</title>
</head>
<body>
    {markdown_to_wechat_html(article.content, theme_color)}
</body>
</html>"""

    st.download_button(
        label="⬇️ 下载 HTML",
        data=html_content,
        file_name=f"{article.title}.html",
        mime="text/html"
    )


def sync_to_wechat_draft(article: GeneratedArticle):
    """同步文章到微信公众号草稿箱"""
    # 检查是否配置了公众号信息
    app_id = st.session_state.wechat_app_id
    app_secret = st.session_state.wechat_app_secret

    if not app_id or not app_secret:
        st.error("请先在侧边栏配置公众号 AppID 和 AppSecret")
        st.info("配置路径：侧边栏 → 📱 公众号配置")
        return

    try:
        with st.spinner("正在同步到公众号草稿箱..."):
            # 创建 WeChat API 实例
            wechat_api = WeChatAPI(app_id=app_id, app_secret=app_secret)

            # 获取访问令牌
            token = wechat_api._get_access_token()
            st.caption("✅ 获取访问令牌成功")

            # 将 Markdown 转换为微信公众号 HTML 格式
            theme_color = get_wechat_templates().get(st.session_state.wechat_theme, {}).get("theme_color", "#1E88E5")
            html_content = markdown_to_wechat_html(article.content, theme_color)

            # 调用保存到草稿箱 API
            result = wechat_api.add_draft(
                title=article.title,
                content=html_content,
                author="",
                digest=article.subtitle or "",
                show_cover=True
            )

            if result.get("errcode", 1) == 0:
                media_id = result.get("media_id", "")
                st.success(f"✅ 同步成功！草稿 media_id: `{media_id}`")
                st.info("📱 请登录微信公众号后台查看草稿箱")

                # 更新数据库记录
                try:
                    session = get_session()
                    # 查找最近的文章记录并更新
                    latest_article = session.query(Article).order_by(Article.created_at.desc()).first()
                    if latest_article and latest_article.title == article.title:
                        latest_article.wechat_media_id = media_id
                        latest_article.status = "synced"
                        session.commit()
                        session.close()
                except Exception as e:
                    st.caption(f"数据库更新失败：{str(e)}")
            else:
                st.error(f"❌ 同步失败：{result.get('errmsg', '未知错误')}")

    except Exception as e:
        st.error(f"同步失败：{str(e)}")


def main():
    """主函数"""
    init_session_state()
    sidebar_config()

    # 检查 API Key
    if not st.session_state.api_key:
        platform = st.session_state.current_platform
        st.warning(f"⚠️ 请先在侧边栏配置 {platform} API Key")
        st.stop()

    # 检查是否有跳转标志（从热点追踪跳转）
    if st.session_state.get('go_to_writer'):
        st.session_state.go_to_writer = False
        main_writer()
        return

    # 页面选择 - 侧边栏导航
    page_options = ["✍️ 写文章", "🔥 热点追踪", "📚 历史记录", "📁 文件管理", "⏰ 定时任务"]
    page_to_index = {
        "write": 0,
        "hot_topics": 1,
        "history": 2,
        "viewer": 3,  # 文件管理页面
        "scheduler": 4
    }

    # 如果有预设主题或 URL 参数，默认选择写文章页面
    default_index = 0
    query_params = st.query_params.to_dict()

    # 检查 page 参数，设置正确的默认索引
    if query_params.get('page') == 'viewer':
        default_index = 3  # 文件管理页面
    elif st.session_state.get('topic') or query_params.get('page') == 'write':
        default_index = 0  # 写文章页面
        # 清除 URL 参数
        if 'page' in query_params:
            del st.query_params['page']

    # 检查是否有 page 参数（用于从执行记录跳转）
    current_page = query_params.get('page', '')

    page = st.sidebar.radio(
        "导航",
        page_options,
        index=min(default_index, len(page_options) - 1)
    )

    # 执行对应页面函数
    if page == "✍️ 写文章":
        main_writer()
    elif page == "🔥 热点追踪":
        show_hot_topics()
    elif page == "📚 历史记录":
        show_history()
    elif page == "📁 文件管理":
        show_markdown_viewer()
    else:
        show_scheduler()


def main_writer():
    """主写作流程"""
    # 步骤导航
    step = st.session_state.current_step
    progress_labels = ["输入主题", "确认大纲", "预览文章"]

    if step > 1:
        st.progress(step / 3)
        st.tabs([f"✓ {l}" if i < step else l for i, l in enumerate(progress_labels)])

    # 步骤 1: 输入主题
    if step == 1:
        result = step1_input_topic()
        topic, template_type, custom_requirements = result

        # 如果有预设主题（从热点追踪跳转），覆盖输入
        if hasattr(st.session_state, 'topic') and st.session_state.topic:
            topic = st.session_state.topic
            template_type = st.session_state.get('template_type', 'newsAnalysis')
            custom_requirements = st.session_state.get('custom_requirements', '')

        # 保存当前输入到 session
        st.session_state.topic = topic
        st.session_state.template_type = template_type
        st.session_state.custom_requirements = custom_requirements

        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🚀 生成大纲", type="primary", use_container_width=True):
                if not topic.strip():
                    st.error("请输入文章主题")
                else:
                    with st.spinner(f"正在生成文章大纲 (使用 {st.session_state.model_name})..."):
                        try:
                            generator = ArticleGenerator(
                                api_key=st.session_state.api_key,
                                base_url=st.session_state.base_url,
                                model=st.session_state.model_name
                            )
                            outline = asyncio.run(
                                generator.generate_outline(
                                    topic,
                                    template_type,
                                    custom_requirements,
                                    model=st.session_state.model_name
                                )
                            )
                            st.session_state.outline = outline
                            st.session_state.current_step = 2
                            st.rerun()
                        except Exception as e:
                            st.error(f"生成失败：{str(e)}")

    # 步骤 2: 预览大纲
    elif step == 2 and st.session_state.outline:
        outline = st.session_state.outline

        # 显示导航
        if st.button("← 返回修改", key="back_to_step1"):
            st.session_state.current_step = 1
            st.rerun()

        edited_sections = step2_preview_outline(outline)

        # 更新大纲
        outline.sections = edited_sections

        col1, col2 = st.columns(2)
        with col1:
            if st.button("← 返回修改", use_container_width=True):
                st.session_state.current_step = 1
                st.rerun()

        with col2:
            if st.button("✍️ 开始撰写全文", type="primary", use_container_width=True):
                with st.spinner(f"正在撰写文章，这可能需要 1-2 分钟 (使用 {st.session_state.model_name})..."):
                    try:
                        generator = ArticleGenerator(
                            api_key=st.session_state.api_key,
                            base_url=st.session_state.base_url,
                            model=st.session_state.model_name
                        )
                        # 使用编辑后的大纲重新生成
                        edited_outline = ArticleOutline(
                            title=st.session_state.get("edit_title", outline.title),
                            subtitle=st.session_state.get("edit_subtitle", outline.subtitle),
                            sections=edited_sections,
                            suggested_cover=outline.suggested_cover
                        )
                        # 直接生成全文
                        article_full = asyncio.run(
                            generator.generate_article(
                                st.session_state.get("topic", ""),
                                st.session_state.get("template_type", "general"),
                                st.session_state.get("custom_requirements"),
                                save=True,
                                model=st.session_state.model_name
                            )
                        )
                        st.session_state.generated_article = article_full
                        st.session_state.current_step = 3
                        st.rerun()
                    except Exception as e:
                        st.error(f"生成失败：{str(e)}")

    # 步骤 3: 预览文章
    elif step == 3 and st.session_state.generated_article:
        article = st.session_state.generated_article
        step3_preview_article(article)

        if st.button("← 返回大纲", key="back_to_step2"):
            st.session_state.current_step = 2
            st.rerun()


def show_history():
    """显示历史记录"""
    st.markdown("## 📚 历史记录")

    try:
        session = get_session()
        articles = session.query(Article).order_by(Article.created_at.desc()).limit(50).all()

        if not articles:
            st.info("暂无历史记录")
            session.close()
            return

        for article in articles:
            with st.expander(f"📄 {article.title} - {article.created_at.strftime('%Y-%m-%d %H:%M')}"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("类型", article.template_type)
                with col2:
                    st.metric("状态", article.status)
                with col3:
                    st.metric("字数", f"约{len(article.content)}字")

                st.markdown(article.content[:500] + "..." if len(article.content) > 500 else article.content)

                # 操作
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("📋 复制", key=f"copy_{article.id}"):
                        st.code(article.content, language="markdown")
                with col2:
                    if st.button("🗑️ 删除", key=f"delete_{article.id}"):
                        session.delete(article)
                        session.commit()
                        st.rerun()
                with col3:
                    if st.button("📥 下载", key=f"download_{article.id}"):
                        st.download_button(
                            label="下载 Markdown",
                            data=article.content,
                            file_name=f"{article.title}.md",
                            mime="text/markdown"
                        )

        session.close()

    except Exception as e:
        st.error(f"加载历史记录失败：{str(e)}")


def show_markdown_viewer():
    """Markdown 文件浏览/编辑器"""
    st.markdown("## 📁 文件管理")
    st.markdown("浏览和管理 output 目录的 Markdown 文件")

    file_manager = get_file_manager()

    # 扫描文件列表
    files = file_manager.scan_output_directory()

    if not files:
        st.info("output 目录暂无 Markdown 文件")
        return

    # 使用两列布局：左侧文件列表 (25%)，右侧内容区域 (75%)
    list_col, content_col = st.columns([1, 3])

    # 左侧：文件列表
    with list_col:
        st.markdown("### 📂 文件列表")
        st.caption(f"共 {len(files)} 个文件")

        # 搜索/过滤
        search_query = st.text_input("🔍 搜索文件", placeholder="输入标题关键词...", key="file_search")

        # 过滤文件
        filtered_files = files
        if search_query:
            filtered_files = [f for f in files if search_query.lower() in f.title.lower()]
            st.caption(f"找到 {len(filtered_files)} 个结果")

        # 滚动文件列表
        with st.container():
            for i, file_info in enumerate(filtered_files):
                file_label = f"📄 {file_info.title[:18]}..." if len(file_info.title) > 18 else f"📄 {file_info.title}"
                file_size_kb = file_info.size / 1024
                size_text = f"{file_size_kb:.1f}KB"

                # 选中样式
                is_selected = st.session_state.get("selected_file") == file_info.path

                if st.button(
                    file_label,
                    key=f"file_{i}_{file_info.path}",
                    use_container_width=True,
                    type="primary" if is_selected else "secondary"
                ):
                    st.session_state.selected_file = file_info.path
                    st.rerun()

        st.divider()

        # 批量操作
        st.markdown("### 🔧 批量操作")
        if st.button("🔄 刷新列表", use_container_width=True):
            st.rerun()

        # 删除选中的文件
        selected_file = st.session_state.get("selected_file")
        if selected_file:
            st.markdown("---")
            if st.button("🗑️ 删除当前文件", type="secondary", use_container_width=True):
                st.session_state.show_delete_confirm = selected_file
                st.rerun()

            # 显示删除确认
            if st.session_state.get("show_delete_confirm") == selected_file:
                st.warning("确认删除？")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("确认", use_container_width=True, type="primary"):
                        if file_manager.delete_file(selected_file):
                            st.success("已删除")
                            st.session_state.selected_file = None
                            st.session_state.show_delete_confirm = None
                            st.rerun()
                        else:
                            st.error("删除失败")
                with col2:
                    if st.button("取消", use_container_width=True):
                        st.session_state.show_delete_confirm = None
                        st.rerun()

    # 右侧：文件内容区域
    with content_col:
        selected_file = st.session_state.get("selected_file")

        if not selected_file:
            # 默认选择第一个文件
            if files:
                selected_file = files[0].path
                st.session_state.selected_file = selected_file
            else:
                st.info("请点击左侧选择一个文件")
                return

        file_info = file_manager.get_file_info(selected_file)
        if not file_info:
            st.error("文件不存在，可能已被删除")
            st.session_state.selected_file = None
            st.rerun()
            return

        # 文件信息头部
        st.markdown(f"### {file_info.get('title', 'Unknown')}")
        st.caption(
            f"📁 {file_info.get('name', 'Unknown')} | "
            f"📊 {file_info.get('size', 0) / 1024:.1f}KB | "
            f"🕐 修改：{file_info.get('modified_at', 'Unknown')}"
        )

        # 读取内容
        content, html_preview = file_manager.get_content_with_preview(selected_file)

        if not content:
            st.error("无法读取文件内容")
            return

        # 浏览/编辑 切换
        view_mode = st.radio("显示模式", ["📖 浏览", "✏️ 编辑"], horizontal=True, key="view_mode_toggle")

        if view_mode == "📖 浏览":
            st.markdown("---")
            # 使用可滚动容器显示内容
            with st.container():
                st.markdown(html_preview, unsafe_allow_html=True)
        else:
            st.markdown("---")
            edited_content = st.text_area(
                "编辑内容",
                value=content,
                height=400,
                label_visibility="collapsed",
                key="editor_content"
            )

            # 操作按钮
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("💾 保存", use_container_width=True, type="primary"):
                    if file_manager.save_file(selected_file, edited_content):
                        st.success("保存成功！")
                        st.session_state.modified = True
                        st.rerun()
                    else:
                        st.error("保存失败")
            with col2:
                if st.button("📋 复制全文", use_container_width=True):
                    st.code(edited_content, language="markdown")
                    st.success("已复制到代码块")
            with col3:
                pass  # 留空

        # 下载按钮
        st.download_button(
            label="⬇️ 下载文件",
            data=content,
            file_name=file_info.get('name', 'file.md'),
            mime="text/markdown",
            use_container_width=True
        )

    # 同步到数据库（隐藏功能，放在底部）
    with st.expander("🔄 数据库同步"):
        if st.button("同步文件列表到数据库"):
            file_manager.sync_to_database()
            st.success("同步完成！")


def show_hot_topics():
    """显示热点追踪页面"""
    st.markdown("## 🔥 热点追踪")
    st.markdown("实时获取各平台热门话题，帮你快速捕捉写作灵感")

    # 获取热点数据
    tracker = get_tracker()

    # 缓存控制（30 分钟内不重复获取）
    now = datetime.now()
    last_fetch = st.session_state.get("hot_topics_last_fetch")
    hot_topics = st.session_state.get("hot_topics")

    force_refresh = st.button("🔄 刷新热点", help="手动刷新热点数据")

    if force_refresh or last_fetch is None or (now - last_fetch).seconds > 1800:
        with st.spinner("正在获取热点数据..."):
            hot_topics = tracker.get_all_hot_topics(limit_per_platform=10)
            st.session_state.hot_topics = hot_topics
            st.session_state.hot_topics_last_fetch = now
            st.rerun()

    if not hot_topics:
        st.warning("暂无热点数据，请点击刷新按钮")
        return

    # 显示各平台热点
    platform_tabs = st.tabs(list(hot_topics.keys()))

    for i, (platform, topics) in enumerate(hot_topics.items()):
        with platform_tabs[i]:
            st.markdown(f"### {platform} 热搜榜")

            for topic in topics:
                col1, col2 = st.columns([5, 1])
                with col1:
                    rank_icon = "🥇" if topic.rank == 1 else "🥈" if topic.rank == 2 else "🥉" if topic.rank == 3 else f"#{topic.rank}"
                    hot_text = f" · 🔥 {topic.hot_value}" if topic.hot_value else ""
                    # 显示标题（移除 Markdown 链接，因为 Streamlit 不支持外部链接）
                    st.markdown(f"**{rank_icon} {topic.title}**{hot_text}")
                    if topic.summary:
                        st.caption(topic.summary[:80] + "..." if len(topic.summary) > 80 else topic.summary)
                    # 显示可点击的链接
                    if topic.url:
                        st.markdown(f"<a href='{topic.url}' target='_blank' style='font-size:12px;color:#666;'>🔗 查看详情</a>", unsafe_allow_html=True)
                with col2:
                    # 一键生成文章按钮
                    if st.button("✍️ 写文章", key=f"write_{platform}_{topic.rank}"):
                        # 保存主题到 session
                        st.session_state.topic = topic.title
                        st.session_state.template_type = "newsAnalysis"
                        st.session_state.current_step = 1
                        # 清空热点数据
                        st.session_state.hot_topics = None
                        st.session_state.hot_topics_last_fetch = None
                        # 设置跳转标志
                        st.session_state.go_to_writer = True
                        st.rerun()
                st.divider()


def show_scheduler():
    """显示定时任务页面"""
    st.markdown("## ⏰ 定时任务")
    st.markdown("设置定时任务，自动根据热点生成文章或定时发布")

    scheduler = get_scheduler()

    # 任务列表
    tasks = scheduler.list_tasks()

    # 创建新任务表单
    with st.expander("➕ 创建新任务", expanded=len(tasks) == 0):
        with st.form("create_task_form"):
            task_name = st.text_input("任务名称", placeholder="例如：每日 AI 新闻早报")

            task_type = st.selectbox(
                "任务类型",
                options=["generate_article", "publish_article"],
                format_func=lambda x: "自动生成文章" if x == "generate_article" else "自动发布文章"
            )

            col1, col2 = st.columns(2)
            with col1:
                schedule_type = st.selectbox(
                    "执行频率",
                    options=["daily", "weekly", "hourly", "custom"],
                    format_func=lambda x: {"daily": "每天", "weekly": "每周", "hourly": "每小时", "custom": "自定义"}.get(x, x)
                )

            with col2:
                if schedule_type == "daily":
                    hour = st.number_input("执行时间（时）", min_value=0, max_value=23, value=9)
                    cron_expr = f"0 {hour} * * *"
                elif schedule_type == "weekly":
                    weekday = st.selectbox("星期几", options=[0, 1, 2, 3, 4, 5, 6], format_func=lambda x: f"星期{x + 1}" if x > 0 else "周日")
                    hour = st.number_input("执行时间（时）", min_value=0, max_value=23, value=9)
                    cron_expr = f"0 {hour} * * {weekday}"
                elif schedule_type == "hourly":
                    minute = st.number_input("执行分钟", min_value=0, max_value=59, value=0)
                    cron_expr = f"{minute} * * * *"
                else:
                    cron_expr = st.text_input("Cron 表达式", placeholder="* * * * * (分 时 日 月 周)")

            # 任务参数
            st.markdown("**任务参数**")
            topic_source = st.radio(
                "主题来源",
                options=["fixed", "hot_topic"],
                format_func=lambda x: "固定主题" if x == "fixed" else "根据热点"
            )

            if topic_source == "fixed":
                fixed_topic = st.text_input("固定主题", placeholder="例如：AI 技术发展最新动态")
                task_params = {
                    "topic": fixed_topic,
                    "template_type": "newsAnalysis"
                }
            else:
                hot_platform = st.selectbox("热点平台", options=["微博", "知乎", "百度", "抖音"])
                hot_rank = st.slider("获取排名", min_value=1, max_value=10, value=1)
                task_params = {
                    "topic": "hot_topic",
                    "template_type": "newsAnalysis",
                    "platform": hot_platform,
                    "rank": hot_rank
                }

            # 同步到公众号选项
            st.markdown("**同步设置**")
            sync_to_wechat = st.checkbox(
                "同步到微信公众号草稿箱",
                value=False,
                help="需要先在侧边栏配置公众号 AppID 和 AppSecret"
            )
            task_params["sync_to_wechat"] = sync_to_wechat

            submitted = st.form_submit_button("创建任务", type="primary", use_container_width=True)

            if submitted:
                if task_name and cron_expr:
                    task_id = scheduler.create_task(
                        name=task_name,
                        task_type=task_type,
                        cron_expression=cron_expr,
                        parameters=task_params
                    )
                    st.success(f"任务创建成功！ID: {task_id}")
                    st.rerun()
                else:
                    st.error("请填写完整的任务信息")

    # 显示任务列表
    if tasks:
        st.markdown(f"### 已创建任务 ({len(tasks)}个)")

        for task in tasks:
            with st.expander(f"**{task.name}** - {task.task_type}", expanded=False):
                status = "🟢 已启用" if task.enabled else "🔴 已禁用"
                st.markdown(f"**状态**: {status}")
                st.markdown(f"**Cron 表达式**: `{task.cron_expression}`")
                st.markdown(f"**上次执行**: {task.last_run or '尚未执行'}")
                st.markdown(f"**下次执行**: {task.next_run or '未设置'}")

                # 操作按钮
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if st.button("⏯️ 切换状态" if task.enabled else "▶️ 启用", key=f"toggle_{task.id}", use_container_width=True):
                        scheduler.toggle_task(task.id)
                        st.rerun()
                with col2:
                    if st.button("📝 编辑", key=f"edit_{task.id}", use_container_width=True):
                        # 这里可以添加编辑功能
                        st.info("编辑功能开发中...")
                with col3:
                    if st.button("🗑️ 删除", key=f"delete_{task.id}", use_container_width=True):
                        scheduler.delete_task(task.id)
                        st.rerun()
                with col4:
                    if st.button("▶️ 立即执行", key=f"run_{task.id}", use_container_width=True):
                        # 立即执行一次任务
                        callback = scheduler._callbacks.get(task.task_type)
                        if callback:
                            try:
                                # 回调是普通函数，内部自己处理事件循环
                                result = callback(**task.parameters)

                                # 提取 file_path（如果回调返回字典）
                                file_path = None
                                message = "任务执行成功"
                                if isinstance(result, dict):
                                    file_path = result.get("file_path")
                                    message = result.get("message", "任务执行成功")

                                st.success(message)

                                # 记录执行历史（包含 file_path）
                                scheduler._log_task_history(
                                    task.id,
                                    "success",
                                    message,
                                    0,
                                    file_path
                                )

                                # 更新上次执行时间
                                scheduler._update_task_last_run(task.id)
                                st.rerun()
                            except Exception as e:
                                st.error(f"执行失败：{e}")
                                # 记录失败历史
                                scheduler._log_task_history(
                                    task.id,
                                    "failed",
                                    str(e),
                                    0,
                                    None
                                )

                # 执行历史
                history = scheduler.get_task_history(task.id, limit=5)
                if history:
                    st.markdown("**最近执行记录**")
                    for record in history:
                        icon = "✅" if record["status"] == "success" else "❌"
                        st.caption(f"{icon} {record['executed_at']} - 耗时 {record['duration']:.2f}s")
    else:
        st.info("暂无定时任务")

    # 显示所有任务的最新执行记录
    st.markdown("---")
    st.markdown("### 📊 最新执行记录")

    all_history = scheduler.get_latest_history(limit=10)
    if all_history:
        for record in all_history:
            task_name = record.get("task_name", f"任务 ID:{record['task_id']}")
            icon = "✅" if record["status"] == "success" else "❌"
            file_path = record.get("file_path")

            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                with col1:
                    st.markdown(f"**{icon} {task_name}**")
                with col2:
                    st.caption(f"{record['executed_at']}")
                with col3:
                    st.caption(f"耗时 {record['duration']:.2f}s")
                with col4:
                    # 如果有文件路径，显示查看按钮
                    if file_path:
                        if st.button("📄 查看", key=f"view_{record.get('executed_at', '')}", use_container_width=True):
                            st.session_state.selected_file = file_path
                            st.query_params.page = "viewer"
                            st.rerun()

                if record.get("result"):
                    result_text = record.get("result", "")
                    if len(result_text) > 80:
                        result_text = result_text[:80] + "..."
                    st.caption(f"结果：{result_text}")
                st.divider()
    else:
        st.caption("暂无执行记录")


# 注册任务回调
def _generate_article_callback(topic: str, template_type: str = "newsAnalysis", sync_to_wechat: bool = False, **kwargs):
    """定时任务：生成文章的回调

    Args:
        topic: 文章主题
        template_type: 文章类型
        sync_to_wechat: 是否同步到微信公众号草稿箱
    """
    import os
    import json
    from pathlib import Path
    from app.generator import ArticleGenerator
    from app.hot_topics import get_tracker
    from app.models import get_session, Article, TaskHistory
    from app.wechat import WeChatAPI, markdown_to_wechat_html

    # 直接读取配置文件
    config_file = Path("data/config.json")
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    current_platform = config.get("current_platform", "通义千问")
    platform_config = config.get("platforms", {}).get(current_platform, {})
    model = platform_config.get("model_name", "qwen3.5-plus")
    api_key = platform_config.get("api_key", "")
    base_url = platform_config.get("base_url", "")

    # 微信公众号配置
    wechat_config = config.get("wechat", {})
    wechat_app_id = wechat_config.get("app_id", "")
    wechat_app_secret = wechat_config.get("app_secret", "")

    print(f"DEBUG: platform={current_platform}, model={model}")

    # 如果没有配置，尝试从环境变量获取
    if not api_key:
        api_key = os.getenv("DASHSCOPE_API_KEY", "")

    # 如果是热点主题，先获取热点
    if topic == "hot_topic":
        tracker = get_tracker()
        hot_platform = kwargs.get("platform", "微博")
        rank = kwargs.get("rank", 1)
        topics = tracker.get_all_hot_topics(limit_per_platform=rank + 1)
        if hot_platform in topics and len(topics[hot_platform]) >= rank:
            topic = topics[hot_platform][rank - 1].title
        else:
            topic = "AI 技术最新发展"

    # 创建新事件循环执行异步任务
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    file_path = None
    article_id = None
    wechat_media_id = None
    wechat_sync_result = None

    try:
        generator = ArticleGenerator(
            api_key=api_key,
            base_url=base_url,
            model=model
        )
        article = loop.run_until_complete(
            generator.generate_article(topic, template_type=template_type, save=True, model=model)
        )
        print(f"任务执行成功：文章已生成 - {article.title}")

        # 获取生成的文件路径
        output_dir = Path("output")
        if output_dir.exists():
            files = sorted(output_dir.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)
            if files:
                file_path = str(files[0])

        # 同步到数据库
        try:
            session = get_session()
            db_article = Article(
                title=article.title,
                subtitle=article.subtitle,
                topic=topic,
                template_type=template_type,
                content=article.content,
                outline={
                    "sections": article.outline.sections,
                    "suggested_cover": article.outline.suggested_cover
                },
                status="draft",
                file_path=file_path,
                created_at=datetime.now()
            )
            session.add(db_article)
            session.commit()
            article_id = db_article.id

            # 如果配置了公众号且要求同步，执行同步操作
            if sync_to_wechat and wechat_app_id and wechat_app_secret:
                try:
                    print(f"正在同步到微信公众号草稿箱...")
                    wechat_api = WeChatAPI(app_id=wechat_app_id, app_secret=wechat_app_secret)

                    # 获取访问令牌
                    token = wechat_api._get_access_token()

                    # 转换 HTML 格式
                    theme_color = "#1E88E5"  # 默认蓝色
                    html_content = markdown_to_wechat_html(article.content, theme_color)

                    # 保存到草稿箱
                    result = wechat_api.add_draft(
                        title=article.title,
                        content=html_content,
                        author="",
                        digest=article.subtitle or "",
                        show_cover=True
                    )

                    if result.get("errcode", 1) == 0:
                        wechat_media_id = result.get("media_id", "")
                        wechat_sync_result = f"草稿箱同步成功，media_id: {wechat_media_id}"
                        # 更新文章记录
                        db_article.wechat_media_id = wechat_media_id
                        db_article.status = "synced"
                        session.commit()
                        print(f"微信公众号同步成功：{wechat_media_id}")
                    else:
                        wechat_sync_result = f"草稿箱同步失败：{result.get('errmsg', '未知错误')}"
                        print(f"微信公众号同步失败：{result}")
                except Exception as wechat_error:
                    wechat_sync_result = f"草稿箱同步异常：{str(wechat_error)}"
                    print(f"微信公众号同步异常：{wechat_error}")

            # 更新最新的 TaskHistory 记录
            latest_history = session.query(TaskHistory).order_by(TaskHistory.executed_at.desc()).first()
            if latest_history and latest_history.file_path is None:
                latest_history.file_path = file_path
                latest_history.article_id = article_id
                session.commit()

            session.close()
        except Exception as e:
            print(f"同步数据库失败：{e}")

    finally:
        loop.close()

    # 返回包含 file_path 的字典
    result_dict = {
        "message": f"文章已生成：{article.title}",
        "file_path": file_path,
        "article_id": article_id
    }

    if wechat_sync_result:
        result_dict["message"] += f"; {wechat_sync_result}"

    return result_dict


# 初始化时注册回调
def _register_scheduler_callbacks():
    """注册调度器回调函数"""
    scheduler = get_scheduler()
    scheduler.register_callback("generate_article", _generate_article_callback)


# 在初始化 session state 时注册回调
if "scheduler_callbacks_registered" not in st.session_state:
    _register_scheduler_callbacks()
    st.session_state.scheduler_callbacks_registered = True


if __name__ == "__main__":
    main()
