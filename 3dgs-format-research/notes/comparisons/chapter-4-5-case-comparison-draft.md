# 第 4-5 章素材草稿：四种 Web 流式 3DGS 格式案例与比较

本文将 Spark RAD、XGRIDS LCC2、PlayCanvas / SuperSplat SOG Streaming 和 Cesium 3D Tiles Gaussian Splat 作为四个主案例。四者共同面对的问题是：如何让大规模 3D Gaussian Splatting 数据在浏览器中可压缩、可索引、可渐进显示，并能根据相机视角按需细化。它们的差异不只是文件后缀不同，而是分别代表了四类格式设计范式：渲染器专用分页容器、大场景空间 LoD 索引包、Web-native 压缩流式交付格式，以及地理空间标准 HLOD 容器。

## 4. Case Studies

### 4.1 Spark RAD

#### 格式定位

Spark RAD 是面向 Spark runtime 的二进制分页容器。它不是训练输出交换格式，而是从普通 3DGS PLY 转换而来的运行时交付格式，重点服务于浏览器中的随机访问、分块下载、LoD 展开和 GPU 上传。

#### 核心文件结构

RAD 文件由全局 header、全局 JSON meta 和一个或多个 RADC chunk 组成。全局 meta 记录 splat 总数、球谐阶数、是否包含 LoD 树、chunkSize 以及每个 chunk 的 offset/bytes。每个 RADC chunk 内部再用 chunk JSON meta 描述属性列的位置和编码方式，payload 则存放 center、alpha、rgb、scales、orientation、SH 以及 LoD 树关系列。

RAD 的关键不在于把 PLY 简单二进制化，而是把离线生成的 LoD 树摊平成一个高斯节点数组，并把树关系压成 `child_count` 和 `child_start` 两列。父节点本身也是一个可渲染的粗层高斯，而不是空目录节点。

#### LoD/Streaming 组织

RAD 的 LoD 树是 splat 级合并树。构建流程会把相近、相似的原始高斯合并为父高斯，经过裁剪和重排后形成适合 chunk 访问的数组顺序。运行时根据当前视角决定某个粗高斯是否需要展开到子高斯；展开时通过 `child_start + child_count` 得到连续子节点，再映射到对应 chunk。

这种组织使 LoD 关系和高斯属性在同一个二进制容器内紧密绑定，适合精细粒度的渐进显示。

#### 浏览器加载路径

浏览器首先读取 RAD header 和全局 meta，得到 chunk 表和格式参数。随后 Spark runtime 根据相机进行 LoD 遍历，计算需要访问的节点和 chunk。如果 chunk 尚未加载，则通过 HTTP Range 或外部 `.radc` 文件请求对应字节段；解码属性列后上传到 GPU。首屏可以先显示粗层高斯，随后在视角靠近时加载更细节点。

#### 设计取舍

RAD 的优势是运行时效率高、chunk 粒度固定、树关系紧凑，适合与 Spark 自有渲染管线深度集成。代价是格式较专用，LoD 构建和属性编码都强依赖 Spark 工具链；其空间语义和标准互操作能力弱于 3D Tiles 或 glTF 生态。

#### 可写入论文的关键句

RAD 将 3DGS 流式问题转化为“已排序的高斯 LoD 节点数组 + 可随机访问的二进制 chunk”问题，其核心贡献在于把父子层级压缩为 `child_count/child_start` 属性列，使浏览器能够在渲染器内部以较低元数据成本完成渐进细化。

### 4.2 XGRIDS LCC2

#### 格式定位

LCC2 是面向大场景扫描、重建和数字孪生应用的空间 LoD 索引格式。它更像一个场景组织包，而不是单一高斯压缩编码。`.lcc2` 负责描述空间层级、包围盒、层级统计和数据索引，真实 3DGS payload 则位于 `data/3dgs/*` 中。

#### 核心文件结构

