# 表现计划 v0.2

这是引擎无关的分镜协议。v0.1 的 `camera` 已删除；旧版本明确拒绝，现有示例已迁移。

顶层字段：schema_version、episode_id、fps、duration_frames、scene、cast、shots。
每个镜头：id、start_frame、end_frame、framing、performances。
每项表演：actor、action、emotion、line。line 可为空字符串。

`framing` 包含：
- `size`：wide 或 close。
- `subjects`：本集角色 ID 列表；close 恰好一个主体。

帧区间为 [start_frame, end_frame)，镜头连续、无重叠，完整覆盖 duration_frames。角色及词汇必须在目录中；后端还需另行检查是否支持。

当前表演在整个镜头中用一个关键姿势代表，同一演员每镜头最多一项。对白显示在镜头期间，尚无音频同步。尚未编码逐动作时序、视线目标、道具和连续姿态。该限制必须在添加精细动画前解决。

后端布局、程序图形、真实模型、材质、骨骼、摄影机参数都不属于本协议。后续应通过版本化后端配置和逻辑 ID 绑定扩展。
