# 小红书舆情监控系统

实时监控小红书笔记和评论的情感倾向、热点话题和竞品动态。

## 技术栈

- **后端**: Python + FastAPI + MongoDB
- **前端**: Next.js 16 + React 19 + Tailwind CSS 4
- **AI分析**: 百度Senta (ERNIE模型)
- **实时通信**: WebSocket

## 项目结构

```
xhs-sentiment-monitor/
├── backend/                    # Python后端
│   ├── src/
│   │   ├── api/               # API路由
│   │   ├── collectors/         # 数据采集
│   │   ├── analyzers/          # 情感分析
│   │   ├── models/            # 数据模型
│   │   ├── services/          # 业务逻辑
│   │   ├── db/                # 数据库
│   │   └── websocket/         # WebSocket服务
│   ├── scripts/              # 启停脚本
│   └── main.py               # FastAPI入口
├── frontend/                 # Next.js前端（待开发）
└── docs/                     # 文档
```

## 快速开始

### 环境要求

- Python 3.11+
- MongoDB 4.4+
- Node.js 18+ (前端)

### 后端启动

```bash
cd backend

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 复制环境变量配置
cp .env.example .env

# 编辑.env配置
vim .env

# 启动服务
./scripts/dev.sh
```

访问 http://localhost:8000/docs 查看API文档

### 前端启动（待开发）

```bash
cd frontend
npm install
npm run dev
```

## API接口

### 笔记相关
- `GET /api/notes/` - 获取笔记列表
- `GET /api/notes/{note_id}` - 获取笔记详情
- `GET /api/notes/stats/summary` - 获取笔记统计

### 评论相关
- `GET /api/comments/` - 获取评论列表
- `GET /api/comments/{comment_id}` - 获取评论详情
- `GET /api/comments/note/{note_id}` - 获取笔记评论

### 情感分析
- `POST /api/sentiment/analyze` - 批量情感分析
- `GET /api/sentiment/stats` - 情感统计

### 趋势分析
- `GET /api/trends/daily` - 今日趋势
- `GET /api/trends/series` - 趋势序列
- `GET /api/trends/hot-topics` - 热门话题

### 竞品分析
- `GET /api/competitors/compare` - 竞品对比
- `GET /api/competitors/{name}` - 竞品详情
- `GET /api/competitors/{name}/trends` - 竞品趋势

## 配置说明

详细配置说明见 `docs/` 目录下的文档。

## 开发指南

### 添加新的数据采集任务

编辑 `src/collectors/scheduler.py` 添加新的定时任务。

### 添加新的情感分析模型

编辑 `src/analyzers/senta_service.py` 扩展模型支持。

### 添加新的API端点

在 `src/api/` 目录下创建新的路由文件。

## 注意事项

- 第三方API可能不稳定，需做好容错处理
- 遵守平台规则，注意数据隐私保护
- 大量数据采集时注意性能优化

## 许可证

MIT
