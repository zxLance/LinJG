# 实验 1：Web 3DGS Streaming Contract 字段级缺口分析

最后审计：2026-06-11

本文对应 `research-plan.md` 第 4、5、7.1 节。目标不是给格式排名，也不是预设 W3GS 更优，而是审计五个对象把哪些 streaming contract 语义写进格式、哪些只存在于实现、哪些在当前证据中尚未发现。

对比对象：

- Spark RAD
- XGRIDS LCC2
- PlayCanvas / SuperSplat SOG Streaming
- Cesium 3D Tiles Gaussian Splat
- W3GS reference contract

## 1. 方法与判定规则

### 1.1 状态定义

| 状态 | 判定规则 |
| --- | --- |
| 显式 | 字段或规范机制直接表达该语义，消费者不必依赖特定私有实现猜测核心含义。 |
| 部分显式 | 已表达一部分关键语义，但缺少独立 profile、粒度、约束或可执行字段。 |
| 隐式于实现 | 格式字段不足，语义主要从 loader、SDK、renderer 或调度代码中获得。 |
| 未发现 | 在已审计样本、源码和官方材料中没有发现足够证据；不等于格式确定没有。 |

### 1.2 证据类型与置信度

| 证据类型 | 含义 |
| --- | --- |
| 本地样本直接证据 | 直接解析仓库中的 `.rad`、`.lcc2`、`lod-meta.json`、SOG meta、`tileset.json`、GLB summary 或 W3GS JSON/payload。 |
| 源码直接证据 | 直接阅读 encoder、decoder、loader、runtime 或 renderer 代码。 |
| 官方规范或文档 | 官方 specification、whitepaper、用户文档、API 文档或教程。 |
| 论文证据 | 同行评审论文或正式技术论文。仅用于解释研究背景，不用论文二手描述覆盖真实字段。 |
| 推断 | 从字段组合或运行结果推导，但没有规范或源码直接确认。 |

置信度分为：

- **高**：本地样本与源码/规范相互印证，或存在规范性标准。
- **中**：有官方文档或真实样本，但语义不完整、版本存在冲突或缺少实现验证。
- **低**：主要依赖推断。

本实验不用“未发现”证明格式缺陷；它只描述当前可审计边界。

## 2. 数据与证据审计

### 2.1 本地样本审计

| 对象 | 本地材料与直接结果 | 证据边界 |
| --- | --- | --- |
| Spark RAD | `demos/spark-rad-demo/coit-40m-sh1-lod.rad` 存在，大小 `1,280,517,688` bytes。直接解析得到 `RAD0`、version 1、50,937,127 splats、`lodTree=true`、chunkSize 65,536、778 chunks；chunk ranges 连续覆盖 `allChunkBytes=1,280,467,288`，加 50,400-byte header/meta 后与文件大小一致。首个 `RADC` chunk 含 `center/alpha/rgb/scales/orientation/sh1/child_count/child_start`，各列为 gzip 压缩。 | 足以验证真实容器、chunk table、范围一致性、属性列和 LoD 拓扑列；尚未逐个解码 778 个 RADC payload，也未形成轻量、许可清楚的可分发 RAD 基准。 |
| XGRIDS LCC2 | `demos/qiyu-lcc2-demo/data/K1-LuoJiaShiYanShi.lcc2` 可直接解析。version 0.0.3、66 nodes、65 个 node 有 `data.3dgs`、43 个非叶 node 同时有 child 和 `data.3dgs`；`splatType=.sog`，`renderingHints` 声明 EWA、depth sorting、pinhole、sRGB。 | 足以分析索引、node data 引用和部分 renderer hints；缺 `data/3dgs/*.sog`，无法验证 `start/count` 与 codec block、实际解码和渲染。 |
| SOG Streaming | `demos/playcanvas-roman-parish-lod/` 有完整下载样本，共 789 files、约 777.02 MiB。`lod-meta.json` 有 7 个 LOD、131 个 filenames、octree bounds/children 和 leaf `lods.file/offset/count`；`0_0/meta.json` 直接声明 524,881 splats 与 `means/scales/quats/sh0` WebP 文件。 | 足以验证 manifest、leaf LOD 引用和 SOG 物理布局；样本过大，尚未做受控网络、GPU、移动端和跨 renderer 实验。 |
| Cesium 3D Tiles 3DGS | `demos/cesium-3dgs-lod-microsoft-sh0/` 是约 3.86 MiB 的真实抽样链路。root 有 `boundingVolume`、`geometricError=93.2957`、`refine=REPLACE`，内容可指向 GLB 或外部 tileset；GLB 使用 `KHR_gaussian_splatting` 和 `KHR_gaussian_splatting_compression_spz_2`。 | 足以验证标准容器、HLOD refinement 与 Gaussian payload 扩展；不是完整 asset，不能代表全场景 tile 数、网络调度或生产 tiler 行为。 |
| W3GS | `demos/w3gs-format-sample/` 有结构样本；`demos/w3gs-from-ply/point_cloud_parent_summary/` 有 51 nodes/chunks 和真实 raw payload；`tools/ply-to-w3gs/` 有 converter；`demos/w3gs-webgpu-viewer/` 能读取 byte range 字段、执行 replacement active set 并上传 WebGPU storage buffer。 | 足以审计当前 reference contract 和 raw profile；实际 viewer 目前按 URI 整文件 fetch 后在内存切片，未证明 HTTP Range；仅实现 raw codec 和简化 billboard renderer；无独立 conformance schema/checker。 |

