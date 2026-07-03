# 添加运营情报信源设计

## 背景

当前运营情报系统已经支持配置化官网信源：后端通过
`backend/config/intel_sources.json` 读取信源，采集器自动识别
`feed`、`rss`、`json_feed`、`listing`、`html_listing` 等抓取方案。项目也已有
`probe_intel_source` 探测器，可以从 URL 推断可用 feed 或静态 HTML 列表选择器。

缺口是：新增信源仍需要手动跑脚本、复制 JSON、重启或等待采集，不适合品牌经理从前端日常维护。

## 目标

在前端运营 dashboard 增加“添加信源”能力：

1. 用户输入目标网站 URL。
2. 后端自动探测抓取方案。
3. 前端展示推荐配置预览。
4. 用户可编辑信源名称、分类、分组。
5. 用户确认后，后端把信源写入配置文件。

本次不立即抓取，保存成功后进入下一轮同步，避免错误配置直接产生误导性数据。

## 用户流程

入口放在 dashboard 主区域顶部，使用 `Plus` 图标按钮。

流程分两步：

1. **探测**
   - 输入 URL。
   - 选择分类，默认 `university_site`。
   - 输入分组，默认 `自定义来源`。
   - 点击“探测”。

2. **确认保存**
   - 展示探测状态、样本数量、抓取方案、推荐 URL。
   - 允许编辑信源名称、分类、分组。
   - 只有 `status=success` 时允许保存。
   - 保存成功后关闭弹窗并提示已加入下一轮同步。

## 后端设计

新增两个 API：

- `POST /api/intel/sources/probe`
  - 请求：`url`、`source_type`、`source_name`、`source_group`
  - 行为：调用 `probe_intel_source`
  - 响应：`status`、`message`、`sample_count`、`recommended_source`

- `POST /api/intel/sources`
  - 请求：一个完整 `IntelSource`
  - 行为：校验配置可采集、校验 `source_id` 不重复、追加到
    `backend/config/intel_sources.json`
  - 响应：保存后的 `source`

配置写入放到新服务 `backend/src/services/intel_source_config.py`：

- `append_intel_source(path, source)`
- `source_exists(sources, source_id)`
- `atomic_write_sources(path, sources)`

写入采用临时文件替换，避免 JSON 写坏。

## 前端设计

新增组件：

- `frontend/src/components/operations-dashboard/add-source-dialog.tsx`

新增类型：

- `IntelSourceConfig`
- `ProbeIntelSourceRequest`
- `ProbeIntelSourceResponse`
- `CreateIntelSourceRequest`
- `CreateIntelSourceResponse`

新增 API helper：

- `probeIntelSource`
- `createIntelSource`

组件状态：

- `idle`：输入 URL
- `probing`：探测中
- `preview`：展示推荐配置
- `saving`：保存中
- `saved`：保存完成
- `error`：展示错误消息

## 错误处理

- URL 缺失或格式错误：前端阻止提交，后端返回 422。
- 探测被拦截：展示 `blocked`，不可保存。
- 探测不支持：展示 `unsupported`，不可保存。
- `source_id` 重复：后端返回 409，前端提示已存在。
- 配置文件写入失败：后端返回 500，前端提示保存失败。

## 测试

后端使用 TDD：

- API 探测成功返回推荐配置。
- 保存成功会追加配置文件。
- 重复 `source_id` 返回 409。
- 无效抓取配置返回 422。

前端当前没有测试脚本；本次使用 TypeScript 类型约束、`npm run lint`、浏览器手动验证。

## 非目标

- 不做信源删除、启停、重测。
- 不做立即抓取。
- 不做浏览器渲染型采集 fallback。
- 不改现有调度器周期。