一个典型 LCC2 资产由入口 `.lcc2` JSON 文件和外部数据目录组成。顶层字段包括 version、name、splatType、totalSplats、totalLevels、lodSplats、splatFiles 和 root。`splatFiles` 记录真实高斯文件列表，节点通过 `data.3dgs.name/start/count` 指向其中某个文件的某段高斯数据。

需要特别强调的是：LCC2 不是只有叶子节点索引高斯数据，而是每个 Node 都可以索引该层级的 3DGS 数据。Node 同时承担空间索引单元和可渲染 LoD 单元的角色。

#### LoD/Streaming 组织

LCC2 的 LoD 树本质是空间 Node 层级树。每个 Node 具有 boundingBox、data、childNum 和 child。浅层节点可以提供大范围低精度高斯，深层子节点提供更小空间范围或更高精度的数据。`lodSplats` 用于记录各层级的高斯数量统计，说明数据按层级组织，而不是只在最底层保存。

浏览器可以先加载 root 或浅层可见节点的数据；当相机靠近某个空间块时，再加载其 child Node 对应的数据，并用更细层级替换或覆盖该区域的粗层表示。

#### 浏览器加载路径

运行时首先请求 `.lcc2` 文件并解析 JSON 树，建立 id 到节点、节点到子节点、节点到数据段的内部索引。每帧根据相机、视锥和节点 boundingBox 判断哪些节点可见、哪些节点需要展开。对需要加载的节点，根据 `name/start/count` 定位到 `splatFiles` 中的高斯文件及数据范围，完成下载、解码和 GPU 上传。

#### 设计取舍

LCC2 的优势是索引可读、空间层级明确、payload 与场景结构解耦，适合大场景资产管理和生产工具链。其代价是初始 JSON 树可能较大，运行时需要把可读索引转换为高效内部结构；此外，公开资料可确认结果格式，但具体 LoD 生成算法和误差度量仍依赖 XGRIDS 工具链，论文中需要谨慎表述。

#### 可写入论文的关键句

LCC2 的关键设计不是重新定义高斯属性编码，而是用 `.lcc2` JSON 将大场景组织成“每个 Node 可索引本层级 3DGS 数据”的空间 LoD 树，从而使远处粗层显示、近处子节点替换成为浏览器流式加载的基础机制。

### 4.3 PlayCanvas / SuperSplat SOG Streaming

#### 格式定位

PlayCanvas / SuperSplat 方案由两层组成：SOG 是面向 Web 分发的压缩高斯格式，Streaming LOD 则通过 `lod-meta.json` 组织多个 SOG chunk，实现大场景渐进下载和相机驱动的 LoD 切换。它服务于 PlayCanvas Engine 的 GSplat 资源体系，具有明显的 Web-native 工程导向。

#### 核心文件结构

普通 SOG 将 Gaussian 属性拆成多张 8-bit 图像或纹理化数据，例如 means、scales、quats、sh0 和可选高阶 SH 数据，并用 meta 描述解码关系；打包形态可以是单个 `.sog`。Streaming LOD 的入口文件必须是 `lod-meta.json`，其中记录 lodLevels、filenames、可选 environment 以及一棵空间 tree。真实数据分布在多个 SOG chunk 中。

在 `lod-meta.json` 中，octree 的叶子节点带有 `lods` 字段。每个 LOD 项通过 `file/offset/count` 指向某个 SOG chunk 中的一段高斯数据，因此多个空间节点可以共享同一个 chunk 文件。

#### LoD/Streaming 组织

SOG Streaming 的 LoD 树是 octree manifest。manifest 保留空间层级，运行时通常将含有 `lods` 的叶子节点抽取为扁平数组，用于快速计算每个叶子的目标 LOD。一个叶子可同时记录多个质量层级：近处使用 LOD 0 等高质量数据，远处使用更高编号的低质量数据。

其替换粒度不是单个高斯，也不是 3D Tiles tile，而是 octree leaf 在不同 LOD 下的 SOG 数据范围。

#### 浏览器加载路径

