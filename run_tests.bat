@echo off
chcp 65001 >nul
echo =======================================
echo 公众号文章自动生成系统 - 测试
echo =======================================
echo.

REM 检查是否安装了依赖
python -c "import pytest" 2>nul
if errorlevel 1 (
    echo [提示] 正在安装测试依赖...
    pip install -r requirements.txt
)

REM 创建测试数据目录
if not exist data mkdir data
if not exist output mkdir output
if not exist tests mkdir tests

REM 运行测试
echo 运行测试...
echo.

if "%1"=="--coverage" (
    pytest --cov=app --cov-report=html --cov-report=term -v
    echo.
    echo 覆盖率报告已生成：htmlcov\index.html
) else if "%1"=="-c" (
    pytest --cov=app --cov-report=html --cov-report=term -v
    echo.
    echo 覆盖率报告已生成：htmlcov\index.html
) else (
    pytest -v
)

echo.
echo =======================================
echo 测试完成!
echo =======================================
pause
