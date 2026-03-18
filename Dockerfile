FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 创建数据目录
RUN mkdir -p data output

# 暴露端口
EXPOSE 8601

# 启动命令
CMD ["streamlit", "run", "app/main.py", "--server.port=8601", "--server.address=0.0.0.0"]
