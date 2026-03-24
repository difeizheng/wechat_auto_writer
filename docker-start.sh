#!/bin/bash
# Docker 快速启动脚本

set -e

echo "🚀 公众号文章自动生成系统 - Docker 启动"
echo "======================================="

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker"
    exit 1
fi

# 检查 Docker Compose 是否安装
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose 未安装，请先安装 Docker Compose"
    exit 1
fi

# 检查 .env 文件是否存在
if [ ! -f .env ]; then
    echo "⚠️  .env 文件不存在，正在从 .env.example 创建..."
    cp .env.example .env
    echo "✅ 已创建 .env 文件，请编辑该文件配置 API Key 等参数"
    echo ""
fi

# 创建必要的目录
mkdir -p data output

# 停止并清理旧容器
echo "🧹 清理旧容器..."
docker-compose down 2>/dev/null || true

# 构建镜像
echo "🔨 构建 Docker 镜像..."
docker-compose build

# 启动服务
echo "🚀 启动服务..."
docker-compose up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 5

# 检查服务状态
if docker-compose ps | grep -q "Up"; then
    echo ""
    echo "✅ 服务启动成功！"
    echo "======================================="
    echo "📍 访问地址：http://localhost:8601"
    echo "📊 查看日志：docker-compose logs -f"
    echo "🛑 停止服务：docker-compose down"
    echo "🔄 重启服务：docker-compose restart"
    echo "======================================="
else
    echo ""
    echo "❌ 服务启动失败，请检查日志："
    docker-compose logs
    exit 1
fi