### 2.2 源码、规范与文档审计

| 对象 | 源码直接证据 | 官方规范或文档 | 论文证据 | 仍属推断的部分 |
| --- | --- | --- | --- | --- |
| Spark RAD | 本地 `sources/spark-src/rust/spark-lib/src/rad.rs` 定义 meta/chunk/property；`src/SplatPager.ts` 实现 header 读取与 Range 请求；`build-lod` 与 LoD 源码可审计。 | 本地 Spark 官方 docs 镜像含 `docs/docs/lod-getting-started.md`；源码许可为 MIT。 | 未使用独立论文证明 RAD 字段。 | 跨 renderer 可移植成本、最佳 chunk 粒度等评价。 |
| XGRIDS LCC2 | 当前没有 LCC Web SDK 源码本地镜像；format note 记录官方 SDK 仓库。 | `LCC2Whitepaper` 与 LCC Web 文档提供字段说明。重要冲突：白皮书把 `data` 描述为 leaf 字段，但本地 0.0.3 样本中大量非叶 node 也含 `data.3dgs`。 | 未发现能替代格式规范的独立论文证据。 | 父子替换时序、独立解码边界、请求合并和缓存策略。 |
| SOG Streaming | PlayCanvas Engine 官方源码中的 `gsplat-octree` / `gsplat-octree-instance` 可直接确认 leaf 展平、距离 LOD、underfill、引用计数和 cooldown；当前未保存本地源码镜像。 | PlayCanvas SOG Format、SplatTransform、Streaming LOD tutorial 和 GSplat API。 | 未使用论文证明 manifest 字段。 | leaf 多 LOD 是否均为完整质量版本、压缩块与 `offset/count` 的物理随机访问边界。 |
| Cesium 3D Tiles 3DGS | 本地没有完整 CesiumJS 源码镜像，但 GLB/tileset 样本可直接检查。 | OGC 3D Tiles、Khronos `KHR_gaussian_splatting`、Cesium 官方 LOD 教程/API；3D Tiles 规范仓库有 JSON schemas。 | 未使用论文替代标准字段。 | Cesium ion/iTwin tiler 的 LoD 生成算法、Gaussian-specific 误差质量和完整资产性能。 |
| W3GS | converter、实验平台和 WebGPU viewer 均为本地源码直接证据。converter 的 `check_consistency` 当前检查 chunk 引用、文件存在、range 越界和 raw stride。 | `proposed-format-design.md` 是项目设计草案，不是外部标准。 | 尚无发表论文证据。 | SPZ/SOG/glTF profile 可替换性、hint 的预测准确度和跨 renderer 行为。 |

