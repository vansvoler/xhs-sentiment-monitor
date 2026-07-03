# Frontend Workspace

这个前端目前同时承载两套视图：

- `/dashboard`：新的官方情报工作台，主线来源为 UCAS、海外大学官网、考试局、签证政策和媒体观察
- `/dashboard/legacy`：旧的小红书舆情面板

## Commands

开发启动：

```bash
bash scripts/dev.sh
```

Lint：

```bash
bash scripts/lint.sh
```

生产构建：

```bash
npm run build
```

## Key Files

- `src/app/dashboard/page.tsx`：官方情报工作台入口
- `src/app/dashboard/legacy/page.tsx`：旧 dashboard 入口
- `src/components/operations-dashboard/`：新工作台组件
- `src/components/dashboard/legacy-xhs-dashboard.tsx`：旧小红书舆情视图
