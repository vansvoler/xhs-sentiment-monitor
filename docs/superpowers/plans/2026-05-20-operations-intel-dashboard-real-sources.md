# Operations Intel Dashboard Real Sources Plan

## Goal

在第一阶段纵向切片已经稳定的前提下，把 `UCAS / 海外大学官网 / 考试局 / 签证政策 / 媒体公众号` 从 fixture 数据升级为真实抓取链路，并补上摘要生成流程。

当前产品主线已经收窄为官方情报工作台。小红书保留现有采集与 legacy 页面，后续作为单独模块处理，不再进入 `/dashboard` 的 overview 或来源导航。

## Scope

- UCAS official feed collector
- University site collector
- Exam board official collector
- Visa policy official collector
- WeChat media collector
- Summary generation pipeline

## Explicitly Out of Scope

- 首页信息架构重做
- 选题池联动
- 内容待办系统
- 高优先级算法排序页

## Entry Condition

只有当下面 3 条成立时再进入第二阶段：

1. `/dashboard` 的来源导航和概览结构已经稳定
2. 统一 `intel_items` contract 不再大改
3. 前端已经能在 fixture + 官方来源真实数据下稳定工作
