# 研究计划：面向 Web 3DGS 流式交付的显式语义契约研究

最后更新：2026-06-12

## 1. 研究动机

3D Gaussian Splatting 正在从离线重建结果，逐渐变成需要在浏览器中加载、调度和渲染的交互式 3D 资产。围绕这一目标，现有生态已经出现明显分层：

- PLY 更像训练输出和交换基线。
- SPZ、MPEG GSC 等方向关注 Gaussian payload 压缩。
- glTF `KHR_gaussian_splatting` 关注资产 schema。
- 3D Tiles 关注大规模场景的空间层级和流式容器。
- SOG Streaming、Spark RAD、XGRIDS LCC2 等系统则在各自 runtime 中打通 LoD、chunk、payload 和加载调度。

因此，本研究的动机不能再简单写成“3DGS 数据很大，Web 需要流式加载”。这个问题已经被许多系统以不同方式解决。

更准确的动机是：

```text
现有 Web 3DGS 系统已经能够实现流式加载，
但它们通常以端到端工具链形式耦合 LoD 生成、payload 编码、
chunk layout、runtime scheduling 和 renderer assumptions。

这种耦合使得格式语义难以独立验证，
系统实验难以归因，
不同 LoD / codec / scheduler 难以复用或替换，
也使开放 Web runtime 很难消费来自不同工具链的 3DGS assets。
```

换句话说，当前缺少的不是又一个压缩算法或 renderer，而是离线 LoD / packing 工具和浏览器 runtime 之间的一个**最小、显式、可验证的 streaming contract**。

这个 contract 的意义不是替代 3D Tiles、glTF、SPZ、SOG 或 RAD，而是回答：

```text
一个 Web 3DGS runtime 至少需要从文件中读到哪些语义，
才能独立执行按需加载、渐进细化、chunk 请求、fallback、
显存预算和 GPU 上传等行为？
```

## 2. 问题陈述

本研究关注的是 **Web 3DGS streaming 数据格式的语义边界**。

现有系统往往把以下职责混在同一实现中：

| 职责 | 典型位置 | 问题 |
| --- | --- | --- |
| LoD generation | 离线转换器、训练或优化工具 | 生成结果往往只适配特定 runtime。 |
| Payload codec | SPZ、SOG、RAD internal encoding、GLB extension | codec 能否随机访问、渐进解码、GPU 友好，常常没有统一声明。 |
| Chunk layout | manifest、tile、page、binary range | chunk 是否独立可解码、是否依赖其他 chunk，语义可能隐含。 |
| Refinement semantics | renderer / runtime 代码 | parent-child 是 replacement、additive 还是 residual，常常依赖实现推断。 |
| Runtime scheduling | viewer / SDK | priority、error、decode cost、GPU upload cost、eviction 规则难以从格式层验证。 |
| Renderer backend | WebGL / WebGPU / native renderer | buffer layout、sorting granularity、GPU residency 与格式语义耦合。 |

本研究的问题不是证明垂直集成系统不好。RAD、SOG、Cesium 3D Tiles 和 LCC2 在各自场景中都有合理优势。

本研究的问题是：

```text
如果目标是开放 Web runtime、可复现实验和跨工具链资产交付，
那么哪些 streaming 语义应该显式进入格式 contract，
哪些决策应留给 runtime？
```

## 3. 核心研究问题

主研究问题：

```text
如何为 Web 3D Gaussian Splatting 定义一个最小而显式的 streaming contract，
使离线 LoD / packing 结果、chunk payload、codec profile 与 runtime scheduling
可以被独立描述、验证和局部替换，
并使浏览器 runtime 的按需加载、渐进细化和资源预算行为可执行、可复现？
```

子问题：

1. 现有 3DGS 格式和流式系统分别显式表达了哪些 streaming 语义，哪些语义仍隐含在 runtime、codec 或工具链中？
2. 一个 Web 3DGS streaming contract 的最小必要字段边界是什么？
3. 如何评价一个格式是否具备 contract-level 的显式性、可验证性和 runtime 可执行性？
4. W3GS 作为 reference contract，能否承载不同 LoD 生成结果、payload profile 和调度策略，而不把语义绑定到单一 renderer？
5. 与现有端到端格式相比，W3GS 的收益、边界和额外开销分别是什么？

