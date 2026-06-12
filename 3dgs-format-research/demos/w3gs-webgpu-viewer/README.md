# W3GS Raw WebGPU Viewer Prototype A

这是一个同时支持 `raw-gaussian-v0`（SH0）和 `raw-gaussian-sh3-v0`（SH3）的 WebGPU 原型 viewer，用来验证：

```text
W3GS JSON -> chunk table -> raw payload -> WebGPU storage buffer -> canvas 可见画面
```

它不是完整的 3D Gaussian Splatting renderer。当前版本只把 splat 画成近似 billboard 圆片，用于验证 W3GS 数据读取、replacement LoD active-set、chunk 装载和 WebGPU 上传链路。

## 输入数据

默认读取统一 10K SH3 实验输出：

```text
../w3gs-from-ply/huce-zhanting-10k-parent-summary-sh3/
```

`scene.w3gs.json` 提供 `files.nodes`、`files.chunks` 和 `files.payloadBaseUri`。viewer 会先加载 manifest，再按 chunk 表中的 `uri`、`byteOffset`、`byteLength` 从 payload 文件中切出二进制片段。

也可用 query 参数打开 SH0 或其他兼容目录：

```text
http://127.0.0.1:8771/w3gs-webgpu-viewer/?sample=../w3gs-from-ply/huce-zhanting-10k-parent-summary/
```

## 运行方式

需要使用支持 WebGPU 的新版 Chrome 或 Edge。因为浏览器会限制 `fetch(file://...)`，请从 `demos` 目录启动静态服务：

```powershell
cd D:\Documents\Project\Python_project\LinJG\3dgs-format-research\demos
python -m http.server 8771
```

然后打开：

```text
http://127.0.0.1:8771/w3gs-webgpu-viewer/
```

自动 WebGPU smoke test：

```powershell
node demos/w3gs-webgpu-viewer/webgpu_smoke_test.mjs
```

runner 只使用 Node 标准库和本机 Chrome，启动隔离 profile、临时静态服务和 DevTools 连接。它在同一相机、同一 active splats 下分别抓取 full SH3 与 DC-only canvas，再补充 180° 视角截图；同时用固定合成系数运行 CPU reference 与 WGSL compute 对照。结束时关闭 Chrome 进程树和端口。测试服务器会把 payload 临时映射到无扩展名本地 URL，避免 IDM 等下载管理器接管 `.bin` fetch；不会修改正式 manifest、payload 或 profile contract。

## UI 功能

- `Load Startup`：加载 `scene.entry.startupSet` 指向的启动层 chunk。
- `Load Leaves`：加载所有叶节点的 layer chunk。
- `Load All`：加载 chunk table 中的所有 chunk。
- `Clear`：清空已加载 chunk 和 GPU buffer。
- `Point scale`：调整屏幕圆片大小。
- `Opacity`：调整显示用 alpha 增益。
- `Camera azimuth` / `Auto orbit`：绕场景 Y 轴移动相机；SH3 的观察方向颜色会随之更新。
- `Full SH3`：仅对 SH3 profile 有效；关闭时在相机和几何不变的情况下只计算 DC 系数，用于隔离高阶 SH 效应。

界面会显示 sample 名称、LoD 模式、codec/profile、SH degree、已加载/active chunk、active splat、GPU buffer 字节数、frame time 和 WebGPU 状态。

## Replacement Active Set

早期 viewer 使用 append 模型：chunk 一旦加载，就一直追加到 GPU buffer 中。这个模型能验证 payload 读取，但不符合 `parent-summary` LoD 的正式语义，因为 parent summary 和 child / leaf fine data 会同时贡献透明度。

当前 viewer 改为 replacement active-set 模型：

1. `loadedChunkIds` 记录已经下载并缓存在 CPU 侧的 chunk。
2. `activeChunkIds` 记录当前真正上传到 GPU buffer 的 chunk。
3. 每次加载后，从 `scene.entry.rootNode` 开始递归遍历 nodes。
4. 如果某个 node 的 child subtree 已有 active chunk，则该 node 自己的 parent summary 不再进入 active set。
5. 如果没有更细 child 可用，才使用该 node 已加载的 layer chunk。
6. 最后用 active chunk 重建一个连续 `Float32Array`，重新上传到 WebGPU storage buffer。

因此：

