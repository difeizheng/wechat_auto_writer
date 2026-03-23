"""
定时任务调度模块
支持定时生成文章、定时发布等任务
使用 SQLAlchemy 统一数据库
"""
import json
import threading
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional, Callable
from pathlib import Path
import schedule

from app.models import get_session, ScheduledTask, TaskHistory


class TaskScheduler:
    """任务调度器"""

    def __init__(self):
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        self._callbacks: dict[str, Callable] = {}
        self._load_tasks()

    def _load_tasks(self):
        """加载已启用的任务并注册到调度器"""
        session = get_session()
        try:
            tasks = session.query(ScheduledTask).filter(ScheduledTask.enabled == 1).all()

            # 清除所有已注册的 job
            schedule.clear()

            # 重新注册启用的任务
            for task in tasks:
                self._schedule_task(task.id, task.cron_expression)
        finally:
            session.close()

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
                return schedule.every(1).minutes.do(
                    self._run_task, task_id=task_id, callback=callback, params=parameters
                )
            elif minute == "*/5" and hour == "*":
                return schedule.every(5).minutes.do(
                    self._run_task, task_id=task_id, callback=callback, params=parameters
                )
            elif minute == "*/15" and hour == "*":
                return schedule.every(15).minutes.do(
                    self._run_task, task_id=task_id, callback=callback, params=parameters
                )
            elif minute == "0" and hour == "*":
                return schedule.every().hour.do(
                    self._run_task, task_id=task_id, callback=callback, params=parameters
                )
            elif minute != "*" and minute.isdigit() and hour == "*":
                return schedule.every(minute).minutes.do(
                    self._run_task, task_id=task_id, callback=callback, params=parameters
                )
            elif minute.isdigit() and hour.isdigit():
                if minute == "0":
                    return schedule.every().day.at(f"{hour}:00").do(
                        self._run_task, task_id=task_id, callback=callback, params=parameters
                    )
                else:
                    return schedule.every().day.at(f"{hour}:{minute.zfill(2)}").do(
                        self._run_task, task_id=task_id, callback=callback, params=parameters
                    )
            elif weekday != "*":
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
        file_path = None

        try:
            print(f"执行任务 {task_id}...")
            # 回调函数现在会返回 file_path
            result = callback(**params)
            if isinstance(result, dict) and "file_path" in result:
                file_path = result["file_path"]
                result = result.get("message", "success")
        except Exception as e:
            status = "failed"
            result = str(e)
            print(f"任务 {task_id} 执行失败：{e}")

        duration = time.time() - start_time

        # 记录执行历史（包含 file_path）
        self._log_task_history(task_id, status, result, duration, file_path)

        # 更新上次运行时间
        self._update_task_last_run(task_id)

        # 发送邮件通知（如果配置了）
        if params.get("email_notification") or params.get("send_email"):
            self._send_email_notification(task_id, status, result, duration)

    def register_callback(self, task_type: str, callback: Callable):
        """注册任务类型的回调函数"""
        self._callbacks[task_type] = callback

    def create_task(self, name: str, task_type: str, cron_expression: str, parameters: dict) -> int:
        """创建新任务"""
        session = get_session()
        try:
            now = datetime.now()
            task = ScheduledTask(
                name=name,
                task_type=task_type,
                cron_expression=cron_expression,
                parameters=parameters,
                enabled=1,
                created_at=now,
                updated_at=now
            )
            session.add(task)
            session.commit()
            task_id = task.id

            # 重新加载任务
            self._schedule_task(task_id, cron_expression)

            return task_id
        finally:
            session.close()

    def get_task(self, task_id: int) -> Optional[ScheduledTask]:
        """获取任务详情"""
        session = get_session()
        try:
            return session.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
        finally:
            session.close()

    def list_tasks(self) -> list[ScheduledTask]:
        """获取所有任务列表"""
        session = get_session()
        try:
            tasks = session.query(ScheduledTask).order_by(ScheduledTask.created_at.desc()).all()
            return tasks
        finally:
            session.close()

    def update_task(self, task_id: int, **kwargs):
        """更新任务"""
        session = get_session()
        try:
            task = session.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
            if not task:
                return

            allowed_fields = ["name", "cron_expression", "parameters", "enabled"]

            for field, value in kwargs.items():
                if field in allowed_fields:
                    if field == "parameters":
                        value = value  # 已经是 dict
                    elif field == "enabled":
                        value = 1 if value else 0
                    setattr(task, field, value)

            task.updated_at = datetime.now()
            session.commit()

            # 重新加载任务
            self._load_tasks()
        finally:
            session.close()

    def delete_task(self, task_id: int):
        """删除任务"""
        session = get_session()
        try:
            task = session.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
            if task:
                session.delete(task)
                session.commit()

            # 重新加载任务
            self._load_tasks()
        finally:
            session.close()

    def toggle_task(self, task_id: int):
        """启用/禁用任务"""
        task = self.get_task(task_id)
        if task:
            self.update_task(task_id, enabled=not task.enabled)

    def _update_task_last_run(self, task_id: int):
        """更新任务上次运行时间"""
        session = get_session()
        try:
            task = session.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
            if task:
                task.last_run = datetime.now()
                session.commit()
        finally:
            session.close()

    def _update_task_next_run(self, task_id: int, next_run: str):
        """更新任务下次运行时间"""
        session = get_session()
        try:
            task = session.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
            if task:
                task.next_run = datetime.strptime(next_run, "%Y-%m-%d %H:%M:%S")
                session.commit()
        finally:
            session.close()

    def _log_task_history(self, task_id: int, status: str, result: str, duration: float, file_path: str = None):
        """记录任务执行历史"""
        session = get_session()
        try:
            history = TaskHistory(
                task_id=task_id,
                status=status,
                result=result,
                executed_at=datetime.now(),
                duration=duration,
                file_path=file_path
            )
            session.add(history)
            session.commit()
        finally:
            session.close()

    def get_task_history(self, task_id: int = None, limit: int = 10) -> list[dict]:
        """获取任务执行历史"""
        session = get_session()
        try:
            if task_id is None:
                # 获取所有任务的历史记录
                histories = session.query(TaskHistory).order_by(TaskHistory.executed_at.desc()).limit(limit).all()
                return [
                    {
                        "task_id": h.task_id,
                        "status": h.status,
                        "result": h.result,
                        "executed_at": h.executed_at.strftime("%Y-%m-%d %H:%M:%S"),
                        "duration": h.duration,
                        "file_path": h.file_path
                    }
                    for h in histories
                ]
            else:
                # 获取指定任务的历史记录
                histories = session.query(TaskHistory).filter(
                    TaskHistory.task_id == task_id
                ).order_by(TaskHistory.executed_at.desc()).limit(limit).all()
                return [
                    {
                        "status": h.status,
                        "result": h.result,
                        "executed_at": h.executed_at.strftime("%Y-%m-%d %H:%M:%S"),
                        "duration": h.duration,
                        "file_path": h.file_path
                    }
                    for h in histories
                ]
        finally:
            session.close()

    def get_latest_history(self, limit: int = 10) -> list[dict]:
        """获取最新的执行记录（包含任务名称）"""
        session = get_session()
        try:
            histories = session.query(TaskHistory).order_by(TaskHistory.executed_at.desc()).limit(limit).all()
            result = []
            for h in histories:
                task_name = ""
                if h.task_id:
                    task = session.query(ScheduledTask).filter(ScheduledTask.id == h.task_id).first()
                    if task:
                        task_name = task.name
                result.append({
                    "task_id": h.task_id,
                    "task_name": task_name,
                    "status": h.status,
                    "result": h.result,
                    "executed_at": h.executed_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "duration": h.duration,
                    "file_path": h.file_path
                })
            return result
        finally:
            session.close()

    def _send_email_notification(self, task_id: int, status: str, result: str, duration: float):
        """发送邮件通知"""
        import os
        import json
        from pathlib import Path

        # 读取邮件配置
        config_file = Path("data/email_config.json")
        if not config_file.exists():
            print("邮件配置不存在，跳过邮件发送")
            return

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                email_config = json.load(f)
        except Exception as e:
            print(f"读取邮件配置失败：{e}")
            return

        # 获取必填配置
        smtp_server = email_config.get("smtp_server")
        smtp_port = email_config.get("smtp_port", 587)
        sender_email = email_config.get("sender_email")
        sender_password = email_config.get("sender_password")
        recipient_emails = email_config.get("recipient_emails", [])
        task_name = email_config.get("task_name", "定时任务")

        if not all([smtp_server, sender_email, sender_password, recipient_emails]):
            print("邮件配置不完整，跳过邮件发送")
            return

        # 构建邮件内容
        subject = f"[{task_name}] 执行{'成功' if status == 'success' else '失败'} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        status_icon = "✅" if status == "success" else "❌"
        body = f"""
<html>
<body>
    <h2>{status_icon} 定时任务执行通知</h2>
    <p><strong>任务名称</strong>: {task_name}</p>
    <p><strong>执行状态</strong>: {'成功' if status == 'success' else '失败'}</p>
    <p><strong>执行时间</strong>: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <p><strong>执行耗时</strong>: {duration:.2f}秒</p>
    <p><strong>执行结果</strong>: {result}</p>
    <hr>
    <p style="color: #666; font-size: 12px;">此邮件由系统自动发送，请勿回复。</p>
</body>
</html>
"""

        try:
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = ', '.join(recipient_emails)
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'html', 'utf-8'))

            # 发送邮件
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_emails, msg.as_string())
            server.quit()

            print(f"邮件通知发送成功：{recipient_emails}")
        except Exception as e:
            print(f"发送邮件失败：{e}")

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