### 2.3 LCC2 规范与样本冲突的处理

本实验不把两种证据强行合并：

```text
官方白皮书：data 作为 leaf node 数据描述。
本地 LCC2 0.0.3 样本：43 个非叶 node 同时含 child 和 data.3dgs。
```

因此本报告只下结论：**本地 0.0.3 生产样本证明 node-level data 不限于叶节点；但是否为所有 LCC2 版本的规范保证，当前置信度为中。** 后续应向 XGRIDS 确认版本演进或获取对应 SDK parser 源码。

## 3. 字段级 Contract Matrix

单元格格式为：**状态；字段/机制；证据；置信度**。

### 3.1 格式定位与 Spatial Index

| 对象 | 格式定位 | Spatial index |
| --- | --- | --- |
| Spark RAD | **显式**；`RadMeta.type=gsplat`、`lodTree`、chunk table，定位为 Spark LoD/paging 容器；本地 RAD + `rad.rs` + Spark docs；**高**。 | **部分显式**；`child_count/child_start` 显式表达 splat 合并树，但没有独立 spatial node、bounds 或 coverage；本地 RADC + `rad.rs`；**高**。 |
| XGRIDS LCC2 | **显式**；`.lcc2` 是场景/LoD JSON 索引，`splatType` 指向外部 payload；本地 `.lcc2` + whitepaper；**高**。 | **显式**；递归 `child`、`childNum`、node `boundingBox` 和 id 路径表达空间树；本地样本；**高**。 |
| SOG Streaming | **显式**；SOG 是 Web 压缩 payload，`lod-meta.json` 是 PlayCanvas streaming manifest；本地样本 +官方文档；**高**。 | **显式**；`tree.bound/children` 与 leaf `bound` 构成 octree；本地 `lod-meta.json` + Engine source；**高**。 |
| Cesium 3D Tiles 3DGS | **显式**；3D Tiles 管 HLOD，GLB/glTF extension 管 Gaussian payload；本地样本 + OGC/Khronos/Cesium 文档；**高**。 | **显式**；tile `boundingVolume`、`children`、`transform`，并支持外部 tileset；本地样本 + 3D Tiles spec；**高**。 |
| W3GS | **显式**；`format=W3GS`，项目定义为 reference contract/profile；`scene.w3gs.json` +设计草案；**高（对当前草案）**。 | **部分显式**；`parent/children/bounds` 已实现，但研究计划提出的独立 `coverage` 字段尚未进入当前样本；W3GS JSON + converter；**高**。 |

### 3.2 LoD / Layer 与 Payload Chunk

| 对象 | LoD / layer semantics | Payload chunk addressability |
| --- | --- | --- |
| Spark RAD | **部分显式**；父 splat 与连续子 splat 拓扑显式，但没有命名的 base/refinement layer 或 layer role；本地 RADC + LoD 源码；**高**。 | **显式**；global `chunks[].offset/bytes`、chunk `base/count/payloadBytes`，单文件可 Range fetch，也可外置 `.radc`；本地 RAD + `SplatPager.ts`；**高**。 |
| XGRIDS LCC2 | **部分显式**；`totalLevels/lodSplats` 与每 node `data.3dgs` 表达层级数据，但没有 ordered layer、base/refinement role；本地样本；**中高**，受白皮书冲突影响。 | **部分显式**；`name/start/count` 可定位 splat 段，但不是 compressed byte range，也未声明独立解码；本地样本 + note；**高（字段）/低（可独立请求）**。 |
| SOG Streaming | **显式**；leaf `lods` 以数值键 0..N 显式列出质量层级；本地样本 + Engine source；**高**。 | **部分显式**；`file/offset/count` 定位 SOG 资源中的 splat 区间，文件级 URI 明确，但没有 compressed byte range/independent-decode 声明；本地样本 + SOG spec；**高**。 |
| Cesium 3D Tiles 3DGS | **显式**；父子 tile、`geometricError` 和 HLOD traversal 明确 coarse/fine 关系，但不表达 tile 内 progressive layer；本地样本 + 3D Tiles spec；**高**。 | **显式（tile 粒度）**；`content.uri` 指向 GLB 或外部 tileset，可作为独立 Web 资源请求和缓存；本地样本 + spec；**高**。 |
| W3GS | **显式**；node `layers[]` 有 `level/kind/lodRole`，真实 parent-summary 样本区分 summary 与 leaf；本地 JSON + converter；**高**。 | **显式（格式字段）**；chunk 有 `uri/byteOffset/byteLength/node/layer/dependencies`；但当前 viewer 整文件 fetch 后切片，尚未验证 HTTP Range；本地 JSON + viewer；**高（字段）/中（运行时）**。 |

