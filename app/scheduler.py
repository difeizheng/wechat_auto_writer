"""
定时任务调度模块
支持定时生成文章、定时发布等任务
"""
import sqlite3
import json
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
import schedule


@dataclass
class ScheduledTask:
    """定时任务数据类"""
    id: Optional[int]
    name: str
    task_type: str  # "generate_article", "publish_article"
    cron_expression: str  # 简单 cron 格式：* * * * * (分 时 日 月 周)
    parameters: dict  # 任务参数
    enabled: bool
    last_run: Optional[str]
    next_run: Optional[str]
    created_at: str
    updated_at: str


class TaskScheduler:
    """任务调度器"""

    def __init__(self, db_path: str = "data/scheduler.db"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        self._callbacks: dict[str, Callable] = {}
        self._init_db()
        self._load_tasks()

    def _init_db(self):
        """初始化数据库"""
        Path(self.db_path).parent.mkdir(exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                task_type TEXT NOT NULL,
                cron_expression TEXT NOT NULL,
                parameters TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                last_run TEXT,
                next_run TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                result TEXT,
                executed_at TEXT NOT NULL,
                duration REAL,
                FOREIGN KEY (task_id) REFERENCES scheduled_tasks(id)
            )
        """)
        conn.commit()
        conn.close()

    def _load_tasks(self):
        """加载已启用的任务并注册到调度器"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, cron_expression FROM scheduled_tasks WHERE enabled = 1")
        rows = cursor.fetchall()
        conn.close()

        # 清除所有已注册的 job
        schedule.clear()

        # 重新注册启用的任务
        for row in rows:
            task_id, name, cron_expr = row
            self._schedule_task(task_id, cron_expr)

    def _schedule_task(self, task_id: int, cron_expression: str):
        """根据 cron 表达式调度任务"""
        task = self.get_task(task_id)
        if not task or not task.enabled:
            return

        callback = self._callbacks.get(task.task_type)
        if not callback:
            print(f"任务类型 {task.task_type} 未注册回调函数")
            return

        # 解析 cron 表达式 (分 时 日 月 周)
        parts = cron_expression.split()
        if len(parts) != 5:
            print(f"无效的 cron 表达式：{cron_expression}")
            return

        minute, hour, day, month, weekday = parts

        # 使用 schedule 库调度
        job = self._create_job(minute, hour, day, month, weekday, task_id, callback, task.parameters)

        if job:
            # 更新下次运行时间
            next_run = job.next_run.strftime("%Y-%m-%d %H:%M:%S")
            self._update_task_next_run(task_id, next_run)

    def _create_job(self, minute, hour, day, month, weekday, task_id, callback, parameters):
        """创建调度任务"""
        try:
            # 简化处理：只支持部分 cron 语法
            if minute == "*" and hour == "*":
                # 每分钟
                return schedule.every(1).minutes.do(
                    self._run_task, task_id=task_id, callback=callback, params=parameters
                )
            elif minute == "*/5" and hour == "*":
                # 每 5 分钟
                return schedule.every(5).minutes.do(
                    self._run_task, task_id=task_id, callback=callback, params=parameters
                )
            elif minute == "*/15" and hour == "*":
                # 每 15 分钟
                return schedule.every(15).minutes.do(
                    self._run_task, task_id=task_id, callback=callback, params=parameters
                )
            elif minute == "0" and hour == "*":
                # 每小时
                return schedule.every().hour.do(
                    self._run_task, task_id=task_id, callback=callback, params=parameters
                )
            elif minute != "*" and minute.isdigit() and hour == "*":
                # 每小时固定分钟
                return schedule.every(minute).minutes.do(
                    self._run_task, task_id=task_id, callback=callback, params=parameters
                )
            elif minute.isdigit() and hour.isdigit():
                # 每天固定时间
                if minute == "0":
                    return schedule.every().day.at(f"{hour}:00").do(
                        self._run_task, task_id=task_id, callback=callback, params=parameters
                    )
                else:
                    return schedule.every().day.at(f"{hour}:{minute.zfill(2)}").do(
                        self._run_task, task_id=task_id, callback=callback, params=parameters
                    )
            elif weekday != "*":
                # 每周固定时间
                weekdays = {"0": "sunday", "1": "monday", "2": "tuesday", "3": "wednesday",
                           "4": "thursday", "5": "friday", "6": "saturday"}
                if weekday in weekdays and hour.isdigit():
                    day_name = weekdays[weekday]
                    if minute.isdigit():
                        return schedule.every().week.day_at(f"{day_name}", f"{hour}:{minute.zfill(2)}").do(
                            self._run_task, task_id=task_id, callback=callback, params=parameters
                        )
                    else:
                        return getattr(schedule.every(), day_name).do(
                            self._run_task, task_id=task_id, callback=callback, params=parameters
                        )
            else:
                # 默认：每天固定时间
                if hour.isdigit():
                    return schedule.every().day.at(f"{hour}:00").do(
                        self._run_task, task_id=task_id, callback=callback, params=parameters
                    )
        except Exception as e:
            print(f"创建任务失败：{e}")
        return None

    def _run_task(self, task_id: int, callback: Callable, params: dict):
        """执行任务"""
        start_time = time.time()
        status = "success"
        result = ""

        try:
            print(f"执行任务 {task_id}...")
            result = callback(**params)
        except Exception as e:
            status = "failed"
            result = str(e)
            print(f"任务 {task_id} 执行失败：{e}")

        duration = time.time() - start_time

        # 记录执行历史
        self._log_task_history(task_id, status, result, duration)

        # 更新上次运行时间
        self._update_task_last_run(task_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def register_callback(self, task_type: str, callback: Callable):
        """注册任务类型的回调函数"""
        self._callbacks[task_type] = callback

    def create_task(self, name: str, task_type: str, cron_expression: str, parameters: dict) -> int:
        """创建新任务"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO scheduled_tasks
            (name, task_type, cron_expression, parameters, enabled, created_at, updated_at)
            VALUES (?, ?, ?, ?, 1, ?, ?)
        """, (name, task_type, cron_expression, json.dumps(parameters, ensure_ascii=False), now, now))

        task_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # 重新加载任务
        self._schedule_task(task_id, cron_expression)

        return task_id

    def get_task(self, task_id: int) -> Optional[ScheduledTask]:
        """获取任务详情"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM scheduled_tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return ScheduledTask(
            id=row[0],
            name=row[1],
            task_type=row[2],
            cron_expression=row[3],
            parameters=json.loads(row[4]),
            enabled=bool(row[5]),
            last_run=row[6],
            next_run=row[7],
            created_at=row[8],
            updated_at=row[9]
        )

    def list_tasks(self) -> list[ScheduledTask]:
        """获取所有任务列表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM scheduled_tasks ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()

        tasks = []
        for row in rows:
            tasks.append(ScheduledTask(
                id=row[0],
                name=row[1],
                task_type=row[2],
                cron_expression=row[3],
                parameters=json.loads(row[4]),
                enabled=bool(row[5]),
                last_run=row[6],
                next_run=row[7],
                created_at=row[8],
                updated_at=row[9]
            ))
        return tasks

    def update_task(self, task_id: int, **kwargs):
        """更新任务"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        allowed_fields = ["name", "cron_expression", "parameters", "enabled"]
        updates = []
        values = []

        for field, value in kwargs.items():
            if field in allowed_fields:
                if field == "parameters":
                    value = json.dumps(value, ensure_ascii=False)
                elif field == "enabled":
                    value = 1 if value else 0
                updates.append(f"{field} = ?")
                values.append(value)

        if updates:
            values.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            values.append(task_id)
            cursor.execute(f"""
                UPDATE scheduled_tasks
                SET {', '.join(updates)}, updated_at = ?
                WHERE id = ?
            """, values)

            conn.commit()

        conn.close()

        # 重新加载任务
        self._load_tasks()

    def delete_task(self, task_id: int):
        """删除任务"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM scheduled_tasks WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()

        # 重新加载任务
        self._load_tasks()

    def toggle_task(self, task_id: int):
        """启用/禁用任务"""
        task = self.get_task(task_id)
        if task:
            self.update_task(task_id, enabled=not task.enabled)

    def _update_task_last_run(self, task_id: int, last_run: str):
        """更新任务上次运行时间"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE scheduled_tasks SET last_run = ? WHERE id = ?", (last_run, task_id))
        conn.commit()
        conn.close()

    def _update_task_next_run(self, task_id: int, next_run: str):
        """更新任务下次运行时间"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE scheduled_tasks SET next_run = ? WHERE id = ?", (next_run, task_id))
        conn.commit()
        conn.close()

    def _log_task_history(self, task_id: int, status: str, result: str, duration: float):
        """记录任务执行历史"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO task_history (task_id, status, result, executed_at, duration)
            VALUES (?, ?, ?, ?, ?)
        """, (task_id, status, result, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), duration))
        conn.commit()
        conn.close()

    def get_task_history(self, task_id: int, limit: int = 10) -> list[dict]:
        """获取任务执行历史"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT status, result, executed_at, duration
            FROM task_history
            WHERE task_id = ?
            ORDER BY executed_at DESC
            LIMIT ?
        """, (task_id, limit))
        rows = cursor.fetchall()
        conn.close()

        return [
            {"status": row[0], "result": row[1], "executed_at": row[2], "duration": row[3]}
            for row in rows
        ]

    def start(self):
        """启动调度器"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self._thread.start()

    def _run_scheduler(self):
        """运行调度器循环"""
        print("任务调度器已启动")
        while self._running:
            schedule.run_pending()
            time.sleep(1)

    def stop(self):
        """停止调度器"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        schedule.clear()


# 全局调度器实例
_scheduler_instance: Optional[TaskScheduler] = None


def get_scheduler() -> TaskScheduler:
    """获取调度器单例"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = TaskScheduler()
    return _scheduler_instance


def init_scheduler():
    """初始化并启动调度器"""
    scheduler = get_scheduler()
    scheduler.start()
    return scheduler
