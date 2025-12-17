# PostgreSQL + pgvector 部署指南

## 1. 安装 PostgreSQL

### macOS (Homebrew)
```bash
brew install postgresql@15
brew services start postgresql@15
```

### 创建数据库
```bash
createdb design_agent
```

## 2. 安装 pgvector 扩展

### macOS (Homebrew)
```bash
brew install pgvector
```

### 在数据库中启用扩展
```bash
psql design_agent
```

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## 3. 配置环境变量

在 `backend/.env` 中添加：
```bash
# PostgreSQL + pgvector 配置
PGVECTOR_CONNECTION_STRING=postgresql://postgres:postgres@localhost:5432/design_agent
```

如果你的 PostgreSQL 有密码，修改为：
```bash
PGVECTOR_CONNECTION_STRING=postgresql://你的用户名:你的密码@localhost:5432/design_agent
```

## 4. 安装 Python 依赖

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

## 5. 验证安装

启动服务后，查看日志，应该看到：
```
Loaded XX document chunks into pgvector database
```

## 6. 查看向量数据

```bash
psql design_agent
```

```sql
-- 查看集合
SELECT * FROM langchain_pg_collection;

-- 查看向量数据
SELECT id, document, cmetadata FROM langchain_pg_embedding LIMIT 5;
```

## 故障排查

### 问题1: PostgreSQL 未启动
```bash
brew services start postgresql@15
```

### 问题2: pgvector 扩展未安装
```bash
brew install pgvector
psql design_agent -c "CREATE EXTENSION vector;"
```

### 问题3: 连接被拒绝
检查 PostgreSQL 是否在运行：
```bash
pg_isready
```

## 性能优化

### 创建向量索引（可选）
```sql
-- 为向量字段创建 HNSW 索引
CREATE INDEX ON langchain_pg_embedding USING hnsw (embedding vector_cosine_ops);
```

### 调整 PostgreSQL 配置（可选）
编辑 `/opt/homebrew/var/postgresql@15/postgresql.conf`：
```
shared_buffers = 256MB
work_mem = 16MB
maintenance_work_mem = 128MB
```

重启服务：
```bash
brew services restart postgresql@15
```