### 3.3 Codec Profile 与 Refinement Contract

| 对象 | Codec profile | Refinement contract |
| --- | --- | --- |
| Spark RAD | **部分显式**；每 property 有 `encoding/compression/min/max`，meta 有 `splatEncoding/maxSh`，但不是可替换的独立 codec capability profile；本地 RADC + `rad.rs`；**高**。 | **隐式于实现**；文件表达父子拓扑，实际展开、父子 active set 与过渡由 Spark runtime 决定，未发现独立 replace/add 字段；LoD/runtime source；**中高**。 |
| XGRIDS LCC2 | **部分显式**；`splatType=.sog` 与文件列表说明 payload 类型，未定义 attribute schema、codec block 或 decode capability；本地样本 + whitepaper；**高**。 | **未发现**；样本没有 replace/add/residual/hysteresis 字段，深层替换浅层是合理推断但未获规范确认；本地样本 +公开文档；**中**。 |
| SOG Streaming | **部分显式**；SOG v2 meta 显式定义 means/scales/quats/sh0 文件和 codebook，但 streaming manifest 没有独立 codec profile/capability；本地 SOG meta +官方 spec；**高**。 | **隐式于实现**；leaf LOD placement 切换、underfill fallback、cooldown 和 refcount 在 PlayCanvas Engine 中，manifest 未声明 additive/replacement；Engine source + manifest；**高**。 |
| Cesium 3D Tiles 3DGS | **显式**；`extensionsUsed/Required`、`KHR_gaussian_splatting` 和 SPZ compression extension 明确 schema/codec；本地 GLB + Khronos spec；**高**。 | **显式**；tile `refine=REPLACE/ADD`，子 tile 继承规则由 3D Tiles 规范定义；本地 root `REPLACE` + spec；**高**。 |
| W3GS | **部分显式**；`scene.codecs` 与 chunk `codec/attributeSchema` 已分离，含 `decodeTarget`，但未声明 random-access/independent-decode capability，真实 decoder 只有 raw；样本 + converter/viewer；**高**。 | **显式**；layer/chunk 有 `refinementMode=replacement/additive`，node 有 `refinementPolicy`，viewer 已实现简化 replacement active set；样本 + viewer；**高**。 |

### 3.4 Runtime Hints 与 GPU / Renderer Interface

