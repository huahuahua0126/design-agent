#!/bin/bash

# Design-Agent 本地开发启动脚本
# 使用方法: ./start.sh

echo "🚀 启动 Design-Agent 本地开发环境..."
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 创建数据目录
mkdir -p "$SCRIPT_DIR/backend/data"
mkdir -p "$SCRIPT_DIR/backend/data/uploads"
mkdir -p "$SCRIPT_DIR/backend/data/chroma"

# 检查 .env 文件
if [ ! -f "$SCRIPT_DIR/backend/.env" ]; then
    echo "⚠️  未找到 .env 文件，正在创建..."
    cat > "$SCRIPT_DIR/backend/.env" << EOF
QWEN_API_KEY=your_api_key_here
EOF
    echo "📝 请编辑 backend/.env 填入您的 Qwen API Key"
fi

# 启动后端
echo "📦 启动后端服务..."
cd "$SCRIPT_DIR/backend"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "   创建 Python 虚拟环境..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt

echo "   后端启动于 http://localhost:8080"
echo "   API 文档: http://localhost:8080/docs"
uvicorn app.main:app --reload --port 8080 &
BACKEND_PID=$!

# 等待后端启动
sleep 3

# 启动前端
echo ""
echo "🎨 启动前端服务..."
cd "$SCRIPT_DIR/frontend"
npm install --silent
echo "   前端启动于 http://localhost:5173"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ 服务已启动！"
echo "   后端 API: http://localhost:8080/docs"
echo "   前端页面: http://localhost:5173"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 捕获 Ctrl+C 信号
trap "echo ''; echo '正在停止服务...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT

# 等待
wait
