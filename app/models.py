"""
数据库模型
"""
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer, JSON
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

# SQLite 数据库
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
    status = Column(String(20), default="draft")  # draft, published, archived
    file_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    published_at = Column(DateTime, nullable=True)

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
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "published_at": self.published_at.isoformat() if self.published_at else None
        }


def init_db():
    """初始化数据库"""
    Base.metadata.create_all(engine)


def get_session():
    """获取数据库会话"""
    return Session()