- `Load Startup` 通常只显示 root summary。
- `Load Leaves` 会让 leaf chunks 成为 active set，root / internal summary 不再参与当前 GPU buffer。
- `Load All` 虽然会下载所有 chunks，但 active set 会按 replacement 语义选择最细已加载节点，而不是把所有 chunks 全部画出来。

## Profile 分派与 Buffer Layout

viewer 依据 manifest 的 `chunk.codec`、codec 声明和 attribute schema 分派，不按目录名猜 profile。当前要求一个 sample 内使用同一种 raw profile。

### raw-gaussian-v0

payload 中每个 splat 使用 14 个 `float32`，共 56 bytes：

| offset | 字段 | 数量 |
| --- | --- | --- |
| 0 | position | 3 |
| 3 | scale | 3 |
| 6 | rotation | 4 |
| 10 | opacity | 1 |
| 11 | color | 3 |

WGSL shader 使用 `array<f32>` 读取 storage buffer，每个 splat 的起始位置为：

```wgsl
let splatIndex = vertexIndex / 6u;
let base = splatIndex * 14u;
```

每个 splat 发出 6 个顶点组成两个三角形。fragment shader 用 quad 的局部 UV 裁剪成圆形，并用 opacity 输出 alpha。

### raw-gaussian-sh3-v0

SH3 每个 splat 是 59 个 float32、236 bytes：共同几何字段占前 11 个 float，`shDc` 位于 11..13，`shRest` 位于 14..58。`shRest` 采用 Graphdeco channel-major 顺序：`R.c1..c15, G.c1..c15, B.c1..c15`。

WGSL 使用 `array<f32>`，stride 由 profile 注入 uniform，因此没有 storage struct padding 歧义。观察方向为：

```wgsl
normalize(position - cameraPosition)
```

shader 按 Graphdeco `eval_sh` 的标准实 SH degree 0..3 常量、顺序和正负号计算颜色，再执行 `max(0, 0.5 + evalSH)`。颜色 attachment / presentation 可能在最终输出阶段限制到显示范围，但 profile 不把逐 Gaussian 的上限 clamp 固化为 Graphdeco 语义。依据及精确 profile 见 `notes/format-cases/w3gs-0.1-payload-profiles.md`。

自动 smoke 还包含一个固定 59-float synthetic fixture：CPU 按同一 Graphdeco 公式计算期望 RGB，WGSL compute shader读取 `shDc + channel-major shRest` 后计算实际 RGB，二者最大绝对误差必须不超过 `1e-5`。该测试与同相机 full/DC 截图共同覆盖公式、系数索引和高阶 SH 分支；它仍不等于完整 Gaussian rasterizer 的像素等价测试。

## 当前渲染近似

当前 viewer 做的是简化轨道相机正交投影：

- 相机围绕场景 Y 轴旋转，固定轻微俯视角。
- 相机 right/up/forward 在 CPU 计算，通过 uniform 进入 WGSL。
- SH3 颜色使用相机到 Gaussian 的方向，因此旋转相机会改变方向相关颜色。
- `scale_0..2` 的最大值用于估计圆片半径。
- `rotation` 字段已读入 payload，但本 viewer 暂不用于椭圆方向。

这足以验证真实 W3GS sample 能进入 WebGPU 并形成可见分布，但不能代表真实 3DGS 椭圆高斯投影质量。

## 与 experiment-platform 的区别

`w3gs-experiment-platform` 是调度和 LoD 策略实验平台，主要用 2D AABB 展示 chunk/node/layer 的装载行为。

本 viewer 是渲染链路原型，重点验证真实 `raw-gaussian-v0` payload 可以被浏览器读取、切片、按 replacement 语义选择 active set、合并、上传到 WebGPU storage buffer，并由 WGSL shader 直接消费。

## 限制与 TODO

- 当前没有严格透明排序，alpha 混合结果只适合原型观察。
- 当前没有真实 3D 相机、透视投影、协方差投影或椭圆高斯积分。
- 当前未使用 rotation 字段。
- SH3 颜色计算已经真实进入 WebGPU shader，但 billboard 仍不是完整椭圆 Gaussian rasterization。
- 当前 replacement 是简化 active-set 重建，没有做 GPU buffer suballocation 或细粒度释放。
- 当前没有做视锥、屏幕误差或相机距离驱动的局部 refinement；按钮只是手动加载集合。
- 后续应支持按 node/layer 增量释放 GPU buffer、视锥筛选、depth/importance 排序，以及接入团队已有 WebGPU renderer 的 buffer/manifest 接口。
