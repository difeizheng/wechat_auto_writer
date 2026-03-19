"""
数据库模型
统一数据库结构：articles.db 包含所有表
"""
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer, JSON, Float, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

Base = declarative_base()

# SQLite 数据库 - 统一数据库
engine = create_engine("sqlite:///data/articles.db", echo=False)
Session = sessionmaker(bind=engine)


class Article(Base):
    """文章记录"""
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    subtitle = Column(String(200), nullable=True)
    topic = Column(String(500), nullable=False)
    template_type = Column(String(50), default="general")
    content = Column(Text, nullable=False)
    outline = Column(JSON, nullable=True)
    status = Column(String(20), default="draft")  # draft, published, archived, synced
    file_path = Column(String(500), nullable=True)
    wechat_media_id = Column(String(100), nullable=True)  # 微信公众号草稿 media_id
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    published_at = Column(DateTime, nullable=True)

    # 关联定时任务执行历史
    task_histories = relationship("TaskHistory", back_populates="article")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "subtitle": self.subtitle,
            "topic": self.topic,
            "template_type": self.template_type,
            "content": self.content,
            "outline": self.outline,
            "status": self.status,
            "file_path": self.file_path,
            "wechat_media_id": self.wechat_media_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "published_at": self.published_at.isoformat() if self.published_at else None
        }


class ScheduledTask(Base):
    """定时任务"""
    __tablename__ = "scheduled_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    task_type = Column(String(50), nullable=False)  # generate_article, publish_article
    cron_expression = Column(String(50), nullable=False)
    parameters = Column(JSON, nullable=False)
    enabled = Column(Integer, default=1)
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联执行历史
    histories = relationship("TaskHistory", back_populates="task", cascade="all, delete-orphan")


class TaskHistory(Base):
    """定时任务执行历史"""
    __tablename__ = "task_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey('scheduled_tasks.id'), nullable=True)
    status = Column(String(20), nullable=False)  # success, failed
    result = Column(Text, nullable=True)
    executed_at = Column(DateTime, default=datetime.now, index=True)
    duration = Column(Float, default=0.0)
    file_path = Column(String(500), nullable=True)  # 生成的文章文件路径
    article_id = Column(Integer, ForeignKey('articles.id'), nullable=True)  # 关联的文章 ID

    # 反向关联
    task = relationship("ScheduledTask", back_populates="histories")
    article = relationship("Article", back_populates="task_histories")


class MarkdownFile(Base):
    """Markdown 文件记录（用于文件管理）"""
    __tablename__ = "markdown_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_path = Column(String(500), unique=True, nullable=False)
    title = Column(String(200), nullable=True)
    content = Column(Text, nullable=True)
    file_size = Column(Integer, default=0)  # 字节
    created_at = Column(DateTime, default=datetime.now)
    modified_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    related_article_id = Column(Integer, ForeignKey('articles.id'), nullable=True)
    related_task_id = Column(Integer, ForeignKey('task_history.id'), nullable=True)
    wechat_media_id = Column(String(100), nullable=True)  # 微信公众号草稿 media_id

    def to_dict(self):
        return {
            "id": self.id,
            "file_path": self.file_path,
            "title": self.title,
            "content": self.content,
            "file_size": self.file_size,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "modified_at": self.modified_at.isoformat() if self.modified_at else None,
            "related_article_id": self.related_article_id,
            "related_task_id": self.related_task_id,
            "wechat_media_id": self.wechat_media_id
        }


def init_db():
    """初始化数据库"""
    Base.metadata.create_all(engine)


def get_session():
    """获取数据库会话"""
    return Session()
