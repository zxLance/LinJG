# 统一源 PLY 到主对比格式的工具链可行性调查

调查日期：2026-06-11  
统一输入：`D:\DATA\3DGS\PLY\HuCeZhanTing.ply`

## 1. 调查范围与证据口径

本调查只做只读 preflight、现有工具探测、源码核验和官方资料核验；未安装大型依赖，未转换完整数据，也未向云服务上传数据。

证据标记如下：

- **[实际]**：本机命令、文件 header 或工具 `--help` 的实际结果。
- **[源码]**：本地或官方仓库中的实现直接证据。
- **[官方]**：项目官方文档、规范、发行页或包元数据。
- **[推断]**：由数据规模、实现结构或相邻能力推断，尚未通过转换实测确认。

网络资料的访问日期均为 **2026-06-11**。

## 2. 统一输入 preflight

| 项目 | 结果 | 证据 |
| --- | --- | --- |
| 路径 | 文件存在 | **[实际]** PowerShell `Test-Path` |
| 文件大小 | 701,875,230 bytes，669.36 MiB | **[实际]** 文件元数据；未扫描 payload |
| PLY 格式 | `binary_little_endian 1.0` | **[实际]** 只读至 `end_header` |
| Gaussian 数量 | 2,830,135 | **[实际]** `element vertex` |
| 属性 | 62 个标量属性，含 position、normal、DC、opacity、scale、rotation 和 45 个 `f_rest_*` | **[实际]** PLY header |
| SH 阶数 | 可表达 SH3 | **[实际]** 45 个高阶 SH 系数 |
| W3GS 输入兼容性 | 必需的 14 个基础字段齐全 | **[实际]** `convert_ply_to_w3gs.py --inspect-only` 成功 |

因此，本次输入不是 SH0/RGB 简化 PLY。任何只保留 DC color 的输出都必须作为有损属性基线单独标注，不能与保留 SH3 的输出直接做无条件画质比较。

## 3. 分链路调查

### 3.1 Spark RAD

