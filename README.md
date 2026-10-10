# claymanclub

可复用的故事生产系统：同一组角色、故事和表演意图，可交给平面火柴人、2D 动画、3D 引擎或其他呈现后端。

**Unreal 是可选后端，不是核心依赖。** 当前可运行的是无第三方依赖的 Python 核心及 SVG 火柴人分镜后端；Unreal、配音、连续角色动画与视频导出尚未实现。

## 运行

需要 Python 3.10+，在仓库根目录运行：

```bash
python3 -m claymanclub validate examples/episode-001.json
python3 -m claymanclub render examples/episode-001.json --backend stickfigure --output outputs/preview
python3 -m unittest discover -s tests -v
```

用浏览器打开 `outputs/preview/index.html`，可播放、暂停和拖动查看 30 秒分镜。第一镜头演示二维平移、旋转与缩放，拖动按绝对帧重算镜头状态。当前每个镜头使用静态关键姿势，无声音、口型或连续身体运动；不是 MP4。输出目录须为新目录，防止覆盖现有结果。

测试全部使用 Python 标准库；若环境中有 Node，会额外执行生成播放器的控制与逐帧一致性测试（Node 不是运行依赖）。

## 抽象边界

1. **故事层**：角色、场景、对白、语义动作和情绪。
2. **表现计划**：整数帧时间线、画面范围、主体、相对摄像机轨迹；不含引擎资产路径或骨骼。
3. **呈现后端**：声明能力、验证绑定、将计划映射到具体表现并输出产物。

同一个 `look_down` 可以由火柴人低头姿势或 3D 骨骼动画表达。二者保留相同故事意图，不承诺视觉质量等价。不支持的能力明确报错，不静默忽略。

## 项目结构

- `claymanclub/backend.py`：PresentationBackend、Capabilities、RenderResult。
- `claymanclub/pipeline.py`：与后端无关的校验及调用流程。
- `claymanclub/validation.py`：v0.2–v0.5 故事协议校验。
- `claymanclub/camera.py`：摄像机轨迹校验、能力协商与确定性采样。
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

## 可选真实浏览器测试

Python 渲染器不需要 Node 或 Playwright。开发验证可使用：

```sh
npm ci
npx playwright install --with-deps chromium
npm run test:browser
```

Linux 建议安装 `fonts-noto-cjk` 以正确显示示例中文。测试直接打开生成的自包含 HTML，
覆盖实际 SVG 栅格化、原生播放/暂停/拖动/键盘定位、跨镜头向后定位、结束重播、
同帧截图一致性和窄屏布局。大部分测试冻结浏览器时钟以可重复执行，另有未模拟
`requestAnimationFrame` 的播放测试。截图和浏览器版本保存于 `outputs/browser-tests/run-*/`；
GitHub Actions 将该目录作为 `chromium-camera-evidence` 保存 30 天。

验证结果、已修复问题与关键帧截图见 [浏览器验证记录](docs/browser-validation/README.md)。

## 定时表演预览（v0.4）

```sh
python3 -m claymanclub render examples/timed-performances.json --backend stickfigure --output outputs/timed-preview
```

打开生成的 index.html：前 20 帧为停顿，20–119 帧显示第一句，120–169 帧切换同一角色的情绪和对白，170 帧起恢复默认姿势。拖动进度可反向重现相同画面，摄像机持续按绝对帧采样。
这是离散姿势切换，尚无连续动作或配音。旧版示例和播放行为继续保留。

## 视线与点头预览（v0.5）

```sh
python3 -m claymanclub render examples/gaze-and-nod.json --backend stickfigure --output outputs/gaze-preview
```

第一镜头的两个角色互相注视；bolt 在 20–120 帧完成一次平滑点头（70 帧最低），运镜继续执行，字幕固定。可以暂停或来回拖动观察相同帧。
只有 v0.5 的 nod 连续运动，旧版行为不变。当前是程序化头部动作，尚无完整肢体动画、音频或视频导出。
