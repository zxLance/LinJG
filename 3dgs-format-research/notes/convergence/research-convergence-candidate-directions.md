# 收敛阶段：候选创新方向

最后更新：2026-06-08

本文档用于把两类输入合并成候选研究方向：

- 前沿论文缺口：`../literature/frontier-paper-format-gaps.md`
- 现有格式缺口：`../comparisons/existing-format-gap-analysis.md`

当前目标已经不是单纯比较已有格式，而是：

```text
设计一种新的、面向 Web 流式渲染的 3DGS 数据格式。
```

## 1. 两条证据线的共同结论

### 1.1 前沿论文给出的信号

前沿论文显示，3DGS 数据格式相关问题正在从“能不能压缩”转向：

- 能不能渐进传输。
- 能不能随机访问局部空间块。
- 能不能同时支持 LoD、视角自适应和带宽自适应。
- 能不能把 payload codec 和空间/层级索引解耦。
- 能不能直接服务浏览器端解码、GPU 上传和显存预算。

不建议把本文做成：

- 新压缩算法论文。
- 新 WebGPU renderer / FPS 竞赛论文。

更合适的定位是：

```text
面向 Web 流式渲染的数据格式设计论文。
```

### 1.2 现有四种格式给出的信号

四种主格式各有强项，但也各有边界：

| 格式 | 最值得吸收 | 主要不足 |
| --- | --- | --- |
| Spark RAD | 极低成本连续数组 LoD 引用。 | LoD、payload codec 和 Spark runtime 绑定较紧。 |
| XGRIDS LCC2 | 每个空间 Node 可索引本层级 3DGS 数据。 | 空间索引清楚，但 payload schema 和替换策略不够显式。 |
| SOG Streaming | Web 压缩交付、chunk 区间和 manifest。 | 与 PlayCanvas runtime 调度绑定较深。 |
| Cesium 3D Tiles 3DGS | 标准化 HLOD 容器和 glTF/SPZ 语义链。 | 通用 HLOD/SSE 不够表达 3DGS 专属视觉误差。 |

共同缺口可以概括为：

```text
已有格式要么高效但封闭，
要么标准但偏重，
要么 Web 友好但 runtime 绑定明显，
还缺一种专门面向 Web 流式 3DGS 的清晰分层格式设计。
```

## 2. 候选方向 A：空间块与渐进层正交的 Web 流式容器

一句话：

```text
设计一种把 spatial node/tile 与 base/refinement layer 分开的 3DGS streaming container。
```

### 2.1 核心思想

现有格式里，空间分块、LoD 层级和 payload 引用经常耦合在一起。候选方向 A 的重点是把它们拆开：

```text
Scene Manifest
  -> Spatial Node Tree
  -> Per-node Base Layer
  -> Per-node Refinement Layers
  -> Chunk Table
  -> Codec Payload
```

一个空间节点不只指向“一段数据”，而是指向：

- 可快速首屏显示的 base layer。
- 多个可追加或替换的 refinement layers。
- 每层对应的 payload chunk。
- 父子节点之间的替换/叠加关系。

### 2.2 新颖性来源

它吸收：

- LCC2 的“Node 自带本层级数据”。
- SOG Streaming 的 chunk/manifest。
- Cesium 3D Tiles 的 HLOD 思想。
- PCGS / progressive streaming 论文里的渐进传输需求。

但它更强调：

```text
空间层级和渐进层是两个正交维度。
```

即：

- 空间上：远处加载大节点，近处加载小节点。
- 精度上：同一个节点也可以先加载粗层，再加载细层。

### 2.3 优点

- 论文价值强：直接回应前沿论文和工程格式的共同缺口。
- 原型可做：可以用 JSON manifest + 二进制 chunk 做最小 demo。
- 不需要挑战压缩率 SOTA。
- 能清楚解释为什么 RAD/LCC2/SOG/3D Tiles 都只解决了问题的一部分。

### 2.4 风险

- 需要定义清楚 base/refinement 的生成方式。
- 需要决定 refinement 是“增量叠加”还是“替换父层”。
- 如果不做实验，容易停留在概念设计。

### 2.5 最小验证

可以做一个最小原型：

```text
scene.json
nodes.json
chunks.bin
```

支持：

- root/base 首屏加载。
- 近处节点 refinement 加载。
- 浏览器按相机位置选择节点。
- 记录请求数、首屏字节数、可见 splat 数。

## 3. 候选方向 B：Codec-independent Gaussian Chunk Profile

一句话：

```text
设计一种不绑定 SPZ、SOG、raw 或未来 MPEG GSC 的 Gaussian chunk envelope。
```

### 3.1 核心思想

当前格式常把空间索引、payload 编码和 runtime 解码路径绑在一起。候选方向 B 试图定义一个统一的 chunk profile：

```text
Chunk Header
  codec = raw | spz | sog | glb | future-mpeg-gsc
  attribute_schema
  quantization_info
  bounding_volume
  splat_count
  dependency
  gpu_layout_hint
  byte_range
Payload
```

格式本身不规定必须使用哪种压缩算法，而是规定：

- chunk 如何被索引。
- chunk 如何声明属性。
- chunk 如何声明依赖和 LoD 层级。
- chunk 如何被浏览器调度和上传。

