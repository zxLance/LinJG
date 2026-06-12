# 3DGS Format Demo Inventory

本目录用于把 `../notes` 中的格式分析和可检查的 demo / 样本文件对应起来。清单重点记录“本地真实文件能直接支撑什么结论”，避免论文论述只停留在源码阅读或推断。

## 总览

### W3GS 自有实验平台

| 项目 | 路径 | 当前状态 | 用途 |
| --- | --- | --- | --- |
| W3GS 格式演示数据 | `w3gs-format-sample/scene.w3gs.json` | 已创建，payload 为 placeholder | 展示 W3GS manifest、node tree、ordered layers、chunk table、codec profile 和 runtime hints 的完整连接关系。 |
| W3GS Prototype 0 实验平台 | `w3gs-experiment-platform/index.html` | 已创建，可直接打开 HTML | 在同一模拟场景、相机路径和网络条件下，对比 Full loading、Spatial-only、Progressive-only 和 W3GS scheduling 的加载指标。 |

说明：Prototype 0 暂不渲染真实 3DGS payload，而是验证 W3GS 的 manifest / node / layer / chunk / scheduling 结构是否能支撑可量化实验。后续 Prototype 1 再接真实 Gaussian payload。

### 四种主格式样本

| 主格式 | 样本状态 | 本地 demo / 数据路径 | 对应 notes | 本地解析 / 打开状态 | 直接支撑的结论 |
| --- | --- | --- | --- | --- | --- |
| Spark RAD | 已有完整真实 `.rad` 样本，体积较大 | `spark-learning/rad-streaming-demo.html`；`spark-learning/spark-rad-fullscreen-test.html`；`spark-rad-demo/coit-40m-sh1-lod.rad` | `../notes/format-cases/spark-rad-format-design.md`；`../notes/comparisons/3dgs-format-comparison.md`；`../notes/comparisons/chapter-4-5-case-comparison-draft.md` | HTML 可打开；已直接解析 `.rad` header、global meta 和首个 RADC chunk meta | 可支撑 Spark runtime 分页加载，也可直接支撑真实 chunk table、property encoding 及 `child_count/child_start` 字段结论 |
| XGRIDS LCC2 | 已有真实 `.lcc2` 索引样本；外部 `data/3dgs/*.sog` payload 未随样本保存 | `qiyu-lcc2-demo/data/K1-LuoJiaShiYanShi.lcc2` | `../notes/format-cases/xgrids-lcc2-format-design.md`；`../notes/comparisons/3dgs-format-comparison.md`；`../notes/comparisons/chapter-4-5-case-comparison-draft.md` | `.lcc2` 可作为 JSON 解析；因缺少 `data/3dgs` payload，不能完整渲染 | 直接支撑 `.lcc2` 是 JSON 索引、`root.splatFiles` 引用外部高斯文件、节点通过 `data.3dgs.name/start/count` 指向数据段，且内部节点也可以索引 `data.3dgs` |
| PlayCanvas / SuperSplat SOG Streaming | 已有真实 streaming 样本，引用文件齐全但体积偏大 | `playcanvas-roman-parish-lod/lod-meta.json` | `../notes/format-cases/playcanvas-sog-streaming-lod.md`；`../notes/comparisons/3dgs-format-comparison.md`；`../notes/comparisons/chapter-4-5-case-comparison-draft.md` | `lod-meta.json` 和每个 `meta.json` 可解析；`download-summary.json` 显示 referenced files 无缺失 | 直接支撑 `lod-meta.json` 作为入口、`filenames` 指向多个 SOG chunk、octree leaf 的 `lods.file/offset/count` 指向 chunk 内数据段、SOG 属性拆成 `means/scales/quats/sh0` 等 WebP 文件 |
| Cesium 3D Tiles Gaussian Splat | 已有真实 Cesium ion 公开 asset 的小型抽样 | `cesium-3dgs-lod-microsoft-sh0/data/tileset.json` | `../notes/format-cases/cesium-3dtiles-gaussian-splat-lod.md`；`../notes/comparisons/3dgs-format-comparison.md`；`../notes/comparisons/chapter-4-5-case-comparison-draft.md` | `tileset.json` 和 GLB summary 可解析；`demo/viewer.html` 可走本地 HTTP 查看样本 | 直接支撑 `tileset.json + .glb` 组织方式、`content.uri` 可指向 GLB 或外部 tileset、`refine: REPLACE`、GLB 使用 `KHR_gaussian_splatting` 与 `KHR_gaussian_splatting_compression_spz_2` |

## 样本细节

### Spark RAD

