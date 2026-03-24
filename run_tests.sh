#!/bin/bash
# 测试运行脚本

set -e

echo "================================"
echo "公众号文章自动生成系统 - 测试"
echo "================================"
echo ""

# 检查是否安装了依赖
if ! python -c "import pytest" 2>/dev/null; then
    echo "正在安装测试依赖..."
    pip install -r requirements.txt
fi

# 创建测试数据目录
mkdir -p data output tests

# 运行测试
echo "运行测试..."
echo ""

if [ "$1" == "--coverage" ] || [ "$1" == "-c" ]; then
    # 带覆盖率测试
    pytest --cov=app --cov-report=html --cov-report=term-missing -v
    echo ""
    echo "覆盖率报告已生成：htmlcov/index.html"
else
    # 普通测试
    pytest -v
fi

echo ""
echo "================================"
echo "测试完成!"
echo "================================"