研究边界：

- 不提出新的 3DGS 重建算法。
- 不声称提出最优 LoD 生成算法。
- 不声称提出最高压缩率 codec。
- 不声称提出完整高质量 3DGS renderer。
- 不替代 3D Tiles、glTF、SPZ、SOG、RAD 或 LCC2。
- W3GS 是一个 reference contract / profile，用来验证 Web 3DGS streaming 语义边界。

## 4. 评价标准

评价标准必须服务于研究问题，而不是简单比较 FPS 或压缩率。

### 4.1 Format-Level 评价标准

| 标准 | 需要回答的问题 |
| --- | --- |
| 显式性 | 空间覆盖、LoD 层级、chunk、codec、依赖、refinement、runtime hint 是否写入格式字段？ |
| 可验证性 | 是否能通过字段检查判断 chunk 依赖、fallback 可渲染性、byte range、codec profile、LoD role 是否有效？ |
| 解耦性 | LoD generator、payload codec、scheduler、renderer backend 是否能局部替换，而不是整体重写？ |
| Runtime 可执行性 | 浏览器 runtime 能否仅凭 contract 执行请求、优先级排序、GPU upload、eviction 和 fallback？ |
| Web 可交付性 | 是否支持 chunk fetch、range fetch、CDN/cache、并发请求、渐进首屏？ |
| Payload 兼容性 | 是否能承载 raw、SPZ-like、SOG-like、glTF-like 或未来 codec profile？ |
| 开销 | manifest / index 大小、chunk 数量、请求数量、解析成本、GPU buffer 额外成本是否可控？ |
| 生态边界 | 它是 payload、schema、container、runtime format，还是 contract/profile？与其他生态如何组合？ |

### 4.2 对比维度

后续比较现有格式时采用以下维度：

| 维度 | 说明 |
| --- | --- |
| 格式定位 | 训练交换、payload codec、Web delivery、runtime 私有格式、标准容器或 contract/profile。 |
| Spatial index | 是否显式表达 node、bounds、parent / children、coverage。 |
| LoD / layer semantics | 是否显式表达 coarse / fine、base / refinement、ordered layers。 |
| Payload chunk addressability | 是否能定位、请求、缓存、独立解码 chunk。 |
| Codec profile | codec 是否独立声明，是否说明属性 schema、decode target、随机访问能力。 |
| Refinement contract | replacement、additive、residual、replace-by-children 是否显式。 |
| Runtime scheduling hints | error、priority、screen size、decode cost、GPU upload bytes、cache policy 是否显式。 |
| GPU / renderer interface | 是否说明 buffer layout、sorting granularity、GPU residency、upload unit。 |
| Interoperability | 是否能映射到 SPZ、SOG、glTF、3D Tiles 或其他生态。 |
| Conformance | 是否存在可机器检查的有效性规则和失败模式。 |

## 5. 对比对象与背景对象

### 5.1 主对比对象

主对比对象应是已经体现 streaming / LoD / chunk / runtime 语义的体系：

| 对象 | 为什么作为主对比 |
| --- | --- |
| Spark RAD | 代表 renderer-specific random-access progressive streaming 和 GPU paging。 |
| XGRIDS LCC2 | 代表生产级大场景空间 LoD 容器和多后端数据引用。 |
| PlayCanvas / SuperSplat SOG Streaming | 代表 Web-native compressed payload、LOD chunks 和 viewer pipeline。 |
| Cesium 3D Tiles Gaussian Splat | 代表标准化 geospatial HLOD container + glTF/SPZ payload 组合。 |

这四类不是全部 3DGS 格式，而是覆盖 Web 3DGS streaming 中最有代表性的四种范式：

```text
runtime-private random access；
production scene container；
Web-native chunked payload；
standard geospatial HLOD container。
```

### 5.2 背景对象

| 对象 | 论文定位 |
| --- | --- |
| PLY / Gaussian Splat PLY | 训练输出和交换基线，不具备 streaming contract。 |
| SPZ | 压缩 payload，不是空间 streaming contract。 |
| glTF KHR_gaussian_splatting | 资产 schema 和互操作层，不是完整 runtime scheduling contract。 |
| SPLAT / KSPLAT | 早期 Web viewer / compressed viewer 格式，作为历史背景。 |
| OpenUSD Gaussian / Particle Fields | DCC / VFX / 生产管线表达趋势。 |
| MPEG Gaussian Splat Coding | 编码标准化趋势。 |