PlayCanvas 的资源加载器根据 URL 判断 parser：`.sog` 走 SOG bundle，`meta.json` 走普通 SOG，`lod-meta.json` 走 GSplatOctreeParser。加载 streaming 场景时，浏览器先下载 manifest，解析 filenames 和 tree，建立叶子节点、bounding box 和 LOD 引用。渲染时根据相机到叶子包围盒的距离、FOV、lodBaseDistance 和 lodMultiplier 计算目标 LOD；若目标 chunk 尚未加载，则异步请求。新 LOD 到达前可继续显示已有粗层，以避免空洞。

#### 设计取舍

SOG 的优势是充分利用浏览器图片/纹理通道和 WebP 等成熟压缩方式，适合 CDN 分发和 GPU 上传。Streaming manifest 将空间节点和 chunk 数据范围解耦，减少小文件数量，并通过引用计数、cooldown 等机制控制内存波动。代价是压缩通常有损，格式和运行时深度绑定 PlayCanvas；同时，octree leaf 多 LOD 方案更偏 Web 展示和引擎交付，而不是地理空间标准互操作。

#### 可写入论文的关键句

PlayCanvas / SuperSplat SOG Streaming 将 3DGS Web 分发拆成“纹理化压缩 payload + octree LOD manifest”两部分，通过 leaf 级 `file/offset/count` 索引实现渐进下载，使浏览器能够在保持已有粗层显示的同时异步切换到更高质量 SOG chunk。

### 4.4 Cesium 3D Tiles Gaussian Splat

#### 格式定位

Cesium 方案不是为 3DGS 单独设计一个私有 manifest，而是把 Gaussian Splat 作为 tile content 纳入 3D Tiles 和 glTF 扩展体系。3D Tiles 负责空间索引、地理定位、HLOD、缓存和调度；GLB 负责单个 tile 的资产容器；`KHR_gaussian_splatting` 负责高斯语义；SPZ 压缩扩展负责降低 payload 体积。

#### 核心文件结构

入口文件是 `tileset.json`。其中 root 和 children 共同描述 tile tree，每个 tile 包含 boundingVolume、geometricError、refine、transform、content.uri 等字段。`content.uri` 可以指向 `.glb`，也可以指向外部子 `tileset.json`。单个 GLB 内部用 glTF mesh primitive 的 POINTS 表达高斯点，并通过 `KHR_gaussian_splatting` 标注 POSITION、ROTATION、SCALE、COLOR 或 SH/OPACITY 等语义；压缩路径下，SPZ payload 存在 bufferView 中。

#### LoD/Streaming 组织

Cesium 的 LoD 树是标准 3D Tiles HLOD tile tree。父 tile 可保存粗层 GLB 内容，子 tile 保存更细空间范围或更高精度内容；也存在只作为分组或中转、没有直接 GLB content 的节点。运行时基于 geometricError 和 screen-space error 判断是否 refine 到子 tile。

`refine` 字段决定粗细层关系：`REPLACE` 表示子 tile 足够精细后替换父 tile，`ADD` 表示子 tile 与父 tile 叠加。3DGS LOD 场景通常更接近 HLOD：先显示父 tile 粗结果，再按规则加载并切换子 tile。

#### 浏览器加载路径

CesiumJS 首先加载 `tileset.json` 并建立 tile tree。每帧根据相机、boundingVolume、geometricError 和 maximumScreenSpaceError 选择需要渲染或细化的 tile。被选中的 tile 会触发 `content.uri` 请求；下载 GLB 后，运行时检查 glTF Gaussian 扩展，解码 SPZ 或相关属性数据，建立 Gaussian 渲染资源，并按照 3D Tiles refinement 与缓存预算管理父子 tile 的显示和卸载。

#### 设计取舍

Cesium 方案的优势是标准化程度高，能够复用 3D Tiles 的地理坐标、HLOD 调度、视锥裁剪、缓存策略和调试工具，也能借助 glTF 扩展获得更好的互操作前景。代价是系统层次更复杂，tile 生产管线和 glTF Gaussian 扩展支持仍在快速演进；对于非地理空间的普通 Web 展示而言，3D Tiles 的坐标和 HLOD 框架可能显得较重。