- 本地文件：`spark-learning/rad-streaming-demo.html`、`spark-learning/spark-rad-fullscreen-test.html`、`spark-learning/notes.md`、`spark-rad-demo/coit-40m-sh1-lod.rad`。
- HTML 中使用的远程 RAD URL：`https://storage.googleapis.com/forge-dev-public/asundqui/rad/260217/coit-40m-sh1-lod.rad`。
- HEAD 探测结果：`Content-Length = 1,280,517,688 bytes`，`Accept-Ranges = bytes`，`Last-Modified = Wed, 18 Feb 2026 04:09:51 GMT`。
- 当前处理：该 RAD 约 1.19 GiB，已经保存到 `spark-rad-demo/`，但不建议作为普通 Git blob 提交。
- 可直接支撑：`paged: true` 会让 Spark 从 RAD URL 做分页流式加载，HTML 还包装了 `window.fetch` 用于观察 `.rad` 的 Range 请求。
- 本地直接解析结果：`RAD0`、version 1、50,937,127 splats、`lodTree = true`、`chunkSize = 65536`、778 chunks；chunk ranges 连续覆盖 `allChunkBytes = 1,280,467,288`，加 50,400-byte header/meta 后与实际文件大小一致；首个 `RADC` chunk 含 `center`、`alpha`、`rgb`、`scales`、`orientation`、`sh1`、`child_count`、`child_start`，属性列均标记为 gzip 压缩。

推荐下一步候选：

| 候选 | 来源 | 大小估计 | 许可证 / 来源说明 | 建议动作 |
| --- | --- | --- | --- | --- |
| `coit-40m-sh1-lod.rad` | Spark 学习 HTML 中使用的公开 Google Cloud URL | 1,280,517,688 bytes | 公开演示资源；具体资产许可证未在本地记录 | 已保存完整本地副本；建议只用于本地验证，不作为普通 Git blob 推送 |
| `robot-head.spz` -> 本地生成 RAD | `https://github.com/sparkjsdev/assets/blob/main/splats/robot-head.spz` | SPZ 1,153,152 bytes；生成 RAD 大小待测 | Spark 官方 assets 仓库；assets 仓库页面未显示明确许可证，Spark 主仓库为 MIT | 用 Spark `build-lod` 从小 SPZ 生成一个可公开复现实验的 RAD；生成物应标注“由官方 SPZ 经 Spark 工具链派生”，不要冒充官方 RAD |
| Spark LoD 官方文档流程 | `https://sparkjs.dev/docs/lod-getting-started/` | 无下载 | 官方文档 | 作为论文引用补充：说明 `.rad` 可由 `build-lod` 生成，`paged: true` 用于 streaming |

### XGRIDS LCC2

- 本地文件：`qiyu-lcc2-demo/data/K1-LuoJiaShiYanShi.lcc2`，约 76.8 KiB。
- 关联信息文件：`qiyu-lcc2-demo/data/info/report.json`、`poses.json`、`thumb.jpg`。
- `.lcc2` 顶层实测字段包括：`version`、`name`、`epsg`、`totalSplats`、`lodSplats`、`totalLevels`、`splatType`、`root`、`renderingHints`。
- 实测数值：`version = 0.0.3`，`totalSplats = 3854189`，`totalLevels = 4`，`lodSplats = [2060455, 1027012, 511766, 254956]`。
- `root.splatFiles` 有 9 个条目，示例：`data/3dgs/0_0.sog`、`data/3dgs/0_9_0.sog`。
- 本地递归统计：66 个 node；65 个 node 有 `data.3dgs`；43 个非叶子 node 同时有 `childNum > 0` 和 `data.3dgs`。
- 关键证据样例：`id = 0_0`，`childNum = 1`，`data.3dgs = { name: 0, start: 0, count: 2827 }`。

可直接支撑：

- `.lcc2` 本身是 JSON 场景索引。
- 真实高斯 payload 通过 `root.splatFiles` 外挂到 `data/3dgs/*.sog`。
- `data.3dgs.name/start/count` 是节点到真实高斯数据段的索引。
- 非叶子节点也可以索引 `data.3dgs`；这正是 notes 中“内部节点也可以索引 data.3dgs”的结论。

限制：

- 本目录没有保存 `data/3dgs/*.sog` payload，因此不能验证每个 `count` 对应的实际 splat 编码，也不能完整打开渲染。

### PlayCanvas / SuperSplat SOG Streaming

