# 3DGS 前沿论文中的数据格式缺口

最后更新：2026-06-08

## 0. 本文判断口径

这份笔记不按“论文摘要”来写，而按一个问题来筛选：

```text
这些工作是否暴露了现有 3DGS 数据格式无法自然承载的数据组织需求？
```

如果一篇论文只是提出更好的训练正则、更快的 rasterizer、更强的剪枝策略，它当然重要，但不一定适合作为“新数据格式论文”的直接创新点。对我们更有价值的是那些把 3DGS 从“一个高斯数组”推向以下结构的工作：

- 可随机访问的空间块、tile、node、chunk。
- 可渐进传输的 layer、prefix、incremental bitstream。
- 可按视角 / 带宽 / 显存预算调度的 LoD 元数据。
- 可被浏览器低成本解码、排序、上传 GPU 的 buffer layout。
- 可接入 glTF、SPZ、3D Tiles、OpenUSD、MPEG GSC 等生态的互操作边界。

一句话判断：

```text
前沿论文已经证明 3DGS 需要的不只是更小的压缩包，
而是“空间索引 + 渐进层 + 编码 payload + Web/GPU 运行时契约 + 标准桥接”的组合格式。
```

## 1. 哪些贡献本质上需要新的数据组织方式

最能支撑“新格式设计”的论文 / 项目有四类。

### 1.1 渐进压缩类：需要 bitstream 层级，而不是单一压缩文件

代表：PCGS、L3GS、Matryoshka GS / CLoD-GS。

这类工作的问题意识是：压缩率高并不等于可流式。传统压缩 3DGS 可能必须完整下载、完整解码、完整上传后才能显示；而 Web / XR / 移动端需要“先看粗结果，后补细节”。这要求格式显式表达：

- 第 0 层最小可渲染集合。
- 后续 refinement layer 或 residual stream。
- 每层的质量收益、字节大小、依赖关系。
- 已加载层如何与 GPU buffer 中的旧数据合并、替换或追加。

这不是单纯算法问题，因为没有层级目录、偏移表和依赖图，progressive bitstream 很难通过 HTTP range、CDN chunk 或浏览器 cache 稳定落地。

### 1.2 LoD / 大场景类：需要空间层级，而不是全局高斯数组

代表：Octree-GS、CityGaussian、VastGaussian、A LoD of Gaussians。

这类工作说明：大场景 3DGS 的瓶颈不是“场景里有多少高斯”这个静态数字，而是当前相机下哪些高斯需要驻留、排序和渲染。格式必须表达：

- bounding volume / spatial key / Morton order / octree node。
- node 内的高斯范围或 payload 引用。
- geometric error、screen-space error 或等价质量度量。
- 父子层级的 refine 语义：替换、叠加、淡入淡出、预算裁剪。
- 跨块边界一致性和 seam 处理相关的元数据。

如果格式仍然只有 `N` 个 splat 的扁平数组，LoD 只能在运行时另建索引，生成成本、加载路径和互操作都会变差。

### 1.3 自适应 streaming 类：需要“多码率 + FoV + QoE”调度元数据

代表：3DGStreaming、L3GS。

这类工作把 3DGS 拉近了视频流媒体问题：不同视角、不同网络、不同设备，不应加载同一份质量。格式应能表达：

- 同一空间块的多码率 / 多质量版本。
- FoV 内外的优先级。
- 码率、字节数、预计解码成本、GPU 内存成本。
- 调度器可读的 QoE / distortion / latency trade-off。

这说明新格式不应只服务离线存储，还应给 runtime scheduler 提供足够可计算的描述。

### 1.4 标准化和 Web 工程类：需要分层互操作，而不是单一“万能格式”

代表：PlayCanvas SOG / SplatTransform、SPZ、KHR_gaussian_splatting、Cesium 3D Tiles Gaussian Splat、MPEG GSC、OpenUSD。

这些项目共同暗示：未来生态不会收敛到一个单文件格式。更可能是：

```text
场景索引 / HLOD 容器
  + Gaussian payload schema
  + 压缩 codec
  + Web runtime layout
  + DCC / GIS / 标准化桥接
```

因此我们的新格式如果想有论文价值，最好不要声称“替代 glTF / SPZ / 3D Tiles”，而是明确填补它们之间的缺层：面向 Web 流式渲染的中间组织层。

## 2. 前沿论文暴露出的主要矛盾