| 对象 | Runtime scheduling hints | GPU / renderer interface |
| --- | --- | --- |
| Spark RAD | **隐式于实现**；格式有 chunk size/count，可供调度，但 screen threshold、paging budget、foveation、eviction 等由 Spark runtime 参数和代码决定；`SplatPager.ts`/renderer source；**高**。 | **部分显式**；property encoding、`splatEncoding` 和 chunk upload unit 可读，sorting、GPU residency、buffer pool 仍由 Spark renderer 实现；RAD meta + source；**高**。 |
| XGRIDS LCC2 | **部分显式**；bounds、levels、lodSplats 可用于调度，whitepaper 有可选 virtual LoD 描述；当前样本 `virtualLoD=null`，未发现 error/priority/decode cost/cache policy；样本 + whitepaper；**中**。 | **部分显式**；样本 `renderingHints` 声明 `splatting/ewa/depth/pinhole/srgb`，但无 buffer layout、upload unit 或 residency；本地样本；**高**。 |
| SOG Streaming | **部分显式**；bounds、lodLevels 和 leaf LOD 可供选择，但 `lodBaseDistance/lodMultiplier/lodUnderfillLimit/cooldown` 在 component/runtime；manifest + Engine source；**高**。 | **部分显式**；SOG 图像布局天然接近纹理上传，meta 给出 codebook/range；统一排序、placement 和 GPU 生命周期由 PlayCanvas renderer；样本 + spec/source；**高**。 |
| Cesium 3D Tiles 3DGS | **显式（tile 调度）**；`boundingVolume/geometricError/viewerRequestVolume/refine` 支撑 SSE traversal；Gaussian decode cost、sort risk、GPU bytes 未表达；3D Tiles spec +样本；**高**。 | **部分显式**；glTF accessor/SPZ、Gaussian kernel/colorSpace/projection/sortingMethod 提供资产到 renderer 的接口，GPU residency/upload policy 仍由 CesiumJS；Khronos spec +样本；**高**。 |
| W3GS | **显式**；`startupSet`、runtimeProfiles、`screenSizeEnter/Exit`、priority、decodeCost、gpuUploadBytes、cachePolicy、error/refinementPolicy 均有字段；样本 + converter；**高（存在性）**，其数值校准有效性仍未验证。 | **部分显式**；chunk 有 `gpuLayout`，codec 有 `decodeTarget`，并有 `gpuUploadBytes`；raw viewer 已上传 WebGPU storage buffer，但 sorting granularity、residency contract 和 adapter schema 未定；样本 + viewer；**高**。 |

### 3.5 Interoperability 与 Conformance

| 对象 | Interoperability | Conformance |
| --- | --- | --- |
| Spark RAD | **隐式于实现**；Spark converter 可接收多种输入，但 RAD 输出语义依赖 Spark encoder/decoder，没有标准 payload 映射；Spark source/docs；**高**。 | **部分显式**；magic/version/type、serde structs 和 decoder 错误构成实现级校验，但未发现独立 schema、validator 或公开 conformance suite；`rad.rs`；**高**。 |
| XGRIDS LCC2 | **部分显式**；`splatType`、splatFiles 和 Three.js/Cesium SDK 路线允许多后端，但每种 payload 的 schema/能力未统一；样本 +官方 docs；**中高**。 | **部分显式**；whitepaper 有版本与字段规则，但没有机器 schema/validator；且 leaf-only 文档与 0.0.3 样本冲突；whitepaper +样本；**中**。 |
| SOG Streaming | **部分显式**；SOG 有开放规格和转换工具，可被其他引擎实现；streaming manifest、parser 选择和最佳路径仍偏 PlayCanvas；官方 spec/tools/source；**高**。 | **部分显式**；SOG v2 meta 有格式规则，当前样本 version/count/files 可检查；未发现 `lod-meta.json` 的公开 JSON Schema 或独立 conformance suite；官方 spec +样本；**中高**。 |
| Cesium 3D Tiles 3DGS | **显式**；组合 OGC 3D Tiles、glTF、Khronos Gaussian 与 SPZ extension，扩展依赖通过 GLB 声明；规范 +样本；**高**。 | **显式**；3D Tiles 有规范性 JSON schema，glTF/KHR extensions 有 requirements/validation rules；是否支持某扩展仍取决于 viewer；官方 specs；**高**。 |
| W3GS | **部分显式**；codec/profile 引用机制已设计，sample 有 raw 与 placeholder 概念，但真实 converter/viewer 只验证 raw，尚未完成 SPZ/SOG/glTF adapter；设计草案 +源码；**高**。 | **部分显式**；converter 已检查引用、payload 存在、range 越界与 raw stride；尚无正式 JSON Schema、独立 validator、依赖环/startup fallback/profile 规则检查；converter + research plan；**高**。 |

## 4. 结果解释

### 4.1 确定结论