## 6. 我们的方法：W3GS

W3GS 的定位是：

```text
一个面向 Web 3DGS streaming 的 reference contract / profile。
```

它不直接定义唯一 LoD 算法、唯一 codec 或唯一 scheduler，而是定义离线 packing 输出和浏览器 runtime 之间需要共享的显式语义。

### 6.1 W3GS 的核心文件

```text
scene.w3gs.json
nodes.w3gs.json
chunks.w3gs.json
payload/
  chunks-*.bin
```

### 6.2 W3GS 的核心语义层

| 层 | 作用 |
| --- | --- |
| Scene manifest | 声明场景、入口、profile、文件关系、默认 codec。 |
| Spatial node tree | 显式记录 node、bounds、parent、children、coverage。 |
| Layer / LoD contract | 表达 summary、leaf、base、refinement、replacement / additive 语义。 |
| Chunk table | 描述 payload uri、byte range、splat count、codec、attribute schema。 |
| Codec profile | 描述 raw SH0、raw SH3 以及未来压缩 payload 的解码约束。 |
| Runtime hints | priority、decode cost、GPU upload bytes、cache policy、error metric。 |
| Conformance metadata | 用于检查依赖、fallback、byte range、LoD role、storage overhead。 |

### 6.3 LoD 生成策略的地位

LoD 生成策略不是 W3GS 的核心贡献，而是 reference converter 的实现选择。

当前已有两种模式：

| 模式 | 地位 |
| --- | --- |
| `duplicated-parent` | baseline，用于展示早期调度链路和重复存储问题。 |
| `parent-summary` | 当前推荐 reference strategy，用于生成 leaf fine data + parent summary data。 |

这两种模式的作用是证明：

```text
同一个 W3GS contract 可以承载不同 LoD 生成结果。
```

而不是证明 `parent-summary` 是最优 LoD 算法。

### 6.4 当前 Raw Payload Profiles

当前 W3GS 0.1 已定义两个无压缩 reference profile：

| Profile | 内容 | 用途 |
| --- | --- | --- |
| `raw-gaussian-v0` | SH0，14 个 float32，56 bytes/splat。 | 链路 smoke、兼容与 SH 阶数消融。 |
| `raw-gaussian-sh3-v0` | 完整 SH3 渲染语义，59 个 float32，236 bytes/splat。 | 正式同源实验的无压缩属性保留基线。 |

SH3 profile 保存 3 个 DC 和 45 个高阶系数，排列与 Graphdeco 官方 PLY save/load 一致。它是便于验证 contract 和属性保留的 raw reference layout，不是生产压缩方案。

## 7. 实验设计

实验必须围绕 contract 是否必要、是否可执行、是否可验证来设计。

### 7.1 字段级缺口分析

目标：

```text
证明现有格式中哪些 streaming contract 语义是显式的，
哪些是隐式的，
哪些绑定在 runtime / SDK / codec 中。
```

方法：

- 对 RAD、LCC2、SOG Streaming、Cesium 3D Tiles 3DGS 做字段级表格。
- 标注每个维度为：显式 / 部分显式 / 隐式 / 缺失。
- 给出来源：源码、官方文档、demo 样本、notes。

当前状态：**第一版已完成**。报告位于 `notes/comparisons/existing-format-gap-analysis.md`。结果没有证明 W3GS 最优，而是明确了五个对象各自显式、部分显式和隐式于实现的语义边界。

### 7.2 W3GS Conformance 检查

目标：

```text
证明 W3GS contract 不是描述性文本，而是可以被机器检查。
```

可检查规则包括：

- layer 引用的 chunk 必须存在。
- chunk byte range 不能越界。
- chunk dependency graph 不能有环。
- startupSet 引用和 dependency closure 必须有效；视觉完整性在字段不足时应报告“无法严格证明”，不能假装已经验证。
- codec profile 必须声明 attribute layout。
- replacement refinement 中 active set 必须有确定规则。
- payload byteLength 必须与 splatCount / attribute schema 一致。