#### 可写入论文的关键句

Cesium 3D Tiles Gaussian Splat 的核心价值在于将 3DGS payload 放入既有地理空间 HLOD 标准中，使浏览器加载问题从“如何自定义 splat streaming”转化为“如何让 Gaussian GLB tile 参与 3D Tiles traversal、SSE refinement 和缓存管理”。

## 5. Comparative Analysis

### 5.1 横向比较表

| 比较维度 | Spark RAD | XGRIDS LCC2 | PlayCanvas / SuperSplat SOG Streaming | Cesium 3D Tiles Gaussian Splat |
| --- | --- | --- | --- | --- |
| 容器形态 | `.rad` 单文件或 `.rad + .radc` 二进制分页容器 | `.lcc2` JSON 索引 + `data/3dgs/*` payload | `lod-meta.json` + 多个 `.sog` chunk | `tileset.json` + 子 tileset + `.glb` |
| LoD 树形态 | 高斯点合并树 | 空间 Node 层级树 | octree manifest，叶子挂多级 LOD | 3D Tiles HLOD tile tree |
| 数据索引方式 | `child_count/child_start` 指向连续子节点，再映射 chunk | 每个 Node 可用 `data.3dgs.name/start/count` 索引本层级数据 | leaf 的 `lods` 用 `file/offset/count` 指向 SOG chunk 区间 | tile 的 `content.uri` 指向 GLB 或外部 tileset |
| 粗细层替换策略 | 父高斯展开为子高斯 | 深层 Node 数据替换对应空间区域的浅层 Node 数据 | 同一 leaf 在不同 LOD 数据范围之间切换 | 按 `REPLACE` 或 `ADD` refinement 处理父子 tile |
| Web 加载方式 | header/meta 后按需 Range fetch chunk 或请求 `.radc` | 先取 JSON 树，再按 Node 数据段加载外部高斯文件 | 先取 manifest，再按距离请求 SOG chunk | Cesium traversal 根据 SSE 请求 tile content |
| 标准化程度 | 渲染器专用 | 工具链/产品格式，公开度有限 | PlayCanvas 生态格式 | 最高，复用 3D Tiles、glTF、SPZ 扩展体系 |
| 适用场景 | 自有 Web viewer、高效渐进渲染 | 大场景扫描、数字孪生、资产管理 | Web 展示、编辑发布、CDN 分发 | GIS、城市级场景、地理空间数字孪生 |

### 5.2 容器形态：单体容器、索引包、manifest 与标准 tileset

四种格式首先体现为容器形态的差异。RAD 把属性、LoD 树和 chunk 表压入同一运行时容器，追求加载路径短和渲染器友好。LCC2 把空间树留在 JSON 中，把高斯 payload 放在外部文件中，追求大场景管理和可检查性。SOG Streaming 则将压缩 payload 和 streaming manifest 分开，用 `lod-meta.json` 统一管理多个 SOG chunk。Cesium 采用标准 `tileset.json + GLB` 分层容器，把 3DGS 放进地理空间资产生态。

因此，容器设计从“渲染器私有高效文件”到“标准生态组合系统”形成了一条光谱。

### 5.3 LoD 树形态：从高斯合并树到 HLOD tile tree

RAD 的 LoD 单元是高斯节点，父节点就是粗层可渲染 splat；LCC2 的 LoD 单元是空间 Node，每个 Node 可以索引该层级高斯数据；SOG Streaming 的 LoD 单元是 octree leaf 的多质量版本；Cesium 的 LoD 单元是 tile，父子 tile 通过 geometricError 和 refinement 组成 HLOD。

这说明 3DGS LoD 并不存在唯一粒度。格式设计必须先回答：LoD 是发生在单个 Gaussian 聚合层面、空间块层面、leaf 多版本层面，还是标准 tile 层面。

### 5.4 数据索引方式：连续数组、数据段、chunk 区间与 URI