1. 四个既有体系都已经显式解决了部分 contract 问题，不存在“现有格式完全没有流式语义”的情况。
2. RAD 在字节寻址和 splat-tree 拓扑上最直接，但调度和 renderer 语义主要由 Spark 实现补全。
3. LCC2 在空间 node 与外部 payload 引用上清楚；本地样本证明内部节点可带本层数据，但该行为与公开白皮书描述存在版本边界。
4. SOG Streaming 显式表达 octree leaf 的多个 LOD 和 SOG 文件映射；refinement/fallback/cache 行为主要在 PlayCanvas runtime。
5. Cesium 组合在空间 HLOD、refinement、互操作和 conformance 上最完整；其粒度是 tile，且通用 SSE contract 不等于 3DGS 专属 progressive contract。
6. W3GS 当前把 node/layer/chunk/refinement/hints 分成独立字段，但 codec 互换、HTTP Range、renderer adapter 和完整 conformance 仍是“已设计、未充分验证”。

### 4.2 不确定边界

- 不根据本地 LCC2 0.0.3 样本断言所有 LCC2 版本都允许内部节点数据。
- 不根据 `start/count` 断言 LCC2 或 SOG 支持任意 compressed byte-range 独立解码。
- 不根据 RAD chunk table 断言固定 65,536 splats 是跨设备最优粒度。
- 不根据 Cesium 抽样链路推断完整资产的 tile 数、带宽或性能。
- 不根据 W3GS 字段存在性断言 runtime hints 已经准确、codec 已可插拔或性能优于既有系统。

## 5. 数据完备性与补充建议

### 5.1 是否足以完成本次字段级分析

**结论：足够完成第一版字段级分析。**

理由：五个对象都至少有真实样本或 reference sample；RAD 和 W3GS 有本地源码；SOG、LCC2、Cesium 有官方文档/规范；不确定语义已经能够标为“隐式于实现”或“未发现”，无需为了填满表格而猜测。

完成论文定稿前仍建议补两项，但不阻塞本次实验：

1. 固定 PlayCanvas Engine、LCC2 whitepaper、3D Tiles 和 `KHR_gaussian_splatting` 的 commit/version 快照，避免后续规范变化。
2. 向 XGRIDS 确认“非叶 node 带 `data.3dgs`”对应的版本语义，或保存对应 SDK parser 源码。

### 5.2 是否足以做后续运行时性能实验

**结论：不足以做公平的跨格式运行时性能对比。**

原因分别是：

- RAD 样本完整但过大，资产许可未明确，且缺小型同源基准。
- LCC2 缺真实 SOG payload，无法解码或渲染。
- SOG 完整但约 777 MiB，未建立受控网络和 GPU instrumentation。
- Cesium 只有抽样链路，不是完整 asset。
- W3GS viewer 当前整文件 fetch 后切片，使用简化 billboard renderer，不能把结果直接与成熟 Gaussian renderer 归因比较。
- 五种对象没有同一场景、同一质量目标、同一 renderer/backend 和同一网络条件。

因此后续实验应优先做 W3GS 内部消融和 contract 可执行性，而不是立即宣称跨系统 FPS/首屏全面比较。

### 5.3 完成本次字段级分析的必需补充

当前没有必须下载的大文件。定稿级必需工作是：

- 保存官方材料的版本/commit 和访问日期。
- 对报告中的关键字段生成可复查解析摘要或脚本，尤其是 RAD header、LCC2 node 统计、SOG leaf 统计、Cesium extension 列表。
- 为 W3GS 实现独立 conformance checker；在此之前 Conformance 只能评为“部分显式”。

### 5.4 后续性能对比实验的必需补充

1. 一个许可清楚、体积适中的同源 Gaussian 数据集，并尽量转换为 RAD、SOG Streaming、W3GS；无法转换的 LCC2/Cesium 不应被强行纳入同 renderer 对比。
2. 实际 HTTP Range loader、请求/字节/时间记录、decode 与 GPU upload 计时、显存统计和统一相机路径。
3. LCC2 的完整 `data/3dgs` payload；否则 LCC2 只参加字段实验。
4. Cesium 的完整可访问 tileset 或稳定的远程运行记录；否则只参加字段实验。
5. W3GS 使用真实 Gaussian renderer 或明确限定为 contract/runtime 原型，不与成熟渲染器比较视觉质量和 FPS。