| 矛盾 | 论文 / 项目暴露方式 | 格式层面的含义 |
| --- | --- | --- |
| 高压缩率 vs 随机访问 | 熵编码、码本、图像 / 视频压缩通常喜欢长连续数据流；streaming 需要只解码当前视角附近的小块。 | payload 必须分 chunk，并为每个 chunk 保存独立解码边界、偏移表和最小依赖。 |
| 渐进传输 vs GPU buffer 稳定性 | progressive 方法不断新增 splat 或细化属性；浏览器端频繁重建 buffer 会卡顿。 | 格式需要定义 append / patch / replace 策略，以及 GPU-friendly alignment。 |
| 离散 LoD vs 视觉 popping / 存储重复 | 多份 LoD 模型容易重复存储，切换时跳变；连续 LoD 又常需要训练时特殊排序或参数。 | 格式可支持 prefix order、importance range、cross-fade metadata，而不是只存 LOD0/LOD1 文件。 |
| 全局压缩 vs 空间调度 | 单个 SPZ / SOG / PLY 可以很小，但不等于可以按视角局部加载。 | 需要把 codec payload 放进空间 node 或 layer chunk，而不是让 codec 吞掉整个场景。 |
| 标准互操作 vs runtime 性能 | glTF 基础扩展强调通用字段和 fallback；Web runtime 更关心 Morton order、纹理化属性、GPU 上传和排序。 | 需要“标准语义层”和“运行时物理布局层”分离，并提供映射。 |
| 浏览器解码便利 vs 编码效率 | WebP / image codec 易部署但随机访问粒度和数值保真有限；Zstd / entropy model 压缩强但 JS/WASM 解码成本高。 | 格式应定义 codec profile 和能力协商，而不是把某一种 codec 写死。 |
| 大场景 out-of-core vs 透明排序 | 大场景只加载可见块，但透明 splat 需要排序和正确混合；跨块排序会影响画质。 | node 元数据需要包含 depth range、opacity / importance 统计、排序辅助信息或 renderer hint。 |

## 3. 5-8 个最重要论文 / 项目

### 3.1 PCGS: Progressive Compression of 3D Gaussian Splatting, 2025

