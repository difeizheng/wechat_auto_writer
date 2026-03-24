@echo off
chcp 65001 >nul
echo =======================================
echo 公众号文章自动生成系统 - Docker 启动
echo =======================================

REM 检查 Docker 是否安装
docker --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Docker 未安装，请先安装 Docker Desktop
    pause
    exit /b 1
)

REM 检查 Docker Compose 是否安装
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Docker Compose 未安装
    pause
    exit /b 1
)

REM 检查 .env 文件是否存在
if not exist .env (
    echo [提示] .env 文件不存在，正在从 .env.example 创建...
    copy .env.example .env
    echo [成功] 已创建 .env 文件，请编辑该文件配置 API Key 等参数
    echo.
)

REM 创建必要的目录
if not exist data mkdir data
if not exist output mkdir output

REM 停止并清理旧容器
echo [清理] 停止旧容器...
docker-compose down >nul 2>&1

REM 构建镜像
echo [构建] 正在构建 Docker 镜像...
docker-compose build

REM 启动服务
echo [启动] 正在启动服务...
docker-compose up -d

REM 等待服务启动
echo [等待] 等待服务启动...
timeout /t 5 /nobreak >nul

REM 检查服务状态
docker-compose ps | findstr "Up" >nul 2>&1
if not errorlevel 1 (
    echo.
    echo =======================================
    echo [成功] 服务启动成功！
    echo =======================================
    echo 访问地址：http://localhost:8601
    echo 查看日志：docker-compose logs -f
    echo 停止服务：docker-compose down
    echo 重启服务：docker-compose restart
    echo =======================================
) else (
    echo.
    echo [错误] 服务启动失败，请检查日志：
    docker-compose logs
    pause
    exit /b 1
)

pause