### 5.5 可选增强材料与潜在下载

本次未下载大型文件。若进入性能阶段，可评估：

| 来源 | 预计大小 | 许可/使用边界 | 必要性 |
| --- | ---: | --- | --- |
| Spark official assets `robot-head.spz`，`https://github.com/sparkjsdev/assets/blob/main/splats/robot-head.spz` | 本地记录约 1,153,152 bytes；派生 RAD 大小待测 | Spark 主仓库 MIT；assets 仓库/具体资产许可仍需单独确认 | 推荐，用于生成小型可复现 RAD；不是本次字段分析必需。 |
| 当前远程 `coit-40m-sh1-lod.rad` | 1,280,517,688 bytes | 公开 demo URL，但资产许可未在本地记录 | 已有完整本地副本，无需重复下载；不宜作为可分发基准。 |
| XGRIDS 样本对应 `data/3dgs/*.sog` | 未知，预计显著大于 76.8 KiB 索引 | 来源与再分发许可必须向样本提供方确认 | 只有在做 LCC2 runtime/performance 时必需。 |
| PlayCanvas 更小的官方 Streaming LOD 样本或由许可清楚 PLY 自行生成的裁剪样本 | 未知 | Engine 为 MIT；具体示例资产许可需单独确认 | 推荐，降低 777 MiB 样本的实验成本。 |
| Cesium ion public asset `4547222` 完整 traversal/content | 约 110M splats，传输总量未统计 | 受 Cesium ion 与资产访问条件约束，不应擅自镜像再分发 | 仅在全场景 Cesium 性能实验时需要；格式分析不需要。 |

## 6. 本实验对后续工作的直接要求

1. 先实现 W3GS conformance checker，覆盖 cross-reference、range、dependency DAG、startup fallback、codec/schema 和 refinement active-set。
2. 将 W3GS viewer 从“整 payload 文件 fetch”改为真实 Range 或独立 chunk fetch，才能验证 chunk addressability 的运行时价值。
3. 后续实验优先比较同一 W3GS 数据的 scheduler/LoD/codec 组件替换；跨格式实验只在数据、renderer 与质量目标可控时进行。

## 7. 主要证据索引

本地：

- `demos/README.md`
- `demos/spark-rad-demo/coit-40m-sh1-lod.rad`
- `sources/spark-src/rust/spark-lib/src/rad.rs`
- `sources/spark-src/src/SplatPager.ts`
- `demos/qiyu-lcc2-demo/data/K1-LuoJiaShiYanShi.lcc2`
- `demos/playcanvas-roman-parish-lod/lod-meta.json`
- `demos/playcanvas-roman-parish-lod/0_0/meta.json`
- `demos/cesium-3dgs-lod-microsoft-sh0/data/tileset.json`
- `demos/cesium-3dgs-lod-microsoft-sh0/data/tile_0.gltf.json`
- `demos/w3gs-format-sample/*.json`
- `demos/w3gs-from-ply/point_cloud_parent_summary/`
- `demos/w3gs-webgpu-viewer/app.js`
- `tools/ply-to-w3gs/convert_ply_to_w3gs.py`
- `notes/format-cases/*.md`

官方：

- Spark LoD docs: https://sparkjs.dev/docs/lod-getting-started/
- XGRIDS LCC2Whitepaper: https://github.com/xgrids/LCC2Whitepaper
- PlayCanvas SOG: https://developer.playcanvas.com/user-manual/gaussian-splatting/formats/sog/
- PlayCanvas Streaming LOD: https://developer.playcanvas.com/tutorials/gaussian-splat-streaming-lod/
- PlayCanvas Engine: https://github.com/playcanvas/engine
- OGC 3D Tiles: https://docs.ogc.org/cs/22-025r4/22-025r4.html
- Khronos Gaussian Splatting: https://github.com/KhronosGroup/glTF/tree/main/extensions/2.0/Khronos/KHR_gaussian_splatting
- Cesium 3DGS LOD: https://cesium.com/blog/2026/04/27/3d-gaussian-splats-lod/
