# Memory - 公众号文章自动生成系统

## 项目位置
`D:\project_room\workspace2024\mytest\public_account\wechat_auto_writer`

## 项目状态 (2026-03-18)

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

8. **定时任务支持** (2026-03-18 新增)
   - 支持每天/每周/每小时定时执行
   - 支持自定义 Cron 表达式
   - 任务类型：自动生成文章、自动发布文章
   - 支持固定主题或根据热点生成
   - 任务执行历史记录

### 技术栈
- 前端：Streamlit
- AI：OpenAI SDK 兼容模式 (支持多平台)
- 数据库：SQLite
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
│   ├── models.py            # 数据库模型
│   └── wechat.py            # 微信公众号 API 封装
├── data/
│   ├── articles.db          # SQLite 数据库
│   └── config.json          # 配置文件 (平台、API Key、模型等)
├── output/                  # 生成的文章
├── .streamlit/
│   └── config.toml          # Streamlit 配置
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── start.bat
└── README.md
```

### 下一步工作
- [ ] 添加更多排版主题模板
- [ ] 优化热点追踪成功率（备用 API）
- [ ] 定时任务邮件通知
- [ ] 微信公众号直接发布集成

### 注意事项
- 需要在侧边栏配置 API Key 才能使用
- 每个平台的配置独立保存
- 自定义平台需要输入 Base URL 和至少一个模型名称
