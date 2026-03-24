# 多阶段构建 - 减小镜像大小
FROM python:3.11-slim as builder

WORKDIR /app

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖到指定目录
RUN pip install --no-cache-dir --user -r requirements.txt

# 运行阶段
FROM python:3.11-slim

WORKDIR /app

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 复制用户安装的 Python 包
COPY --from=builder /root/.local /root/.local

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p data output && \
    chmod -R 755 data output

# 添加用户（安全最佳实践）
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# 环境变量
ENV PATH=/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    STREAMLIT_SERVER_PORT=8601 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8601/_stcore/health || exit 1

# 暴露端口
EXPOSE 8601

# 启动命令
ENTRYPOINT ["streamlit", "run", "app/main.py"]
CMD ["--server.port=8601", "--server.address=0.0.0.0", "--server.headless=true"]
