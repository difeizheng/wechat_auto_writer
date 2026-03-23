"""
文件管理模块
用于扫描、读取、保存 output 目录的 Markdown 文件
"""
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass

from app.models import get_session, MarkdownFile


@dataclass
class FileInfo:
    """文件信息"""
    path: str
    name: str
    title: str
    size: int
    created_at: datetime
    modified_at: datetime


class FileManager:
    """文件管理器"""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def scan_output_directory(self) -> List[FileInfo]:
        """扫描 output 目录，返回文件列表"""
        files = []
        if not self.output_dir.exists():
            return files

        for file_path in self.output_dir.glob("*.md"):
            try:
                stat = file_path.stat()
                title = self._extract_title(file_path)
                files.append(FileInfo(
                    path=str(file_path),
                    name=file_path.name,
                    title=title,
                    size=stat.st_size,
                    created_at=datetime.fromtimestamp(stat.st_ctime),
                    modified_at=datetime.fromtimestamp(stat.st_mtime)
                ))
            except Exception as e:
                print(f"读取文件信息失败 {file_path}: {e}")

        # 按修改时间倒序排列
        files.sort(key=lambda x: x.modified_at, reverse=True)
        return files

    def _extract_title(self, file_path: Path) -> str:
        """从 Markdown 文件提取标题"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                if first_line.startswith('# '):
                    return first_line[2:]
                return file_path.stem
        except:
            return file_path.stem

    def read_file(self, file_path: str) -> Optional[str]:
        """读取文件内容"""
        path = Path(file_path)
        if not path.exists():
            return None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"读取文件失败 {file_path}: {e}")
            return None

    def save_file(self, file_path: str, content: str) -> bool:
        """保存文件内容"""
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"保存文件失败 {file_path}: {e}")
            return False

    def delete_file(self, file_path: str) -> bool:
        """删除文件"""
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                return True
            return False
        except Exception as e:
            print(f"删除文件失败 {file_path}: {e}")
            return False

    def delete_files(self, file_paths: List[str]) -> Dict[str, bool]:
        """批量删除文件
        返回：{file_path: success/failure}
        """
        results = {}
        for file_path in file_paths:
            try:
                path = Path(file_path)
                if path.exists():
                    path.unlink()
                    results[file_path] = True
                else:
                    results[file_path] = False
            except Exception as e:
                print(f"删除文件失败 {file_path}: {e}")
                results[file_path] = False
        return results

    def get_file_info(self, file_path: str) -> Optional[Dict]:
        """获取文件详细信息"""
        path = Path(file_path)
        if not path.exists():
            return None

        stat = path.stat()
        return {
            "path": str(path),
            "name": path.name,
            "title": self._extract_title(path),
            "size": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
        }

    def sync_to_database(self):
        """同步文件列表到数据库"""
        session = get_session()
        try:
            files = self.scan_output_directory()
            for file_info in files:
                existing = session.query(MarkdownFile).filter_by(file_path=file_info.path).first()
                if existing:
                    existing.title = file_info.title
                    existing.file_size = file_info.size
                    existing.modified_at = file_info.modified_at
                else:
                    md_file = MarkdownFile(
                        file_path=file_info.path,
                        title=file_info.title,
                        file_size=file_info.size,
                        created_at=file_info.created_at,
                        modified_at=file_info.modified_at
                    )
                    session.add(md_file)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"同步数据库失败：{e}")
        finally:
            session.close()

    def get_content_with_preview(self, file_path: str) -> tuple:
        """获取文件内容和 HTML 预览"""
        content = self.read_file(file_path)
        if content is None:
            return None, None

        try:
            import markdown
            html = markdown.markdown(content, extensions=['extra', 'codehilite', 'toc'])
            return content, html
        except ImportError:
            return content, content


# 全局文件管理器实例
_file_manager: Optional[FileManager] = None


def get_file_manager() -> FileManager:
    """获取文件管理器单例"""
    global _file_manager
    if _file_manager is None:
        _file_manager = FileManager()
    return _file_manager