RAD 依赖预先重排后的连续数组，索引极紧凑，但更依赖离线构建。LCC2 和 SOG Streaming 都使用 `start/count` 类型的数据段索引，不过 LCC2 的索引挂在空间 Node 上，SOG 的索引挂在 octree leaf 的各 LOD 项上。Cesium 使用 URI 作为 tile content 引用，粒度更粗，但与 Web 资源、缓存和标准工具链天然兼容。

这一维度反映了“索引紧凑性”和“生态可组合性”的取舍。

### 5.5 粗细层替换策略：展开、替换、切换与 refinement

RAD 更像从父高斯展开到子高斯；LCC2 是用深层 Node 数据替换同一区域的浅层表示；SOG Streaming 是同一 leaf 在不同质量 chunk 区间之间切换；Cesium 则把替换或叠加交给 3D Tiles 的 `REPLACE/ADD` refinement 规则。

论文中可以将其总结为四类策略：splat-level expansion、node-level replacement、leaf-level LOD switching 和 tile-level HLOD refinement。

### 5.6 Web 加载方式：range fetch 与 runtime traversal

RAD 的加载路径最贴近字节随机访问：读 header 后按需 Range fetch chunk。LCC2 先解析完整或主要 JSON 树，再按 Node 引用加载数据段。SOG Streaming 先解析 manifest 并扁平化 leaf，再以 chunk 引用计数管理加载和卸载。Cesium 则由 3D Tiles traversal 统一处理可见性、SSE、请求优先级和缓存预算。

浏览器端真正需要的不是“能下载文件”，而是格式中是否包含足够的信息让 runtime 判断：何时加载、加载多少、加载后替换谁、内存不足时释放谁。

### 5.7 标准化程度与适用边界

RAD 和 SOG 更接近特定 Web runtime 的高效工程格式，适合快速展示和引擎集成。LCC2 处在产品化大场景格式位置，强调空间组织和工具链。Cesium 方案标准化程度最高，适合 GIS 和城市级地理空间场景，但系统复杂度也最高。

由此可见，3DGS 流式格式不存在单一最优解。更合理的判断标准是应用边界：普通 Web 展示更重视压缩和首屏速度，大场景扫描更重视空间层级和资产管理，地理空间数字孪生更重视标准 HLOD、坐标系统和跨平台调度。

## 6. 还缺什么证据 / 引用 / 实验

1. 官方引用补全：需要为四个主案例分别补正式来源，包括 Spark RAD 源码/文档、XGRIDS LCC2 白皮书与 SDK、PlayCanvas SOG 与 Streaming LOD 文档、Cesium 3D Tiles Gaussian Splat 博文/教程、glTF `KHR_gaussian_splatting` 和 OGC 3D Tiles 规范。
2. 真实样本证据：需要为 LCC2 截取若干真实 Node，证明内部节点也含 `data.3dgs.name/start/count`；为 Cesium 截取真实 `tileset.json` 和 GLB extension 结构；为 SOG Streaming 截取 `lod-meta.json` leaf 的 `lods` 结构；为 RAD 截取 global meta 和 chunk properties。
3. 元数据复杂度实验：统计四类入口文件的节点数量、字段数量、入口文件大小、平均每节点索引字段数，以及首屏所需请求数量。
4. 加载路径小实验：用同一或相近场景记录首屏加载数据量、首次可见时间、视角靠近后的追加请求数、粗细层切换时是否出现空洞或重复绘制。
5. 替换策略验证：需要分别确认 RAD runtime 的父子节点显示策略、LCC Web SDK 的浅层/深层 Node 替换策略、PlayCanvas 的 underfill/cooldown 行为，以及 Cesium 在 3DGS tileset 中常用 `REPLACE` 还是 `ADD`。
6. 生成流程边界：RAD 和 PlayCanvas 工具链相对可追踪；LCC2 与 Cesium ion/tiler 的具体 LoD 生成算法公开度有限，论文中需要补引用或明确写成“结果格式可确认，生成算法未完全公开”。
7. 标准化状态：`KHR_gaussian_splatting`、SPZ 压缩扩展、CesiumJS 支持路径仍可能变化，需要在定稿前核对当前版本和规范状态。