当前状态：**repository-level independent reference checker 已完成**。工具位于 `tools/w3gs-validator/`，当前测试为 19/19 通过。它不能替代 codec 解码、视觉正确性、HTTP/CDN 行为或标准认证级 conformance suite。

### 7.3 真实数据转换与可视化

目标：

```text
证明 W3GS 可以从真实 3DGS PLY 生成，
并被浏览器 WebGPU runtime 消费。
```

当前统一源：

- `D:\DATA\3DGS\PLY\HuCeZhanTing.ply`
- 2,830,135 Gaussian，62 个属性，完整 SH3，669.36 MiB。
- 已冻结 10K/250K 确定性嵌套子集及 SHA-256：`datasets/unified-huce-zhanting/`。
- 已生成 W3GS 10K SH3 `parent-summary` 样本：`demos/w3gs-from-ply/huce-zhanting-10k-parent-summary-sh3/`。
- 格式、属性保留和 conformance 已验证；浏览器增强 SH3 正确性 smoke 尚受 `Target crashed` 阻塞。

### 7.4 组件替换实验

目标：

```text
验证 W3GS 能局部替换 LoD source、scheduler 或 codec profile，
而不重写整个 runtime。
```

阶段性实验：

| 替换对象 | 当前状态 |
| --- | --- |
| LoD generator | 已有 `duplicated-parent` 与 `parent-summary`。 |
| Scheduler | 待实现 priority-first、memory-budget-first、error-first。 |
| Codec profile | 已有 SH0 与 SH3 raw profiles；尚未实现真实压缩 codec adapter。 |
| Renderer backend | 已有 WebGPU raw viewer；SH3 高阶计算的增强独立 smoke 尚未通过。 |

### 7.5 性能与开销指标

实验指标：

| 指标 | 说明 |
| --- | --- |
| manifest / metadata bytes | contract 本身带来的额外开销。 |
| payload bytes | payload 总大小。 |
| first render bytes / time | 首屏可见所需数据和时间。 |
| request count | chunk 请求数量。 |
| time to target quality | 达到目标细节所需时间。 |
| overfetch ratio | 下载但当前视角未使用的数据比例。 |
| peak GPU bytes | 最大 GPU buffer 占用。 |
| active splats | replacement active set 中实际渲染 splat 数。 |
| duplicate ratio | 原始 splat 是否被多层重复存储。 |
| summary overhead | parent summary 相对 leaf fine data 的额外开销。 |

## 8. 预期贡献

预期贡献应克制表述：

1. 提出一套 Web 3DGS streaming format semantics，用于分析离线 packing 与浏览器 runtime 之间的 contract 边界。
2. 基于 RAD、LCC2、SOG Streaming、Cesium 3D Tiles 3DGS 等公开体系，给出字段级 contract 缺口分析。
3. 提出 W3GS reference contract，显式表达 spatial nodes、LoD layers、payload chunks、codec profiles、refinement semantics 和 runtime hints。
4. 实现 PLY -> W3GS reference converter，展示同一 contract 可承载不同 LoD generation results。
5. 实现 WebGPU raw viewer，验证 W3GS payload 可被浏览器读取、上传并按 replacement active set 渲染。
6. 提出可复现实验指标，用于评价 contract 显式性、可验证性、可替换性、Web 交付开销和 runtime 可执行性。

不能写的主张：

- 不说 W3GS 是首个 Web 3DGS streaming format。
- 不说 W3GS 全面优于 RAD、SOG、LCC2 或 Cesium。
- 不说 W3GS 替代 3D Tiles、glTF、SPZ 或 MPEG GSC。
- 不说 W3GS 提出新压缩率、新 renderer 或新重建质量。
- 不把 reference converter 的 LoD 策略包装成最优 LoD 算法。

## 9. 当前原型证据

### 9.1 字段级实验

- 报告：`notes/comparisons/existing-format-gap-analysis.md`。
- 比较对象：RAD、LCC2、SOG Streaming、Cesium 3D Tiles 3DGS、W3GS。
- 每个单元格记录状态、字段/机制、证据类型和置信度。
- 当前数据足够完成字段分析，不足以做公平的跨格式运行时性能排名。

### 9.2 Converter 与 Payload Profiles

工具：`tools/ply-to-w3gs/`。

支持：

