# 四种 3D 高斯数据格式对比

这份文档对比四种已经整理过的 3D Gaussian Splatting 数据格式 / 加载体系：

- Spark RAD
- XGRIDS LCC2
- PlayCanvas / SuperSplat SOG + Streaming LOD
- Cesium 3D Gaussian Splat + 3D Tiles LOD

## 1. 一句话总览

| 格式 / 体系 | 一句话理解 |
| --- | --- |
| Spark RAD | 面向 Spark runtime 的二进制分页容器，把 LoD 高斯节点和属性压进 chunk。 |
| XGRIDS LCC2 | 面向大场景的 JSON 空间 LoD 索引包，每个 Node 可索引该层级高斯数据。 |
| PlayCanvas SOG Streaming | 面向 Web 的图像化压缩高斯格式，用 `lod-meta.json` 管 SOG chunk 和 octree LoD。 |
| Cesium 3D Tiles 3DGS | 把高斯点纳入 3D Tiles HLOD 体系，用 `tileset.json` 管空间层级，用 GLB 存 Gaussian payload。 |

最关键的区别：

```text
RAD:
  LoD 树是高斯点合并树。

LCC2:
  LoD 树是空间 Node 树，每个 Node 可带本层级高斯数据。

SOG Streaming:
  LoD 树是 octree manifest，叶子记录多个 LOD 的 SOG 数据范围。

Cesium 3D Tiles:
  LoD 树是 3D Tiles HLOD，tile 内容是带 Gaussian 扩展的 GLB。
```

## 2. 总体对比表

| 维度 | Spark RAD | XGRIDS LCC2 | PlayCanvas SOG Streaming | Cesium 3D Tiles 3DGS |
| --- | --- | --- | --- | --- |
| 文件形态 | `.rad` 单文件或 `.rad + .radc` chunk | `.lcc2` JSON + `data/3dgs/*` | `lod-meta.json` + 多个 `.sog` chunk | `tileset.json` + 子 tileset + `.glb` |
| 核心入口 | RAD header | `.lcc2` | `lod-meta.json` | `tileset.json` |
| 数据本体 | RAD chunk 中的属性列 | 外部 3DGS 文件段 | SOG 图像 / 纹理化属性 | GLB 中的 Gaussian point primitive |
| LoD 树形态 | 高斯点合并树 | 空间 Node 层级树 | octree leaf + 多级 LOD 引用 | 3D Tiles HLOD tile tree |
| 节点是否可渲染 | 父节点本身是合并高斯点 | 每个 Node 可索引本层级高斯数据 | leaf 记录不同 LOD 数据范围 | tile 可有自己的 GLB 内容 |
| 数据索引方式 | `child_count` / `child_start` + chunk index | `data.3dgs.name/start/count` | `fileIndex/offset/count` | `content.uri` |
| 加载粒度 | 固定 chunk，默认 65536 splats | Node 引用的数据段 | SOG chunk | 3D Tiles tile |
| 浏览器调度 | 相机驱动 LoD 遍历 + range fetch | 相机驱动 Node 展开和替换 | 相机距离驱动 leaf LOD 切换 | Cesium tile refinement |
| 适用侧重 | Spark 自有 Web 渲染管线 | 大场景、扫描、数字孪生 | PlayCanvas Web 交付 | 地理空间、全球坐标、标准生态 |

## 3. LoD 树对比

| 格式 / 体系 | LoD 树本质 | 粗层数据在哪里 | 细化方式 |
| --- | --- | --- | --- |
| RAD | splat 级合并树 | 父 splat 本身 | 根据相机展开 child splats |
| LCC2 | 空间块层级树 | 每个 Node 的 `data.3dgs` | 加载更深 child Node 的数据 |
| SOG Streaming | octree leaf 多 LOD 引用 | leaf 的低质量 LOD 数据段 | 同一 leaf 切换更高质量 LOD |
| Cesium 3D Tiles | tile HLOD 树 | 父 tile 的 GLB content | Cesium refinement 加载子 tile |

四者都叫 LoD，但粒度不同：

```text
RAD:
  LoD 粒度接近单个高斯点或合并高斯点。

LCC2:
  LoD 粒度是空间 Node。

SOG Streaming:
  LoD 粒度是 octree leaf 的不同质量版本。

Cesium:
  LoD 粒度是 3D Tiles tile。
```

## 4. 文件内部结构对比

### 4.1 RAD：二进制容器 + JSON meta + 属性列

RAD 文件大致是：

```text
RAD_MAGIC
global JSON meta
RADC chunk 0
RADC chunk 1
...
```

每个 chunk 内部：

