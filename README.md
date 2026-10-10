# claymanclub

可复用的故事生产系统：同一组角色、故事和表演意图，可交给平面火柴人、2D 动画、3D 引擎或其他呈现后端。

**Unreal 是可选后端，不是核心依赖。** 当前可运行的是无第三方依赖的 Python 核心及 SVG 火柴人分镜后端；已支持定时程序化角色动画；Unreal 和配音尚未实现。

## 运行

需要 Python 3.10+，在仓库根目录运行：

```bash
python3 -m claymanclub validate examples/episode-001.json
python3 -m claymanclub render examples/episode-001.json --backend stickfigure --output outputs/preview
python3 -m unittest discover -s tests -v
```

用浏览器打开 `outputs/preview/index.html`，可播放、暂停和拖动查看 30 秒分镜。第一镜头演示二维平移、旋转与缩放，拖动按绝对帧重算镜头状态。episode-001 保留 v0.3 静态角色语义；连续动作请看下方 v0.5/v0.6 示例。无声音或口型。输出目录须为新目录，防止覆盖现有结果。

测试全部使用 Python 标准库；若环境中有 Node，会额外执行生成播放器的控制与逐帧一致性测试（Node 不是运行依赖）。

## 抽象边界

1. **故事层**：角色、场景、对白、语义动作和情绪。
2. **表现计划**：整数帧时间线、画面范围、主体、相对摄像机轨迹；不含引擎资产路径或骨骼。
3. **呈现后端**：声明能力、验证绑定、将计划映射到具体表现并输出产物。

同一个 `look_down` 可以由火柴人低头姿势或 3D 骨骼动画表达。二者保留相同故事意图，不承诺视觉质量等价。不支持的能力明确报错，不静默忽略。

## 项目结构

- `claymanclub/backend.py`：PresentationBackend、Capabilities、RenderResult。
- `claymanclub/pipeline.py`：与后端无关的校验及调用流程。
- `claymanclub/validation.py`：v0.2–v0.6 故事协议校验。
- `claymanclub/camera.py`：摄像机轨迹校验、能力协商与确定性采样。
- `claymanclub/backends/stickfigure.py`：SVG 与 HTML 分镜后端。
- `examples/`：后端无关的能力词汇和示例故事。
- `docs/`：架构、协议、路线图及制作规则。
- `tests/`：替换后端、拒绝不支持能力、重复输出等契约验证。

## 下一步

先用火柴人验证剧情节奏，使用现有逐项表演、连续动作与位移制作短剧，再实现第二个真实呈现后端。两角色、单场景、三集 30–60 秒短剧是首次内容验证范围。

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
v0.5 支持程序化 nod/wave/bow，旧版行为不变。尚无完整骨骼动画、音频或视频导出。

## 挥手与鞠躬预览（v0.5）

```sh
python3 -m claymanclub render examples/gestures.json --backend stickfigure --output outputs/gestures-preview
```

第一镜头 bolt 挥手、pixel 鞠躬；20 帧开始，120 帧回正。镜头持续运动，字幕保持固定。暂停、反向拖动和重播都按当前帧重算关节状态。
动作仅使用同一套 performance 时间字段；不引入逐帧图片、额外动画时钟或新运行依赖。


## 行走与真实视频 demo（v0.6）

```sh
python3 -m claymanclub render examples/stage-motion.json --backend stickfigure --output outputs/stage-preview
python3 scripts/export_video.py examples/stage-motion.json --output outputs/claymanclub-demo.mp4
```

18 秒、540×960、30 fps：靠近 → 点头/挥手 → 挥手/鞠躬，三个镜头都有运镜。示例使用英文字幕，无配音。
视频导出是可选 Linux 工具，需要系统 `librsvg-2`、Cairo 和支持 libx264 的 FFmpeg；逐帧调用真实 SVG 后端，再栅格化编码，不录制鼠标或播放器控件。不同 SVG 栅格化器的字体与抗锯齿可有差异，动作采样规则一致。中文示例导出还需系统安装相应 CJK 字体。

位移轨迹与动作独立组合，按绝对帧采样；尚无脚步锁定、碰撞、空间深度或骨骼混合。

## 第一支叙事样片：《再来一条 / One More Take》

```sh
python3 -m claymanclub render examples/one-more-take.json --backend stickfigure --output outputs/one-more-take
python3 scripts/export_video.py examples/one-more-take.json --output outputs/one-more-take.mp4
```

36 秒、六个镜头：到场 → 约定口令 → 做错动作 → 反应近景 → 再次做错 → 收尾。
复用 walk、wave、nod、bow 和 look_down；没有为这支片子增加专用动作或协议字段。
火柴人后端 0.6.1 为 walk 增加交替抬脚和屈膝，保留首末中立、两周期和绝对帧语义；仍不提供脚部锁定。
英文字幕、无音频。分镜与验收记录见 [样片说明](docs/one-more-take.md)。


## 肘、膝关节（火柴人后端 0.7）

双臂、双腿均使用两段刚性线段，新增两个肘关节和两个膝关节。挥手由肩抬臂、肘带动前臂摆动；行走时双肘弯曲、双膝交替屈伸。圆点标示关节位置。

复用 `examples/stage-motion.json` 和上面的导出命令即可观看；故事协议没有增加后端专用关节坐标。骨段不拉伸，所有姿态依旧按绝对帧确定。

## 线框空间与道具（火柴人后端 0.8）

```sh
python3 -m claymanclub render examples/wireframe-scene.json --backend stickfigure --output outputs/wireframe-scene
python3 scripts/export_video.py examples/wireframe-scene.json --output outputs/wireframe-scene.mp4
```

`wireframe_lounge` 通过墙角、疏密地面线、窗框、桌椅、书架和盆栽表现空间。道具使用细线，角色使用较粗高亮线；头部遮住背后的布景线，避免线条穿过表情。
场景和道具一起运镜，字幕与 UI 固定。旧 `robot_lounge` 保留原画面，新场景仅需更换已有 `scene` ID。
这是二维线框布景：尚无真实三维投影、深度排序、碰撞、坐下或拿取道具动作。
