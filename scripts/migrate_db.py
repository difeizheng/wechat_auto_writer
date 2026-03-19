"""
数据库迁移脚本
将旧 scheduler.db 的数据迁移到统一的 articles.db
"""
import sys
import sqlite3
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 数据库路径
OLD_SCHEDULER_DB = Path("data/scheduler.db")
ARTICLES_DB = Path("data/articles.db")


def migrate_scheduler_data():
    """迁移定时任务数据到 articles.db"""
    if not OLD_SCHEDULER_DB.exists():
        print("旧的 scheduler.db 不存在，跳过迁移")
        return

    if not ARTICLES_DB.exists():
        print("articles.db 不存在，请先运行主程序初始化数据库")
        return

    # 连接旧数据库
    old_conn = sqlite3.connect(OLD_SCHEDULER_DB)
    old_conn.row_factory = sqlite3.Row
    old_cursor = old_conn.cursor()

    # 连接新数据库
    new_conn = sqlite3.connect(ARTICLES_DB)
    new_cursor = new_conn.cursor()

    try:
        # 迁移 scheduled_tasks 表
        old_cursor.execute("SELECT * FROM scheduled_tasks")
        tasks = old_cursor.fetchall()

        print(f"找到 {len(tasks)} 个定时任务")

        for task in tasks:
            # 检查是否已存在
            new_cursor.execute("SELECT id FROM scheduled_tasks WHERE id = ?", (task['id'],))
            if new_cursor.fetchone():
                print(f"任务 ID {task['id']} 已存在，跳过")
                continue

            new_cursor.execute("""
                INSERT OR REPLACE INTO scheduled_tasks
                (id, name, task_type, cron_expression, parameters, enabled, last_run, next_run, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task['id'],
                task['name'],
                task['task_type'],
                task['cron_expression'],
                task['parameters'],
                task['enabled'],
                task['last_run'],
                task['next_run'],
                task['created_at'],
                task['updated_at']
            ))
            print(f"迁移任务：{task['name']}")

        # 迁移 task_history 表
        old_cursor.execute("SELECT * FROM task_history")
        histories = old_cursor.fetchall()

        print(f"找到 {len(histories)} 条执行历史记录")

        for history in histories:
            new_cursor.execute("""
                INSERT INTO task_history
                (task_id, status, result, executed_at, duration, file_path, article_id)
                VALUES (?, ?, ?, ?, ?, NULL, NULL)
            """, (
                history['task_id'],
                history['status'],
                history['result'],
                history['executed_at'],
                history['duration']
            ))

        new_conn.commit()
        print("迁移完成！")

    except Exception as e:
        new_conn.rollback()
        print(f"迁移失败：{e}")
        raise
    finally:
        old_conn.close()
        new_conn.close()


def init_database():
    """初始化数据库（创建表结构）"""
    from app.models import init_db
    init_db()
    print("数据库初始化完成")


if __name__ == "__main__":
    print("=" * 50)
    print("数据库迁移工具")
    print("=" * 50)

    # 1. 初始化数据库
    print("\n1. 初始化数据库表结构...")
    init_database()

    # 2. 迁移数据
    print("\n2. 迁移旧数据...")
    migrate_scheduler_data()

    print("\n" + "=" * 50)
    print("迁移完成！")
    print("=" * 50)
