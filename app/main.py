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
from app.wechat import markdown_to_wechat_html


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

        使用 Claude AI 自动生成高质量公众号文章
        """)


def step1_input_topic():
    """第一步：输入主题和要求"""
    st.markdown('<p class="main-title">📝 公众号文章自动生成器</p>', unsafe_allow_html=True)
    st.markdown("---")

    col1, col2 = st.columns([2, 1])

    with col1:
        topic = st.text_area(
            "🎯 文章主题/关键词",
            placeholder="例如：如何使用 Python 进行数据分析、2024 年 AI 发展趋势、微信小程序开发指南...",
            height=100,
            key="topic_input"
        )

    with col2:
        template_type = st.selectbox(
            "📋 文章类型",
            options=[
                ("general", "通用文章"),
                ("techTutorial", "技术教程"),
                ("newsAnalysis", "资讯解读"),
                ("opinion", "观点评论"),
                ("productPromo", "产品推广")
            ],
            format_func=lambda x: x[1],
            key="template_input"
        )

    custom_requirements = st.text_area(
        "💡 特殊要求（可选）",
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
    col1, col2, col3, col4 = st.columns(4)

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
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{article.title}</title>
</head>
<body>
    {markdown_to_wechat_html(article.content)}
</body>
</html>"""

    st.download_button(
        label="⬇️ 下载 HTML",
        data=html_content,
        file_name=f"{article.title}.html",
        mime="text/html"
    )


def main():
    """主函数"""
    init_session_state()
    sidebar_config()

    # 检查 API Key
    if not st.session_state.api_key:
        platform = st.session_state.current_platform
        st.warning(f"⚠️ 请先在侧边栏配置 {platform} API Key")
        st.stop()

    # 页面选择
    page = st.sidebar.radio(
        "导航",
        ["✍️ 写文章", "📚 历史记录"],
        index=0
    )

    if page == "✍️ 写文章":
        main_writer()
    else:
        show_history()


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


if __name__ == "__main__":
    main()