- 本地入口：`playcanvas-roman-parish-lod/lod-meta.json`。
- 来源记录：`https://code.playcanvas.com/examples_data/example_roman_parish_02/lod-meta.json`。
- `download-summary.json` 记录：`lodLevels = 7`，`manifestFilenames = 131`，`expectedReferencedFiles = 788`，`missingReferencedFiles = 0`，`totalMiB = 777.02`。
- `lod-meta.json` 实测：`filenames` 指向多个 `*/meta.json`，另有 `environment/environment.sog`。
- octree 统计：约 11,095 个 tree node；5,548 个 leaf 带 `lods`；`lods` 引用约 37,725 条；最大 LOD 编号为 6。
- 一个 leaf 的 `lods` 示例包含：`0: { file: 0, offset: 0, count: 81 }`、`1: { file: 2, offset: 0, count: 27 }`、`2: { file: 3, offset: 0, count: 11 }` 等。
- 单个 chunk 示例：`playcanvas-roman-parish-lod/0_0/meta.json` 显示 `count = 524881`，属性文件包括 `means_l.webp`、`means_u.webp`、`scales.webp`、`quats.webp`、`sh0.webp`。

可直接支撑：

- SOG Streaming 的入口不是单个 `.sog`，而是 `lod-meta.json` manifest。
- manifest 的 `filenames` 将逻辑 LOD/chunk 引用映射到多个 SOG meta 文件。
- octree leaf 通过 `lods.file/offset/count` 指向 chunk 文件中的不同数据段。
- SOG payload 将高斯属性拆成 WebP 纹理/图像文件，meta 描述解码范围和 codebook。

限制：

- 当前样本体积 777.02 MiB，已经超过轻量 demo 的理想范围。后续最好补一个更小的官方 streaming 样本或裁剪样本，只用于论文证据摘录。

### Cesium 3D Tiles Gaussian Splat

- 本地入口：`cesium-3dgs-lod-microsoft-sh0/data/tileset.json`。
- 来源记录：Cesium ion public asset `4547222`，URL 为 `https://assets.ion.cesium.com/us-east-1/4547222/LOD_3DT_Microsoft_SH0/tileset.json?v=2`。
- 本地抽样总大小：约 3.86 MiB。
- `endpoint-summary.json` 记录：`asset.version = 1.0`，`rootGeometricError = 93.29574584960938`，`rootRefine = REPLACE`，`rootHasContent = true`，`rootChildren = 1`。
- 根 `tileset.json` 实测：root `content.uri = tile_0.glb`，子 tile `content.uri = ts_0/tileset.json`，`extensionsUsed` 包含 `3DTILES_content_gltf`，扩展中声明 glTF 使用 `KHR_gaussian_splatting` 与 `KHR_gaussian_splatting_compression_spz_2`。
- `sample-glb-summary.json` 中三个 GLB 抽样：
  - `tile_0.glb`：397,300 bytes，22,178 points。
  - `ts_0/tile_1.glb`：1,860,776 bytes，103,522 points。
  - `ts_0/ts_1/ts_2/tile_2.glb`：601,152 bytes，33,108 points。
- `tile_0-gltf-summary.json` 显示 GLB magic 为 `glTF`，primitive mode 为 `0`，attributes 包括 `POSITION`、`COLOR_0`、`KHR_gaussian_splatting:SCALE`、`KHR_gaussian_splatting:ROTATION`。

可直接支撑：

- Cesium 3DGS 复用 3D Tiles 的 `tileset.json` 作为空间层级入口。
- tile content 可以是 `.glb`，也可以是外部 `tileset.json`，遍历时必须递归解析 URI。
- GLB 中 Gaussian payload 以 glTF extension 标注，且样本使用 SPZ 压缩扩展。
- `refine: REPLACE` 可作为本样本中 HLOD 替换策略的实证。

限制：

- 本目录保存的是小型抽样链路，不是完整 Cesium ion asset。它足够支撑格式结构与扩展字段，不足以分析完整生产管线和全场景调度统计。

## 缺口与推荐动作

| 缺口 | 推荐动作 |
| --- | --- |
| Spark RAD 样本过大且资产许可未明确 | 已有 1.19 GiB 完整本地样本，无需再次下载；字段分析直接使用当前副本。性能实验优先用许可清楚的小 SPZ 经 `build-lod` 生成派生 RAD。 |
| LCC2 缺 `data/3dgs` payload | 如需要验证渲染和 payload 编码，回到样本来源补齐 `data/3dgs/*.sog`；如果只论证 `.lcc2` 索引结构，当前样本已经足够。 |
| PlayCanvas 样本过大 | 保留当前完整样本作为强证据；另找或裁剪一个小型 streaming manifest 作为论文附录级样本。 |
| Cesium 仅有抽样链路 | 若论文要讨论全 asset HLOD 统计，需要补完整 tileset 遍历结果；若只讨论格式容器和 Gaussian glTF extension，当前样本足够。 |
