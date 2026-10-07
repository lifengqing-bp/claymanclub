# StoryStage

可反复拍摄的虚拟摄影棚：复用角色、场景、表演和镜头，以 3D 故事线持续生产短视频。

**状态：项目初始化。** 当前包含设计文档、能力目录、分镜示例及离线校验器；尚未接入 Unreal、TTS 或视频渲染，也不包含可运行的 Unreal 工程。StoryStage 为暂定项目名。

## 第一阶段目标

两个风格化角色、一个室内场景，制作三集 30–60 秒短剧。先人工打磨第一集，再验证第二、第三集的资产复用和人工工时下降。

## 原则

- 内容质量先于批量生产。
- 编剧只能使用已实现的场景、演员、动作和镜头能力。
- AI 提出剧情与分镜，确定性的执行器组织拍摄；人审核低清预览。
- 每个镜头独立追踪，支持局部修改与重拍。
- 固定时间基准、输入版本和资产版本；关键模拟需要烘焙或缓存。
- 不把 planned 能力当成已实现能力。

## 本地运行

需要 Python 3.10+，无需第三方依赖。在仓库根目录运行：

```bash
python3 scripts/validate_episode.py examples/episode-001.json
```

校验器只检查分镜结构、时间覆盖和目录引用；通过不代表已可渲染。目录中所有资源目前都是 planned 占位项，接入引擎前须完成真实资产绑定。

## 项目结构

- `docs/architecture.md`：生产流程、职责与引擎边界。
- `docs/roadmap.md`：里程碑与验收条件。
- `docs/shot-contract.md`：初版分镜格式及限制。
- `docs/production.md`：质量检查、成本指标及资产管理。
- `examples/catalog.json`：计划支持的摄影棚能力。
- `examples/episode-001.json`：30 秒双机器人短剧草稿。
- `scripts/validate_episode.py`：离线校验入口。

## 下一步

人工在 Unreal 中搭建一个摄影棚，完成一个双人对话镜头；记录引擎版本、角色绑定、动作和机位。不要先建设通用 Agent 平台。

## Git 与远程仓库

仓库使用 `main`，项目包保留 Git 历史。尚未配置远程地址。
创建空的远程仓库后，在本地执行：

```bash
git remote add origin <YOUR_REPOSITORY_URL>
git push -u origin main
```

当前未选择开源许可证；引入第三方素材前记录来源及适用授权。