```text
RADC_MAGIC
chunk JSON meta
payloadBytes
center payload
alpha payload
rgb payload
scales payload
orientation payload
sh payload
child_count payload
child_start payload
```

特点是运行时友好，树关系和高斯属性都已经压成二进制列。

### 4.2 LCC2：JSON 空间树 + 外部高斯数据

LCC2 入口是 `.lcc2`：

```text
scene.lcc2
data/3dgs/*
data/mesh/*
```

`.lcc2` 负责：

```text
root / child tree
boundingBox
data.3dgs.name/start/count
splatFiles
lodSplats
```

特点是可读、可维护，适合大场景资产管理。

### 4.3 SOG Streaming：图像化高斯属性 + LOD manifest

普通 SOG 把高斯属性拆成图像 / 纹理形式，用 meta 描述解码。

Streaming LOD 再加：

```text
lod-meta.json
chunk_000.sog
chunk_001.sog
...
```

`lod-meta.json` 负责空间 octree、leaf bound、每个 leaf 的多 LOD 数据引用。

### 4.4 Cesium：3D Tiles 树 + GLB Gaussian payload

Cesium 使用标准 3D Tiles 入口：

```text
tileset.json
```

每个 tile 的内容是：

```text
content.uri -> .glb 或外部 tileset.json
```

GLB 内用：

```text
KHR_gaussian_splatting
KHR_gaussian_splatting_compression_spz_2
```

来表达高斯语义和压缩数据。

## 5. 生成流程对比

| 格式 / 体系 | 输入 | 生成流程 |
| --- | --- | --- |
| RAD | 普通 PLY / splat 数据 | `build-lod` 读入 PLY，生成高斯点合并树，重排 chunk，写 RAD。 |
| LCC2 | XGRIDS / LCC Studio 重建数据 | 构建空间 LoD Node 树，为每个节点生成本层级数据索引，导出 `.lcc2 + data/3dgs`。 |
| SOG Streaming | PLY / 多级 LOD PLY | `splat-transform` 生成 SOG，或把多级 LOD 输入打包成 `lod-meta.json + SOG chunks`。 |
| Cesium 3D Tiles | 3DGS reconstruction | Cesium ion / tiler 生成 3D Tiles HLOD 树，将 Gaussian 数据写入 GLB tile。 |

生成算法公开程度也不同：

```text
RAD:
  有源码，可追踪到 BhattLod / TinyLod。

LCC2:
  公开格式，不完整公开具体 LoD 生成算法。

SOG Streaming:
  有 PlayCanvas 工具和运行时源码，LOD 输入/打包机制较清楚。

Cesium:
  公开 3D Tiles 和 glTF 扩展，具体 tiler 生产算法未完全作为格式规范公开。
```

## 6. 浏览器加载对比

### 6.1 RAD

```text
读取 RAD header
  |
  v
根据相机遍历 LoD tree
  |
  v
得到需要的 chunk index
  |
  v
HTTP Range fetch chunk
  |
  v
解码属性列并上传 GPU
```

### 6.2 LCC2

```text
读取 scene.lcc2
  |
  v
解析 Node tree，建立运行时索引
  |
  v
先加载浅层 Node 的 data
  |
  v
相机靠近后加载 child Node 的 data
  |
  v
用更细层级替换粗层级
```

### 6.3 SOG Streaming

```text
读取 lod-meta.json
  |
  v
建立 octree leaf 列表
  |
  v
根据相机距离选择每个 leaf 的目标 LOD
  |
  v
加载对应 SOG chunk 的 offset/count
  |
  v
新 LOD 到达后替换旧 LOD
```

### 6.4 Cesium 3D Tiles

```text
读取 tileset.json
  |
  v
Cesium 构建 tile tree
  |
  v
根据 screen space error / geometricError 选择 tile
  |
  v
加载 tile content GLB
  |
  v
解析 Gaussian glTF extensions
  |
  v
按 3D Tiles refinement 规则替换或叠加
```

## 7. 设计理念对比

| 格式 / 体系 | 设计理念 |
| --- | --- |
| RAD | 为 Spark runtime 定制，优先考虑 chunk 级流式加载和高效二进制解码。 |
| LCC2 | 为大场景组织和工具链维护设计，优先考虑空间层级、可编辑 JSON 索引和跨格式数据引用。 |
| SOG Streaming | 为浏览器高斯点交付设计，优先考虑 SOG 压缩、渐进加载和 PlayCanvas runtime 集成。 |
| Cesium 3D Tiles | 为地理空间标准生态设计，优先复用 3D Tiles 的 HLOD、调度、坐标和缓存能力。 |