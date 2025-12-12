# 🎨 Design-Agent 设计需求管理系统

一个基于 **AI 对话式交互** 的设计需求管理平台，通过智能 Agent 自动采集需求、推荐设计规范、管理任务流程。

---

## ✨ 功能特点

### 🤖 AI 需求助手
- **对话式需求采集**：自然语言描述需求，AI 自动提取关键信息
- **智能字段补全**：自动识别标题、类型、尺寸等必填项
- **设计规范推荐**：根据需求类型推荐尺寸、字体、配色等规范

### 📋 任务看板
- **五状态流转**：待接单 → 进行中 → 待验收 → 修改中 → 已完成
- **角色分权**：运营提需求，设计师接单，管理员全局查看
- **实时更新**：WebSocket 实时推送状态变更

### 📊 效能统计
- 设计师工作量统计
- 任务完成率分析
- 平均工时报表

---

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| **后端** | Python 3.11+ / FastAPI / SQLAlchemy / LangChain / LangGraph |
| **前端** | React 18 / TypeScript / Ant Design / Vite |
| **数据库** | SQLite（开发）/ PostgreSQL（生产）|
| **AI** | 通义千问 (Qwen) API |

---

## 🚀 快速开始

### 环境要求
- Python 3.11+
- Node.js 18+
- pnpm / npm

### 1. 克隆项目
```bash
git clone https://github.com/your-username/design-agent.git
cd design-agent
```

### 2. 配置 API Key
```bash
# 创建并编辑 backend/.env
echo "QWEN_API_KEY=your_api_key_here" > backend/.env
```

### 3. 启动后端
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

### 4. 启动前端
```bash
cd frontend
npm install
npm run dev
```

### 5. 访问系统
- **前端页面**: http://localhost:5173
- **API 文档**: http://localhost:8080/docs

---

## 👥 测试账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | 123456 | 管理员 |
| operator | 123456 | 运营 |
| designer | 123456 | 设计师 |

---

## 📁 项目结构

```
design-agent/
├── backend/
│   ├── app/
│   │   ├── api/          # API 路由
│   │   ├── agent/        # LangChain Agent
│   │   ├── core/         # 配置、数据库
│   │   └── models/       # SQLAlchemy 模型
│   ├── data/             # SQLite 数据文件
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/   # 公共组件
│   │   ├── pages/        # 页面
│   │   ├── services/     # API 服务
│   │   └── stores/       # 状态管理
│   └── package.json
└── README.md
```

---

## 📜 License

MIT License

---

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/)
- [LangChain](https://langchain.com/)
- [Ant Design](https://ant.design/)
- [通义千问](https://dashscope.aliyun.com/)
