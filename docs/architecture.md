# 架构

## 工作流

故事草案 → 能力校验 → 分镜 → 配音与时长对齐 → 表演编排 → 低清预览 → 人工审核 → 正式渲染 → 剪辑与质检。

当前只实现分镜草稿的离线校验。其他组件均待开发。

## 职责与边界

| 组件 | 输入 | 输出 | 状态 |
| --- | --- | --- | --- |
| 故事规划 | 人设、栏目规则、能力目录 | 剧情和对白 | planned |
| 分镜校验 | JSON 分镜、能力目录 | 错误或通过 | 初版可用 |
| 配音 | 台词、角色音色 | 音频及实际时长 | planned |
| 时间编排 | 分镜、实际音频时长 | 以帧为单位的表演时间线 | planned |
| Unreal 适配器 | 已验证时间线、资产绑定 | Sequencer 序列 | planned |
| 渲染调度 | 序列、预设、版本信息 | 镜头文件、状态和日志 | planned |
| 后期 | 镜头、声音、字幕 | 竖屏成片 | planned |

分镜与引擎分离：分镜引用稳定的逻辑 ID，适配器将 ID 映射到真实 Unreal 资产。模型不能任意创建资产路径或执行编辑器代码。

## 可重复拍摄

- 统一使用整数帧，区间为 [start_frame, end_frame)。
- 摄影机切换不应重置角色表演；正式适配器使用共享表演时间线。
- 每个镜头保存起始状态、角色姿态、视线和道具状态，必要时带预滚帧。
- 固定随机种子并不能保证物理模拟完全确定；重要模拟需要缓存或烘焙。
- 每次拍摄记录剧本、声音、资产、引擎、适配器和渲染预设的版本。
- 按镜头重跑；任务状态拟为 queued/running/succeeded/failed/cancelled。
- 渲染并发、队列、重试有上限。付费配音请求不自动重试。

## 技术选择

优先验证 Unreal 的 Sequencer 与 Movie Render Queue。引擎版本在首个可运行摄影棚落地时锁定，当前不声称兼容任何具体版本。暂不开发自主 NPC、自由物理交互或多 Agent 编排。

官方资料：
- https://dev.epicgames.com/documentation/en-us/unreal-engine/cinematics-and-movie-making-in-unreal-engine
- https://dev.epicgames.com/documentation/en-us/unreal-engine/movie-render-pipeline-in-unreal-engine
- https://dev.epicgames.com/documentation/en-us/metahuman/audio-driven-animation