链接：[arXiv:2503.08511](https://arxiv.org/abs/2503.08511)

核心贡献：PCGS 明确批评现有压缩方法缺少 progressivity，导致 on-demand 应用无法高效利用已下载 bitstream。它同时控制 Gaussian / anchor 数量和属性量化质量，用 progressive masking、progressive quantization 和跨层概率预测形成渐进码流。

暴露的数据格式缺口：PCGS 把“压缩包”变成“可分阶段使用的码流”。这意味着格式必须记录每个阶段的增量范围、依赖关系、概率模型状态、量化步长和可渲染条件。传统 PLY / SPZ / SOG 单体 payload 不天然表达“第 k 层已经足够渲染、k+1 层是 refinement”。

对我们格式设计的启发：

- 设计 `base layer + refinement layers`，每层可独立寻址。
- 每层记录 `byteRange`、`splatRange`、`attributeMask`、`quantization`、`dependsOn`。
- 把“数量渐进”和“属性质量渐进”分成两个正交维度，避免只做几份重复 LoD 文件。

### 3.2 L3GS: Layered 3D Gaussian Splats for Efficient 3D Scene Delivery, 2025

链接：[arXiv:2504.05517](https://arxiv.org/abs/2504.05517)，[MobiCom PDF](https://jiasi.engin.umich.edu/wp-content/uploads/sites/81/2025/05/L3GS_mobicom_25.pdf)

核心贡献：L3GS 面向 3D scene delivery，把场景组织成 layered 3DGS，并研究下载调度：何时下载哪些 splats，以提升视觉质量并降低延迟。论文还强调它可与其他压缩 3DGS 表示结合。

暴露的数据格式缺口：L3GS 的贡献已经不只是“怎么训练一个更小模型”，而是“如何把场景切成可调度的层”。这要求数据格式中有 layer id、优先级、每层收益、下载成本和与视角路径相关的调度信息。

对我们格式设计的启发：

- 新格式可把 `layer` 作为一等概念，而非文件名约定。
- 支持 scheduler 读取 `bytes / expectedQualityGain / decodeCost / gpuCost`。
- 支持同一空间 node 内多层渐进加载，避免只有全局 LoD。

### 3.3 3DGStreaming: Spatial-Heterogeneity-Aware 3-D Gaussian Splatting Compression and Streaming, 2025

链接：[HKUST Research Portal](https://researchportal.hkust.edu.hk/en/publications/3dgstreaming-spatial-heterogeneity-aware-3-d-gaussian-splatting-c/)，[DOI](https://doi.org/10.1109/JIOT.2025.3590142)

核心贡献：3DGStreaming 把 3DGS streaming 明确建模为 QoE 问题，包含空间异质性感知分区、两步渐进场景生成、多码率 3DGS 场景，以及基于 FoV 的 bitrate adaptation。

暴露的数据格式缺口：如果一个 3DGS 场景有多个空间分区、每个分区有多个码率版本，格式就必须像 DASH/HLS 那样提供 manifest，而不是只提供一个资产文件。当前常见 3DGS 格式通常缺少“同一 tile 的 bitrate ladder”和“FoV 优先级”。

对我们格式设计的启发：

- 设计 `variant` 或 `rateSet`：同一 node 的多个质量 / 码率 payload。
- manifest 中记录 FoV 外低码率、FoV 内高码率的选择条件。
- 引入 QoE 相关字段：预计 latency、distortion proxy、字节大小、decode time。

### 3.4 Octree-GS: Towards Consistent Real-time Rendering with LOD-Structured 3D Gaussians, 2024

链接：[arXiv:2403.17898](https://arxiv.org/abs/2403.17898)

核心贡献：Octree-GS 用 octree 组织多分辨率 anchor / Gaussian，并根据视角动态选择合适 LoD，以稳定大复杂场景的渲染性能。

暴露的数据格式缺口：Octree-GS 说明 LoD 是 3DGS 表示本身的一部分，而不是 viewer 临时做的后处理。若格式不存 octree node、anchor 层级、父子关系和选择度量，跨工具传输后 LoD 结构会丢失。

对我们格式设计的启发：

- manifest 采用空间树结构，node 记录 bounding box、level、children、payload。
- 每个 node 可绑定一个或多个 Gaussian payload chunk。
- LoD selection metric 应作为格式字段，而不是写死在某个 runtime 中。

### 3.5 A LoD of Gaussians: Unified Training and Rendering for Ultra-Large Scale Reconstruction with External Memory, 2025

链接：[arXiv:2507.01110](https://arxiv.org/abs/2507.01110)

核心贡献：这篇工作反对简单分块：分块会带来边界伪影、训练尺度不一致和非结构化场景困难。它把完整场景放在外存 / CPU memory 中，训练 LoD 表示，并用 Gaussian hierarchies + Sequential Point Trees 做 view-dependent LoD selection 和动态 streaming。

暴露的数据格式缺口：真正的大场景 Web 渲染不是“下载很多小文件”就够了，还需要 out-of-core 数据结构、缓存策略、时间一致的 view scheduling。格式如果只存 tile，不存层级顺序、缓存粒度和访问序列提示，很难支持这种 runtime。

对我们格式设计的启发：

- 支持 out-of-core 友好的 `page` 概念，page 小于 tile，可单独缓存和淘汰。
- 记录 temporal coherence hint，例如相邻 page、父子 page、预取优先级。
- 避免只采用刚性空间切块，可支持 hierarchy / point-tree 混合索引。

### 3.6 WebSplatter: Enabling Cross-Device Efficient Gaussian Splatting in Web Browsers via WebGPU, 2026

链接：[arXiv:2602.03207](https://arxiv.org/abs/2602.03207)

核心贡献：WebSplatter 是面向浏览器异构 WebGPU 环境的端到端渲染管线，提出 wait-free hierarchical radix sort 以绕开 WebGPU 缺少全局 atomics 的限制，并用 opacity-aware culling 降低 overdraw 和峰值内存。

暴露的数据格式缺口：WebSplatter 主要是渲染论文，但它强烈反向塑形格式：浏览器中排序、culling、buffer 更新和显存峰值比离线解码更重要。格式若只追求压缩率，可能导致 Web 端必须做昂贵重排、重解码和重上传。

对我们格式设计的启发：

- chunk payload 应尽量 GPU-ready：对齐、连续、字段分离或交错方式明确。
- manifest 可携带 opacity / size / depth range 统计，帮助 runtime culling。
- 格式应区分 `decode layout` 和 `render layout`，并允许预排序或 Morton order。

### 3.7 PlayCanvas SOG / SplatTransform Streaming LOD, 2025-2026

链接：[SOG Format Spec](https://developer.playcanvas.com/user-manual/gaussian-splatting/formats/sog/)，[Splat formats](https://developer.playcanvas.com/user-manual/gaussian-splatting/formats/)，[Open-sourcing SOG blog](https://blog.playcanvas.com/playcanvas-open-sources-sog-format-for-gaussian-splatting/)，[splat-transform](https://github.com/playcanvas/splat-transform)

核心贡献：SOG 是 Web delivery 导向的 3DGS 压缩容器：用 `meta.json` 引用多个 lossless WebP 属性图，属性按像素 co-located；官方文档定位为 runtime / delivery 格式，约 15-20x 小于 PLY。SplatTransform 还提供 LoD 输出和 chunked streaming workflow。

暴露的数据格式缺口：SOG 很好地解决了 Web codec 可用性和 GPU-ready Morton order，但它也暴露一个边界：图像化属性压缩适合整包或较大 chunk 交付，若要更精细随机访问、FoV 多码率、标准互操作和跨 runtime 调度，还需要更明确的 scene-level manifest。

对我们格式设计的启发：

- 可以借鉴“属性分图 + metadata + Web 原生解码”的工程务实性。
- 但新格式应把 SOG 视为可插拔 payload codec，而不是唯一容器。
- 在 SOG chunk 外层补充空间 node、quality layer、range index 和标准映射。

### 3.8 KHR_gaussian_splatting + SPZ + Cesium 3D Tiles Gaussian Splat, 2026

链接：[KHR_gaussian_splatting spec](https://github.com/KhronosGroup/glTF/blob/main/extensions/2.0/Khronos/KHR_gaussian_splatting/README.md)，[Khronos press release](https://www.khronos.org/news/press/gltf-gaussian-splatting-press-release?khr-2026-000=khr-2026-001)，[SPZ GitHub](https://github.com/nianticlabs/spz)，[Cesium 3DGS with HLOD](https://cesium.com/blog/2026/04/27/3d-gaussian-splats-lod/)

核心贡献：KHR_gaussian_splatting 把 3DGS 作为 glTF mesh primitive 扩展，定义 position、rotation、scale、opacity、SH 等基础语义，并刻意保持可扩展。SPZ 提供开放压缩 payload。Cesium 则用 3D Tiles 作为空间索引和 HLOD 容器，用 glTF / SPZ 作为 tile payload，使城市级到细节级 3DGS 可以在地理空间中流式加载。

暴露的数据格式缺口：这个组合是目前最接近产业标准的答案，但它是“分层拼装”而不是单一格式：3D Tiles 负责空间调度，glTF 负责资产语义，SPZ 负责压缩。它仍然没有完全定义 Web 端渐进属性细化、chunk 内多层 bitstream、GPU 上传策略、FoV 多码率和非 GIS 场景的轻量 manifest。

对我们格式设计的启发：

- 新格式应兼容 glTF/SPZ/3D Tiles，而不是与其对立。
- 论文创新可以定位为“Web 端 progressive Gaussian chunk layer”，向上可嵌入 3D Tiles，向下可承载 SPZ/SOG/raw payload。
- 标准字段应保留 extension / profile 机制，避免被某个压缩算法锁死。

## 4. 值得提及但不宜作为主创新点的方向

### 4.1 纯剪枝、纯量化、纯码本压缩

LightGaussian、Compact3D / CompGS、HAC、EAGLES 等工作对压缩背景很重要，但如果我们只复现“更少高斯 + 更低 bit + 更好 entropy coding”，论文会落入算法压缩赛道。除非我们把它们转化成“chunk 内 codec profile”和“可随机访问的码本 / 熵模型边界”，否则不适合作为格式论文主线。

### 4.2 纯 WebGPU 排序 / rasterizer 加速

WebSplatter、FlashGS、GauRast 等说明 runtime 约束很强，但直接做更快排序或 rasterizer 是图形算法论文，不是格式论文。我们应提炼其格式启发：buffer layout、预排序、culling hint、GPU upload granularity。

### 4.3 纯训练阶段的大场景重建

CityGaussian、VastGaussian 的 partition / fusion 对格式有启发，但训练流程本身不是格式创新。我们能吸收的是 block-wise LoD、跨块一致性和大场景索引，而不是把论文目标改成更好重建。

### 4.4 纯标准包装

只把 PLY 转成 glTF、SPZ 或 3D Tiles，不足以成为新格式论文。标准兼容很必要，但创新点应落在它们还没覆盖的 progressive / Web streaming / GPU-ready chunk 组织。

## 5. 适合作为新 3DGS 数据格式的创新方向

按“可行性 + 论文价值”排序如下。

### 5.1 第一优先：空间块与渐进层正交的 Web 流式容器

核心设计：

```text
Scene manifest
  -> spatial nodes / tiles
      -> base layer
      -> refinement layers
          -> codec payload chunks
```

为什么最有价值：它直接回应 PCGS、L3GS、3DGStreaming、Octree-GS 和 Cesium 3D Tiles 暴露的共同缺口：现有格式通常只有压缩 payload 或空间 HLOD，但缺少“空间随机访问 + 属性渐进细化”统一表达。

可验证实验：

- 首屏只加载 root/base layer。
- 视角靠近时加载 node refinement。
- 比较 PLY/SPZ/SOG 单体加载、简单 3D Tiles、我们格式的首屏字节、请求数、可见质量和 GPU 内存。

### 5.2 第二优先：codec-independent Gaussian chunk profile

核心设计：

```text
每个 chunk 有统一 envelope：
  bbox / splatCount / byteRange / codec / attributeMask / quantization / dependency / gpuLayout

payload 可选：
  raw binary / SPZ / SOG image set / future MPEG GSC / custom progressive stream
```

为什么有论文价值：它把 SPZ、SOG、MPEG GSC、glTF 扩展之间的矛盾转化成格式分层问题。我们的贡献不是发明最高压缩 codec，而是定义“压缩 payload 如何被流式容器可靠调度”。

风险：需要避免写成普通封装器。必须通过随机访问、渐进加载、Web decode profile 证明 envelope 有必要。

### 5.3 第三优先：GPU-upload-aware layout 与 runtime hint

核心设计：

- chunk 内字段按 WebGPU / WebGL 上传路径组织。
- manifest 记录 Morton order、预排序方式、alignment、attribute buffer layout。
- 每个 node 提供 opacity、scale、depth、importance 统计，帮助 culling / budget selection。

为什么有价值：WebSplatter 和 PlayCanvas SOG 都说明浏览器端性能很大程度取决于数据是否“拿来就能进 GPU”。这能让格式论文区别于传统压缩论文。

风险：如果做得太深入，会变成渲染器专用格式。应把它设计成 profile / hint，而不是强制绑定某个 renderer。

### 5.4 第四优先：标准桥接层

核心设计：

- 向上：可嵌入 3D Tiles tile content 或作为 tileset payload。
- 向下：可导出 glTF KHR_gaussian_splatting + SPZ。
- 横向：保留 OpenUSD / MPEG GSC 的扩展映射位置。

为什么有价值：2026 年 glTF、SPZ、3D Tiles、OpenUSD、MPEG GSC 都在快速标准化。论文如果忽略它们会显得脱离生态；但如果只复述标准也没有创新。最好的位置是做“Web progressive streaming layer”，并证明它可以与标准协作。

### 5.5 第五优先：连续 / prefix LoD 的可选元数据

核心设计：

- 每个 chunk 内 splat 按 importance / prefix budget 排序。
- manifest 记录 prefix breakpoints：例如 10%、25%、50%、100%。
- 支持 budget-driven rendering：先上传 prefix，再补后缀。

为什么有启发：Matryoshka GS、CLoD-GS 都说明连续 LoD 可能避免多份离散模型的存储重复和 popping。但这类方法依赖训练策略，格式可先提供承载能力，不应把论文主贡献押在重新训练连续 LoD 上。

## 6. 不适合我们做格式论文主线的问题

最不建议作为主线的两个方向：

1. **重新提出一种压缩算法并追求压缩率 SOTA。** 这会进入 LightGaussian / HAC / PCGS / MPEG GSC 等强竞争赛道，而且需要大量训练、率失真实验和主观质量评估。除非我们的压缩设计服务于随机访问和渐进 chunk，否则偏离“格式论文”。
2. **重新实现一个 WebGPU 3DGS renderer 并追求 FPS SOTA。** WebSplatter、FlashGS、PlayCanvas Engine 已经很强。我们的论文可以做最小 Web prototype 验证加载路径，但不应把贡献写成排序算法或 rasterizer。

## 7. 当前建议的论文定位

建议把论文问题从：

```text
哪种 3DGS 格式更好？
```

升级为：

```text
如何设计一种面向 Web 的 progressive spatial Gaussian container，
在空间随机访问、渐进质量层、浏览器解码、GPU 上传和标准互操作之间建立清晰的数据组织契约？
```

这个定位有三个优点：

- 它直接由前沿论文需求推出，而不是凭空造格式。
- 它避开纯压缩、纯训练、纯渲染算法的高风险赛道。
- 它能把已有四个主案例纳入统一对照：RAD 偏 runtime paging，LCC2 偏空间 node，SOG 偏 Web codec，3D Tiles 偏标准 HLOD；我们的格式尝试补齐它们之间的 progressive Web streaming 层。