### 3.2 新颖性来源

它吸收：

- SPZ 的压缩 payload 价值。
- SOG 的 Web-friendly chunk 化。
- glTF / KHR_gaussian_splatting 的属性 schema 意识。
- Cesium 3D Tiles 的容器与 payload 分离思想。

### 3.3 优点

- 生态兼容性强。
- 容易论证未来可扩展到 MPEG GSC、OpenUSD 或 glTF。
- 适合写成“profile / envelope / interchange layer”。

### 3.4 风险

- 如果只做 envelope，可能被认为工程规范多于研究创新。
- 需要和现有 glTF / SPZ / 3D Tiles 的边界讲清楚。
- 不如方向 A 那样直接体现 LoD/Streaming 创新。

### 3.5 最小验证

可以用同一个 manifest 同时引用两类 payload：

- raw splat chunk。
- SPZ 或 SOG chunk。

证明浏览器加载逻辑不依赖具体 codec。

## 4. 候选方向 C：Gaussian-specific LoD Contract 与 Web 调度元数据

一句话：

```text
为 3DGS 定义专门的 LoD 合同和 Web runtime hints，而不是沿用通用点云/mesh HLOD 指标。
```

### 4.1 核心思想

3DGS 的 LoD 不只是“点少一点”。它还涉及：

- 透明混合误差。
- 排序风险。
- Gaussian 尺度变化。
- 密度连续性。
- 父子层替换时的视觉闪烁。
- SH / opacity / scale 的降阶策略。

候选方向 C 试图让格式显式描述这些信息：

```text
lod_error
opacity_error
density_change
sort_risk
screen_size_threshold
decode_cost
gpu_upload_cost
memory_budget_class
mobile_profile
```

浏览器 runtime 不再只看 bounding box 和距离，而是结合这些 hint 决定：

- 先加载谁。
- 是否展开子节点。
- 是否加载 refinement。
- 是否合并 range request。
- 是否释放远处节点。

### 4.2 新颖性来源

它吸收：

- Cesium 3D Tiles 的 screen space error 思想。
- WebSplatter 对浏览器渲染约束的提示。
- L3GS / 3DGStreaming 的 FoV、带宽和异质性调度需求。
- 3DGS 特有的透明排序和 Gaussian 属性误差问题。

### 4.3 优点

- 研究问题很鲜明：通用 HLOD 指标不足以表达 3DGS。
- 与 Web 调度联系强。
- 可以作为方向 A 的关键子模块。

### 4.4 风险

- 需要定义可计算的指标，否则容易变成“字段堆叠”。
- 可能需要更多实验来证明这些 hint 真的有用。
- 单独作为完整论文方向略窄，但作为新格式的核心创新点很合适。

### 4.5 最小验证

可以实现两个调度策略对比：

- 只按距离 / 屏幕大小调度。
- 按 Gaussian-specific hint 调度。

比较：

- 首屏可见质量。
- refinement 抖动。
- 请求优先级是否更合理。
- 显存是否更稳定。

## 5. 三个方向的比较

| 方向 | 论文价值 | 可实现性 | 新颖性 | 风险 | 建议 |
| --- | --- | --- | --- | --- | --- |
| A. 空间块与渐进层正交容器 | 高 | 中高 | 高 | 需要做原型 | 最推荐作为主方向 |
| B. codec-independent chunk profile | 中高 | 高 | 中 | 容易像工程规范 | 适合作为 A 的支撑层 |
| C. Gaussian-specific LoD contract | 高 | 中 | 高 | 指标需实验支撑 | 适合作为 A 的核心创新点 |

## 6. 推荐收敛方案

建议不要在 A、B、C 中只选一个孤立方向，而是形成一个主方向 + 两个支撑创新点：

```text
主方向：
  A. 空间块与渐进层正交的 Web 流式 3DGS 容器

支撑创新点：
  B. codec-independent Gaussian chunk profile
  C. Gaussian-specific LoD contract / Web scheduling hints
```

这样论文贡献可以写成：

1. 提出一种将空间索引、渐进层和 Gaussian payload 解耦的 Web 3DGS streaming format。
2. 设计 codec-independent chunk profile，使 raw / SPZ / SOG / future codec 可以作为可插拔 payload。
3. 定义 Gaussian-specific LoD contract 和 Web scheduling hints，用于指导浏览器按需加载、细化和显存管理。
4. 实现最小原型，验证该格式支持首屏 base layer、局部 refinement 和视角相关加载。

## 7. 当前建议

当前最可行的选择是：

```text
选择方向 A 作为论文主线，
把方向 B 和 C 合并为格式设计中的两个核心模块。
```

这个选择的理由：

- 它不需要和压缩算法论文拼 SOTA。
- 它不需要和 WebGPU renderer 拼 FPS。
- 它能自然吸收四种主格式的优点。
- 它能回应前沿论文暴露的 streaming/progressive/random-access 缺口。
- 它可以通过一个较小 demo 验证。

如果接受这个方向，下一步应该开始写：

```text
proposed-format-design.md
```

重点定义：

- 格式目标。
- 文件组成。
- manifest schema。
- node tree。
- base/refinement layers。
- chunk table。
- payload profile。
- LoD contract。
- browser loading protocol。
- 最小转换和渲染 demo。
