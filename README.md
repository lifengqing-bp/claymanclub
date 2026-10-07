# claymanclub

可复用的故事生产系统：同一组角色、故事和表演意图，可交给平面火柴人、2D 动画、3D 引擎或其他呈现后端。

**Unreal 是可选后端，不是核心依赖。** 当前可运行的是无第三方依赖的 Python 核心及 SVG 火柴人分镜后端；Unreal、配音、连续动画与视频导出尚未实现。

## 运行

需要 Python 3.10+，在仓库根目录运行：

```bash
python3 -m claymanclub validate examples/episode-001.json
python3 -m claymanclub render examples/episode-001.json --backend stickfigure --output outputs/preview
python3 -m unittest discover -s tests -v
```

用浏览器打开 `outputs/preview/index.html`，可播放、暂停和拖动查看 30 秒分镜。当前每个镜头使用静态关键姿势，无声音、口型或连续身体运动；不是 MP4。输出目录须为新目录，防止覆盖现有结果。

## 抽象边界

1. **故事层**：角色、场景、对白、语义动作和情绪。
2. **表现计划**：整数帧时间线、画面范围、主体；不含引擎资产路径或骨骼。
3. **呈现后端**：声明能力、验证绑定、将计划映射到具体表现并输出产物。

同一个 `look_down` 可以由火柴人低头姿势或 3D 骨骼动画表达。二者保留相同故事意图，不承诺视觉质量等价。不支持的能力明确报错，不静默忽略。

## 项目结构

- `claymanclub/backend.py`：PresentationBackend、Capabilities、RenderResult。
- `claymanclub/pipeline.py`：与后端无关的校验及调用流程。
- `claymanclub/validation.py`：v0.2 故事协议校验。
- `claymanclub/backends/stickfigure.py`：SVG 与 HTML 分镜后端。
- `examples/`：后端无关的能力词汇和示例故事。
- `docs/`：架构、协议、路线图及制作规则。
- `tests/`：替换后端、拒绝不支持能力、重复输出等契约验证。

## 下一步

先用火柴人验证剧情节奏，增加逐项表演时间和连续动作，再实现第二个真实呈现后端。两角色、单场景、三集 30–60 秒短剧是首次内容验证范围。

GitHub：https://github.com/lifengqing-bp/claymanclub

```bash
git clone https://github.com/lifengqing-bp/claymanclub.git
cd claymanclub
```

项目许可证见 `LICENSE`。第三方资产需要单独记录来源与授权。