**工具与版本。** 官方可信工具为 Spark 仓库内 Rust CLI `build-lod`。本地已有官方源码镜像 `sources/spark-src/`，版本 `@sparkjsdev/spark 2.1.0`，commit `82fc4a9d9596837ad602637ed7430caa60662331`，MIT License。入口为 `npm run build-lod -- ...` 或直接 `cargo run --release`。证据：**[实际/源码]** `sources/spark-src/package.json`、`rust/build-lod/src/main.rs`、`docs/docs/lod-getting-started.md`；**[官方]** [Spark 仓库](https://github.com/sparkjsdev/spark)、[LoD 文档](https://sparkjs.dev/docs/lod-getting-started/)。

**自动化与规模。** CLI 可固定 commit 和参数，适合复现实验。官方文档称运行时 LoD 可支持约 30M 输入 splats，并给出每 1M 约 1--3 秒的运行时构建量级；离线 `build-lod` 直接面向大数据生成。2.83M 在设计范围内，但本机未编译、未跑小样，离线峰值内存和实际耗时仍是 **[推断]**。

**属性保留。** PLY reader 读取 position、scale、rotation、opacity、DC 与高阶 SH；`--max-sh=0..3` 可限制输出阶数，本输入可用 `--max-sh=3`。RAD 对 position、alpha、RGB、scale、orientation、SH 分别选择压缩编码，高阶 SH 还可用 `--cluster-sh` 聚类。它不是逐 float 原样复制，而是保留语义后量化编码。

**LoD、chunk 与 Streaming。** `--quick`/`--quality` 或 `tiny-lod`/`bhatt-lod` 生成父 Gaussian 和 LoD 树；`--rad` 生成单文件 RAD，`--rad-chunked` 生成小 `.rad` header 加多个 `.radc`。源码中 chunk 固定为 65,536 splats，CLI 未暴露 chunk 数量参数。只有预构建 LoD 并在 Spark 中以 `paged: true` 加载，尤其是 `--rad-chunked` 输出，才应计为本研究的 paged RAD streaming；普通静态格式转换不能替代该链路。

**本机可执行性与成本。** Node.js 已安装，但 `cargo/rustc` 缺失，源码目录也没有 `node_modules` 或 `rust/target`。需安装 Rust stable 并下载 Cargo crates；**[推断]** 网络下载约数百 MiB，安装和编译产物可能占 1--3 GiB，首次 release 编译成本为分钟级。全程本地，无上传和数据隐私风险。

**结论：需小样验证。** 工具链公开、自动化且输出是真正 streaming RAD；阻塞仅是本机 Rust 环境和未做规模实测。

### 3.2 PlayCanvas / SuperSplat SOG Streaming

**工具与版本。** 官方工具为 `@playcanvas/splat-transform`，开源 MIT，既是 Node.js CLI/库，也有 SuperSplat Convert Web 前端。2026-06-11 通过 `npm view` 核验当前版本为 `2.5.2`，包解压大小 40,875,709 bytes、149 files，依赖 `@adobe/spz 0.2.2` 与 `webgpu 0.4.0`。证据：**[实际]** npm metadata probe；**[官方]** [仓库](https://github.com/playcanvas/splat-transform)、[工具文档](https://developer.playcanvas.com/user-manual/splat-transform/)、[Streamed SOG 指南](https://github.com/playcanvas/splat-transform/blob/main/guides/STREAMED_SOG.md)、[SOG 规格](https://developer.playcanvas.com/user-manual/gaussian-splatting/formats/sog/)。

**自动化与规模。** 官方指南明确给出单个 PLY 的两阶段流程：先用 progressive pairwise merging 逐级 `--decimate 50%`，再给各 PLY 标记 `--lod n` 并写入 `lod-meta.json`。指南称 streamed SOG 面向数千万 Gaussian；官方示例对超大场景建议提高 Node heap 到 32 GB。2.83M 应可处理，但本机尚未安装工具，GPU/WebGPU backend、内存和耗时需实测。

**属性保留。** SplatTransform 支持 position、scale、quaternion、opacity、DC 和 SH0--SH3；`--filter-harmonics 0..3` 可主动降阶。SOG v2 将 means、scales、quats、sh0 等写入 WebP，并对高阶 SH 使用 codebook/centroid/label 压缩。因此可保留 SH3 语义，但属于有损压缩，需记录 `--iterations` 和是否使用 `--filter-harmonics`。

**LoD、chunk 与 Streaming。** 单独执行 `input.ply output.sog` 只得到静态 SOG，不能计为 SOG Streaming。研究所需输出必须是 `lod-meta.json` 加 `{lod}_{chunk}/meta.json + WebP`，其中 manifest 包含空间树和各 LOD chunk 索引。可控参数包括各级 decimation 比例、`-C/--lod-chunk-count`（默认约 512K Gaussian）和 `-X/--lod-chunk-extent`（默认 16 m），以及 SH 压缩迭代数。该输出是真正按空间与 LOD 渐进请求的 streaming 形态。

**本机可执行性与成本。** Node.js 24 已安装且满足 `>=18`，但 `splat-transform` 尚未安装。包本体约 39 MiB 解压；计入 native WebGPU 依赖后，**[推断]** 应预留约 0.1--0.3 GiB 下载/安装空间。生成多级 PLY 会带来约 1 GiB 以上临时数据和额外转换时间；D 盘当前约 35 GiB 可用。CLI 本地运行无上传风险；若使用网页转换器，则 669 MiB 数据是否离开浏览器需另行核验，不应作为论文的默认可复现路径。

**结论：需小样验证。** 公开工具已经覆盖从单 PLY 到真实 streamed SOG 的完整自动化链路，但必须先验证本机安装、WebGPU backend 和多级属性一致性。

### 3.3 XGRIDS LCC2

**已发现的相邻工具。** XGRIDS 官方 `LCC-Unity-SDK` v1.2.18（release commit `1f26d1b`）声明可导入标准 3DGS PLY，并可把“clip data”保存为 PLY 或 LCC；还声明支持 SH0/SH3 渲染。`LCC-Web-SDK` v0.6.0（commit `10d9126`）增加 LCC2 beta **读取/渲染**。LCC2 白皮书当前描述版本为 0.0.3。证据：**[官方]** [Unity SDK](https://github.com/xgrids/LCC-Unity-SDK)、[Web SDK](https://github.com/xgrids/LCC-Web-SDK)、[LCC2 Whitepaper](https://github.com/xgrids/LCC2Whitepaper)。

**缺失的关键证据。** 未发现公开的 PLY -> LCC2 writer/tiler、CLI、批处理 API 或“整场景导出为 LCC2 LoD 树”的文档。Unity SDK 的“clip data save as LCC”不能推出它会生成 LCC2，也不能推出会生成每层 Node 数据、空间分块和可复现 LoD。PlayCanvas `splat-transform` 对 `.lcc` 只有输入支持，也不是 LCC2 writer。

**自动化、属性与规模。** 因生成端未公开，无法确认 position/scale/rotation/opacity/SH 的写出精度、是否保留 SH3、2.83M 上限、LoD 算法、chunk 参数和压缩参数。官方 SDK 仓库主要发布二进制 release，未发现标准开源许可证声明；LCC2 白皮书使用带署名、再分发和用途限制的专有条款，不应简称为 MIT/Apache 式开源。

**本机可执行性与风险。** 本机未发现 Unity、Unity Hub、LCC Studio 或 XGRIDS 安装。Release asset 大小在可访问页面中未显示；Unity 编辑器本身通常是多 GiB 级安装，SDK 资产大小需下载前再核验。若存在本地 SDK/Studio 导出，隐私风险低，但自动化、许可和结果再分发边界需向 XGRIDS 确认。

**结论：当前不可复现。** LCC2 可继续参加字段分析和原生样本实验；在获得明确的 LCC2 writer、版本、许可和批处理入口前，不进入统一 PLY 同源端到端实验。若只通过 GUI 手工导出，也应降级为“只能人工”，不能与 CLI 链路混作可重复实验。

### 3.4 Cesium 3D Tiles Gaussian Splat

**已核验的公开能力。** CesiumJS 可以加载带层次 LoD 的 3D Tiles Gaussian Splat tileset；公开样本来自 Cesium ion，并以 `KHR_gaussian_splatting`、SPZ 压缩和 3D Tiles refinement 组织。Cesium 官方公开的是运行时、结果格式和从照片生成 reality model 的云端路径。证据：**[官方]** [Gaussian Splat LoD 博文](https://cesium.com/blog/2026/04/27/3d-gaussian-splats-lod/)、[CesiumJS LoD 教程](https://cesium.com/learn/cesiumjs-learn/3d-guassian-splat-tilesets-lods/)、[CesiumGS/3d-tiles-tools](https://github.com/CesiumGS/3d-tiles-tools)。

**不存在的公开链路。** 截至访问日期，未发现官方公开的本地 PLY -> 3D Tiles Gaussian HLOD tiler，也未发现 Cesium ion 文档明确接受已训练 3DGS PLY 并将其切成 Gaussian LoD tileset。开源 `3d-tiles-tools` 能重打包、升级和分析既有 tileset，但其公开 CLI 中未发现 Gaussian 或 PLY 建树命令。Cesium 能展示 Gaussian，不能据此推导存在公开 PLY tiler。

**属性、LoD 与参数。** 结果格式可表达 position、scale、rotation、opacity、SH，并可用 SPZ 压缩；3D Tiles 提供 bounding volume、geometric error、`ADD/REPLACE` refinement 和分 tile 请求。但从本 PLY 到这些内容的属性保留、SH 阶数、父层生成算法、tile 粒度和误差参数均未公开为可控转换接口，因此不能为同源实验预设。

**本机与云端风险。** 本机未发现 Cesium tiler CLI。即便未来 Cesium ion 开放 PLY 入口，669 MiB 原始场景上传会引入账户、配额、服务版本漂移、数据驻留、许可和隐私风险；未经用户明确授权不得上传。云服务的 tiler 版本/commit 也通常不可固定，不利于严格复现。

**结论：当前不可复现。** 可参加字段分析、标准机制实验和官方/原生 tileset 运行时实验；不能参加当前统一 PLY 到主研究 streaming 形态的同源转换实验。

### 3.5 W3GS reference contract

**工具与版本。** 本地工具为 `tools/ply-to-w3gs/convert_ply_to_w3gs.py`，Python CLI，无第三方依赖；当前文件 SHA-256 为 `45631DF20903ACD96E48B6D3A2788AE7EDE37B0DA527FBE8FE6F5AD05B3B978C`。仓库未发现单独许可证文件，因此它应描述为本项目 reference implementation，而不是对外宣称某种开源许可。**[实际]** `--help` 与 `--inspect-only` 均成功。

**自动化与输出形态。** 可固定参数生成 `scene/nodes/chunks` manifest 和多个 payload 文件；`parent-summary` 模式生成 internal summary、leaf fine data、replacement refinement 和 octree。`--payload-file-max-mb` 控制物理 payload 文件滚动，层和 chunk 有独立索引。因此输出具备研究中的 streaming contract 形态，不只是单文件静态格式；但当前 raw codec 没有压缩，运行时实现成熟度仍低于生产工具链。

**属性保留。** 调查完成后，W3GS 已补充 `raw-gaussian-sh3-v0`：59 个 float32、236 bytes/splat，保留 3 个 DC 与 45 个高阶 SH 系数。SH0 `raw-gaussian-v0` 仍保留用于 smoke/消融。正式同源实验应显式选择 SH3；不能再使用旧 SH0 输出代表 W3GS 的正式容量或画质基线。

**完整 2.83M 可行性。** CLI 默认只转 200,000 splats；显式提高 `--max-splats` 才会尝试全量。源码为每个选中记录执行 seek/read，构造大量 Python `Splat` 对象和多层 index list，再生成 parent summaries。它在语义上支持全量，但尚无 2.83M 实测，内存、随机/重复 seek 和构树成本存在明显风险。仅 leaf raw payload 理论下限约 151.2 MiB，另有 summary 和 JSON 开销。故不能把已有 200K 样本通过外推为“完整 PLY 已验证”。

**本机可执行性与风险。** Python 3.11 已安装，不需要下载依赖；全程本地，无上传风险。当前 D 盘约 35 GiB 可用，磁盘空间不是首要阻塞，峰值 RAM 和转换时间才是。

**结论：10K 格式基线已通过，浏览器增强验收待完成。** 10K SH3 converter、逐值属性审计和 validator 已通过；WebGPU 同相机 full/DC 与 CPU/WGSL fixture 当前受 `Target crashed` 阻塞。完整 2.83M 仍需按 250K -> 全量逐级验证，必要时先优化内存表示与构树成本。

## 4. 最终决策表

| 格式 | 可信 PLY 工具 | 真正生成研究中的 streaming 形态 | 2.83M 完整数据判断 | 当前分级 | 实验准入 |
| --- | --- | --- | --- | --- | --- |
| Spark RAD | 官方 `build-lod` | 是，须 LoD + `--rad-chunked`/paged RAD | 设计上可行，未本机实测 | **需小样验证** | 小样通过后进入同源端到端实验 |
| SOG Streaming | 官方 `splat-transform 2.5.2` | 是，须多级 LOD + `lod-meta.json`，单 `.sog` 不算 | 官方面向数千万，未本机实测 | **需小样验证** | 小样通过后进入同源端到端实验 |
| XGRIDS LCC2 | 未发现公开 writer/tiler | 未能从统一 PLY 复现 | 无法判断 | **当前不可复现** | 仅字段分析与原生样本实验 |
| Cesium 3D Tiles 3DGS | 未发现公开本地或明确云端 PLY tiler | 官方原生资产是，但统一 PLY 链路不是 | 无法判断 | **当前不可复现** | 仅字段/标准分析与原生 tileset 实验 |
| W3GS | 本地 reference converter | 是，manifest + node/layer/chunk/payload；raw SH3 未压缩 | 10K SH3 格式/属性/conformance 已验证，全量风险未验证 | **10K 有条件通过** | 浏览器增强验收后进入同源实验；SH0 只作消融 |

现阶段可规划的“同源端到端”集合是 **Spark RAD、SOG Streaming、W3GS**，但准入条件是三者使用同一个确定性小样先完成 smoke test。XGRIDS LCC2 与 Cesium 不应为凑齐五列而用人工猜测输出；它们继续保留在字段级比较和各自原生样本运行时实验中，研究结论反而更严谨。

## 5. 建议给 Turing 的实际执行顺序

1. **冻结共同输入。已完成。** 已实现固定 seed 的 SplitMix64 priority bottom-k sampler，生成完整保留 62 个属性的嵌套 10K/250K 子集及 manifest。
2. **W3GS 10K SH3。格式部分已完成。** converter、逐值 SH 审计和 validator 已通过；下一步只处理 WebGPU 增强 smoke 的 `Target crashed`。
3. **SOG 静态探路后再测 streaming。** 经授权安装固定版 `@playcanvas/splat-transform@2.5.2`，先运行 `--version/--help` 和 10K 静态 SOG，以排除 WebGPU backend 问题；随后生成 50%/25% LOD 并输出 `lod-meta.json`，检查 tree、chunk 数、SH 文件和浏览器渐进请求。静态 SOG 成功不等于该步骤通过。
4. **Spark pinned build。** 经授权安装 Rust stable，在本地 commit `82fc4a9...` 上 release build；对 10K 运行 `--quality --max-sh=3 --rad-chunked`，确认 `.rad + .radc`、65,536 chunk 上限行为和 `paged: true` 请求路径。
5. **扩大到 250K。** 三条链路统一记录 wall time、峰值 RSS、临时/最终磁盘、属性阶数、chunk/请求数量和 first-render bytes；先修复工具链问题，再决定是否跑 2.83M。
6. **全量顺序。** 建议 SOG -> Spark -> W3GS。前两者是成熟工具，可先建立规模参考；W3GS 若在 250K 已出现非线性内存/seek 开销，应先优化 converter，不直接硬跑全量。
7. **暂缓两条阻塞链路。** 向 XGRIDS 询问“PLY -> LCC2 whole-scene writer、CLI/API、LoD 参数、许可与 release size”；向 Cesium 询问“是否接受已训练 3DGS PLY 并生成 Gaussian HLOD tileset”。任何云上传必须另行获得用户授权。

## 6. 需授权或补充的内容

- 安装 Rust stable 并编译 Spark `build-lod`；预计数百 MiB 下载、1--3 GiB 安装/构建空间，具体以安装器和 Cargo 输出为准。
- 安装固定版 `@playcanvas/splat-transform@2.5.2`；包本体解压约 39 MiB，连同 native 依赖建议预留 0.1--0.3 GiB。
- 若尝试 XGRIDS，先取得 LCC2 writer 的官方确认、许可证和 asset 大小；当前不建议直接安装 Unity/LCC SDK。
- 若尝试 Cesium ion，先确认 PLY 输入能力、账户配额、服务条款和数据上传许可；当前不应上传 `HuCeZhanTing.ply`。
- 公平性补充：W3GS 已有 raw SH3 profile。正式比较使用 SH3；SH0 只作为降阶消融组。raw float32 与 SOG/RAD 压缩结果的容量差异仍不能直接归因于 contract 设计。
