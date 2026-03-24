# 公众号文章自动生成系统 - Makefile
# 简化常用 Docker 和开发操作

.PHONY: help build start stop restart logs clean dev

# 默认目标
help:
	@echo "公众号文章自动生成系统 - 可用命令"
	@echo "================================"
	@echo "  make build      - 构建 Docker 镜像"
	@echo "  make start      - 启动服务"
	@echo "  make stop       - 停止服务"
	@echo "  make restart    - 重启服务"
	@echo "  make logs       - 查看日志"
	@echo "  make clean      - 清理容器和镜像"
	@echo "  make dev        - 本地开发模式启动"
	@echo "  make shell      - 进入容器 Shell"
	@echo "  make backup     - 备份数据"
	@echo "  make restore    - 恢复数据"

# 构建 Docker 镜像
build:
	docker-compose build

# 启动服务
start:
	@mkdir -p data output
	docker-compose up -d
	@echo "服务已启动：http://localhost:8601"

# 停止服务
stop:
	docker-compose down

# 重启服务
restart:
	docker-compose restart

# 查看日志
logs:
	docker-compose logs -f

# 清理容器和镜像
clean:
	docker-compose down -v
	docker rmi wechat-auto-writer:latest 2>/dev/null || true
	@echo "清理完成"

# 本地开发模式（不使用 Docker）
dev:
	@mkdir -p data output
	streamlit run app/main.py --server.port=8601 --server.address=0.0.0.0

# 进入容器 Shell
shell:
	docker-compose exec wechat-writer bash

# 备份数据
backup:
	@mkdir -p backups
	tar -czf backups/data-$$(date +%Y%m%d_%H%M%S).tar.gz data/
	@echo "数据备份完成"

# 恢复数据（需要指定备份文件）
restore:
	@if [ -z "$(file)" ]; then \
		echo "请指定备份文件：make restore file=backups/data-YYYYMMDD_HHMMSS.tar.gz"; \
	else \
		tar -xzf $(file) -C ./; \
		echo "数据恢复完成"; \
	fi
