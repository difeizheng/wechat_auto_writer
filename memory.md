# Memory - 公众号文章自动生成系统

## 项目位置
`D:\project_room\workspace2024\mytest\wechat_auto_writer`

## 项目状态 (2026-03-19 重构更新)

### 已完成功能

1. **多平台 AI 支持**
   - 通义千问 (Base URL: https://coding.dashscope.aliyuncs.com/v1)
   - OpenAI (Base URL: https://api.openai.com/v1)
   - DeepSeek (Base URL: https://api.deepseek.com/v1)
   - 智谱 AI (Base URL: https://open.bigmodel.cn/api/paas/v4)
   - 自定义平台

2. **配置持久化**
   - 配置文件：`data/config.json`
   - 每个平台独立保存：API Key、Base URL、模型名称、自定义模型列表、隐藏模型列表
   - 切换平台自动加载对应配置

3. **模型管理**
   - 下拉选择模型
   - 添加自定义模型
   - 隐藏/恢复默认模型
   - 删除自定义模型

4. **文章生成流程**
   - 输入主题 → 生成大纲 → 确认/修改 → 生成全文
   - 支持多种文章类型：通用、技术教程、资讯解读、观点评论、产品推广
   - Markdown 预览和导出
   - HTML 格式导出（微信公众号格式）

5. **历史记录**
   - SQLite 数据库存储
   - 支持查看、复制、删除、下载

6. **微信公众号排版优化** (2026-03-18 新增)
   - 6 种预设主题：默认蓝、清新绿、活力橙、优雅紫、中国红、商务黑
   - 精美的 CSS 样式：标题、引用、代码块、列表、表格等
   - 自动美化处理：渐变背景、圆角、阴影效果
   - 支持主题颜色自定义

7. **热点追踪功能** (2026-03-18 新增)
   - 支持平台：微博、知乎、百度、抖音、36 氪
   - 实时获取各平台热搜榜
   - 一键生成热点文章
   - 30 分钟缓存机制

8. **定时任务支持** (2026-03-18 新增，2026-03-19 修复并重构)
   - 支持每天/每周/每小时定时执行
   - 支持自定义 Cron 表达式
   - 任务类型：自动生成文章、自动发布文章
   - 支持固定主题或根据热点生成
   - 任务执行历史记录（带文件链接）
   - **修复** (2026-03-19)：定时任务模型名称读取错误问题
   - **重构** (2026-03-19)：统一数据库，使用 SQLAlchemy

9. **Markdown 文件管理** (2026-03-19 新增)
   - 浏览 output 目录所有 Markdown 文件
   - 在线预览和编辑
   - 保存、删除、下载文件
   - 从定时任务执行记录跳转到文件查看

10. **微信公众号草稿箱同步** (2026-03-19 新增)
    - 侧边栏配置公众号 AppID 和 AppSecret
    - 文章生成后一键同步到草稿箱
    - 定时任务支持自动同步选项
    - 自动转换 Markdown 为微信公众号 HTML 格式
    - 数据库记录 wechat_media_id 字段

### 技术栈
- 前端：Streamlit 1.32.0
- AI：OpenAI SDK 兼容模式 (支持多平台)
- 数据库：SQLite + SQLAlchemy 2.0
- 部署：Docker / 本地运行

### 当前运行状态
- 端口：8601
- 命令：`streamlit run app/main.py --server.port=8601 --server.headless=true`
- 访问地址：http://localhost:8601

### 项目结构
```
wechat_auto_writer/
├── app/
│   ├── __init__.py
│   ├── main.py              # Streamlit 主界面
│   ├── generator.py         # AI 文章生成逻辑
│   ├── models.py            # 数据库模型 (统一数据库)
│   ├── wechat.py            # 微信公众号 API 封装
│   ├── hot_topics.py        # 热点追踪功能
│   ├── scheduler.py         # 定时任务调度器 (SQLAlchemy)
│   └── file_manager.py      # 文件管理器 (新增)
├── data/
│   ├── articles.db          # SQLite 统一数据库
│   └── config.json          # 配置文件
├── output/                  # 生成的文章
├── scripts/
│   └── migrate_db.py        # 数据库迁移脚本
├── .streamlit/
│   └── config.toml          # Streamlit 配置
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── start.bat
└── README.md
```

### 数据库表结构
```sql
articles          -- 文章记录
scheduled_tasks   -- 定时任务
task_history      -- 任务执行历史
markdown_files    -- Markdown 文件记录
```

### Git 信息
- 最新提交：`4f481ca` - feat: 文件管理页面增加同步到公众号功能
- 版本 Tag：`v2.2`、`v2.1`、`v2.0`、`refactor-unified-db-20260319`、`v1.0`
- 仓库：https://github.com/difeizheng/wechat_auto_writer.git

### 下一步工作
- [ ] 添加更多排版主题模板
- [ ] 优化热点追踪成功率（备用 API）
- [ ] 定时任务邮件通知
- [ ] 定时任务参数编辑功能（目前显示"开发中"）
- [ ] 文件管理批量操作（批量删除）
- [ ] 更新 README.md 文档
- [ ] 微信公众号正式发布集成（目前仅支持草稿箱）

### 注意事项
- 需要在侧边栏配置 API Key 才能使用
- 每个平台的配置独立保存
- 自定义平台需要输入 Base URL 和至少一个模型名称
- Streamlit 1.32.0 不支持 `st.switch_page`、`st.Page` 等新版 API
- 数据库已统一为 `data/articles.db`（包含所有表）
- 文件管理页面采用两列布局，支持搜索过滤

---

## 更新记录

### v2.2 (2026-03-19) - 文件管理页面同步功能

**新增功能**:

1. **文件管理页面同步到公众号**
   - 新增"📱 同步到公众号"区域
   - 点击按钮直接将 Markdown 文件同步到草稿箱
   - 自动提取 Markdown 标题（第一个 # 标题）
   - 自动提取摘要（正文前 120 字符）
   - 同步成功后显示 media_id

**修改的文件**:
- `app/main.py` - 新增 sync_file_to_wechat 函数，修改文件管理页面 UI
- `app/models.py` - MarkdownFile 模型新增 wechat_media_id 字段

---

### v2.1 (2026-03-19) - 微信公众号草稿箱同步

**新增功能**:

1. **微信公众号草稿箱同步**
   - 侧边栏配置：公众号 AppID、AppSecret
   - 文章预览页：一键同步到草稿箱按钮
   - 定时任务：支持自动同步选项
   - 自动将 Markdown 转换为微信公众号 HTML 格式
   - 同步成功后自动更新数据库状态

**修改的文件**:
- `app/main.py` - 新增公众号配置、sync_to_wechat_draft 函数、更新定时任务回调
- `app/models.py` - Article 模型新增 wechat_media_id 字段
- `app/wechat.py` - 已有 add_draft 等方法，直接使用
- `memory.md` - 更新文档

---

### v2.0 (2026-03-19) - 架构重构与功能增强

**重构内容**：

1. **统一数据库**
   - 将 `articles.db` 和 `scheduler.db` 合并为统一数据库
   - 使用 SQLAlchemy ORM 替代原生 sqlite3
   - 新增表：`TaskHistory`、`MarkdownFile`、`ScheduledTask`

2. **新增文件管理模块** (`app/file_manager.py`)
   - `FileManager` 类：扫描、读取、保存、删除 Markdown 文件
   - `sync_to_database()`：同步文件列表到数据库

3. **新增 Markdown 浏览/编辑页面**
   - 两列布局：左侧文件列表（25%），右侧内容区域（75%）
   - 浏览模式：Markdown 渲染预览
   - 编辑模式：在线编辑并保存
   - 支持搜索过滤、下载、删除文件

4. **定时任务执行记录增强**
   - 记录生成文件的路径 (`file_path`)
   - 显示"📄 查看"按钮，点击跳转到文件管理页面
   - 使用 `get_latest_history()` 获取包含任务名称的执行记录

5. **数据库迁移脚本** (`scripts/migrate_db.py`)
   - 将旧 `scheduler.db` 数据迁移到 `articles.db`

**修改的文件**：
- `app/models.py` - 新增模型，统一数据库
- `app/scheduler.py` - 改用 SQLAlchemy
- `app/main.py` - 新增 `show_markdown_viewer()`，修改执行记录显示
- `app/file_manager.py` - 新增文件管理模块
- `scripts/migrate_db.py` - 新增迁移脚本

---

## 重要问题修复记录

### 2026-03-19: 定时任务模型名称读取错误

**问题描述**：
- 用户侧边栏配置使用 `qwen3.5-plus` 模型
- 执行定时任务时报错：`model qwen-plus is not supported`

**原因分析**：
- `_generate_article_callback` 函数使用 `st.session_state.current_platform` 读取平台
- 定时任务在后台线程执行，无法访问 Streamlit 的 session state
- 导致回退到预设模型的第一个 `qwen-plus`

**修复方案**：
修改 `app/main.py` 中的 `_generate_article_callback` 函数，直接从配置文件读取：

```python
def _generate_article_callback(topic: str, template_type: str = "newsAnalysis", **kwargs):
    import json
    from pathlib import Path

    # 直接读取配置文件
    config_file = Path("data/config.json")
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    current_platform = config.get("current_platform", "通义千问")
    platform_config = config.get("platforms", {}).get(current_platform, {})
    model = platform_config.get("model_name", "qwen3.5-plus")
    api_key = platform_config.get("api_key", "")
    base_url = platform_config.get("base_url", "")

    # 使用读取的配置创建生成器
    generator = ArticleGenerator(
        api_key=api_key,
        base_url=base_url,
        model=model
    )
```

**验证方式**：
- 执行定时任务，检查是否正确使用配置文件中保存的模型名称