```text
--lod-mode duplicated-parent
--lod-mode parent-summary
--payload-profile raw-gaussian-v0
--payload-profile raw-gaussian-sh3-v0
```

完整 SH3 输入在 `auto` 下选择 SH3；残缺 SH3 默认报错，只有显式选择 SH0 才允许降阶，并记录 downcast metadata。

### 9.3 独立 Conformance Checker

- 工具：`tools/w3gs-validator/`。
- 检查 JSON、tree、cross-reference、byte range、dependency DAG、codec/schema、startup closure、refinement 和 runtime hints。
- 当前测试：19/19 通过。
- SH3 10K 样本：0 error、1 warning、1 info。

### 9.4 统一数据集

- 源：`D:\DATA\3DGS\PLY\HuCeZhanTing.ply`。
- manifest：`datasets/unified-huce-zhanting/dataset-manifest.json`。
- sampler：`tools/ply-sampler/`，测试 6/6 通过。
- 10K 和 250K 是固定 seed 的嵌套无放回样本，完整保留 62 个属性。

### 9.5 W3GS 10K SH3 样本

目录：`demos/w3gs-from-ply/huce-zhanting-10k-parent-summary-sh3/`。

| 指标 | 结果 |
| --- | ---: |
| nodes / layers / chunks | 25 / 25 / 25 |
| leaf splats | 10,000 |
| internal summary splats | 506 |
| payload bytes | 2,479,416 |
| startup bytes | 41,064 |
| summary overhead | 5.06% |

逐值审计确认 leaf 的 48 个 SH 系数完整保留。Parent summary 对 48 个系数逐项加权平均，仅是 reference LoD 近似，不是 profile 规定，也不保证视觉等价。

### 9.6 WebGPU Viewer

- 目录：`demos/w3gs-webgpu-viewer/`。
- 支持 SH0/SH3 profile 分派、replacement active set 和 Graphdeco SH degree 0--3 公式。
- viewer 是圆片近似，不是完整 Gaussian rasterizer。
- 历史双视角 smoke 曾成功加载 10K SH3，但不能隔离高阶 SH 正确性。
- 增强 smoke 已实现同相机 full/DC 和 CPU/WGSL fixture，当前在 Chrome/Edge 上遇到 `Target crashed`，尚未验收通过。

## 10. 下一步计划

近期严格按以下顺序：

1. **完成 WebGPU SH3 增强验收**  
   定位 `Target crashed`，取得同相机 full/DC 对照及 CPU/WGSL `<= 1e-5` 数值证据。

2. **打通 SOG Streaming 10K 同源链路**  
   经用户授权安装固定版 `@playcanvas/splat-transform@2.5.2`。先验证静态 SOG，再生成真正的 `lod-meta.json + octree/chunks` streaming 输出。

3. **打通 Spark RAD 10K 同源链路**  
   经用户授权安装 Rust stable，在固定 Spark commit 上构建 `build-lod`，生成 SH3 chunked/paged RAD。

4. **建立 10K 同源 smoke 对齐表**  
   对 W3GS、SOG Streaming、RAD 记录属性保留、LoD/空间结构、metadata、payload、chunk、startup bytes、转换时间和工具版本。

5. **扩大到 250K**  
   记录 wall time、peak RSS、临时/最终磁盘、请求单元和格式开销。250K 稳定后才决定是否运行完整 2.83M。

6. **实现受控 runtime instrumentation**  
   固定相机路径、网络、缓存和资源预算，测 first render、time to target quality、request count、overfetch、peak GPU bytes 和 active splats。

7. **做组件替换/消融实验**  
   在 W3GS 内比较 scheduler、LoD source 和 codec profile，验证 contract 的局部替换能力；这与端到端格式工具链比较分开解释。

8. **根据结果迭代 W3GS**  
   W3GS 当前不是评价体系下已证明最优的格式。实验结果应允许暴露字段冗余、缺失、额外开销和 runtime 不可执行语义，并反向修改 contract。

长期计划：

- 实现真实压缩 payload adapter，而不是只使用 raw profiles。
- 引入 coarse-vs-full visual proxy error 和统一质量目标。
- 探索与 3D Tiles、glTF、SPZ 的映射关系。
- 与团队自有 WebGPU renderer 对接。
- 在证据链稳定后撰写 Introduction、Method 和 Evaluation。
