# PlayCanvas / SuperSplat SOG 与 Streaming LOD 简明说明

## 1. 一句话结论

SuperSplat 是 PlayCanvas 生态里的高斯点编辑和发布工具；浏览器运行时主要落到 PlayCanvas Engine 的 `gsplat` 资源体系。

PlayCanvas 当前有两层格式：

- `SOG`：面向 Web 分发的压缩高斯点格式。
- `lod-meta.json`：面向大场景的流式 LOD manifest，内部引用多个 SOG chunk，并用 octree 描述空间分块与各 LOD 的数据范围。

它的思想类似 3D Tiles：分块、包围盒、LOD、按需加载。但它不是 Cesium 3D Tiles，也不使用 `tileset.json / geometricError` 那套结构。

## 2. 整体链路

```text
训练/编辑输出
  PLY / compressed PLY / KSPLAT / SPZ / LCC
        |
        v
SplatTransform / SuperSplat Convert
        |
        +--> 普通交付: scene.sog
        |               或 meta.json + *.webp
        |
        +--> 流式交付: lod-meta.json + 多个 SOG chunk
                            |
                            v
                    PlayCanvas GSplatComponent
                            |
                            v
              相机驱动 LOD 选择、加载、替换、卸载
```

## 3. 普通 SOG 文件结构

SOG 的核心设计是：把每个 Gaussian 的属性拆成多张 8-bit 图像，通过 `meta.json` 描述解码方式。

常见未打包目录结构：

```text
scene/
  meta.json
  means_l.webp
  means_u.webp
  scales.webp
  quats.webp
  sh0.webp
  shN_centroids.webp   # 可选，高阶球谐
  shN_labels.webp      # 可选，高阶球谐
```

也可以打成单个 `.sog` 文件。官方规格把 `.sog` 描述为包含上述文件的 ZIP 变体。

关键属性：

- `means_l.webp` / `means_u.webp`：位置的低 8 位和高 8 位。
- `scales.webp`：三轴尺度，通常通过 codebook 解码。
- `quats.webp`：方向四元数的压缩表示。
- `sh0.webp`：基础颜色 DC 分量和 opacity。
- `shN_centroids.webp` / `shN_labels.webp`：可选的高阶球谐，使用 palette / label 压缩。

索引规则很简单：同一个像素 `(x, y)` 在所有属性图里对应同一个 Gaussian。

```text
i = x + y * width
x = i % width
y = floor(i / width)
```

设计重点：

- 用 WebP 等浏览器原生图片通道承载量化数据。
- 文件体积比原始 PLY 小很多，但这是有损压缩。
- 适合 CDN 分发和浏览器快速上传 GPU。
- 属性被组织成纹理后，运行时可以避免把所有数据先还原成巨大 CPU 结构。

## 4. Streaming LOD 文件结构

流式 LOD 的入口文件必须叫：

```text
lod-meta.json
```

典型结构可以理解成：

```text
scene_lod/
  lod-meta.json
  chunk_000.sog
  chunk_001.sog
  chunk_002.sog
  ...
```

从 PlayCanvas Engine 源码看，`lod-meta.json` 至少包含这些概念：

```js
{
  "lodLevels": 5,
  "filenames": [
    "chunk_000.sog",
    "chunk_001.sog"
  ],
  "environment": "environment.sog", // optional
  "tree": {
    "bound": {
      "min": [x, y, z],
      "max": [x, y, z]
    },
    "children": [
      ...
    ]
  }
}
```

树的叶子节点带有 `lods`：

```js
{
  "bound": {
    "min": [x, y, z],
    "max": [x, y, z]
  },
  "lods": {
    "0": { "file": 3, "offset": 0, "count": 120000 },
    "1": { "file": 8, "offset": 0, "count": 35000 },
    "2": { "file": 9, "offset": 0, "count": 9000 }
  }
}
```

含义：

- `tree.bound`：整个场景或节点的 AABB。
- `children`：octree 内部节点。
- `lods`：叶子节点在不同 LOD 下的数据引用。
- `file`：索引到 `filenames`。
- `offset` / `count`：该节点在对应 chunk 内的 Gaussian 区间。

所以它不是“每个节点一个独立文件”这么粗，而是：

```text
octree leaf node
  -> LOD 0: file A, offset/count
  -> LOD 1: file B, offset/count
  -> LOD 2: file C, offset/count
```

多个节点可以共享同一个 chunk 文件，通过不同区间引用其中的数据。

## 5. 文件如何生成

生成工具是 `@playcanvas/splat-transform`。SuperSplat Convert 页面本质上是它的 Web 前端。

安装：

```bash
npm install -g @playcanvas/splat-transform
```

普通 SOG：

```bash
splat-transform source.ply output.sog --filter-nan
```

未打包 SOG：

```bash
splat-transform source.ply output/meta.json --filter-nan
```

Streaming LOD：

```bash
splat-transform \
  lod0.ply -l 0 \
  lod1.ply -l 1 \
  lod2.ply -l 2 \
  lod3.ply -l 3 \
  output/lod-meta.json \
  --filter-nan
```

注意点：

- `lod-meta.json` 这个文件名是格式开关，不能随便改名。
- `LOD 0` 是最高质量，数字越大越粗。
- SplatTransform 可以把多个已生成的 LOD 文件打包成流式结构。
- 官方文档也说明可以先用 decimation 从一个高质量源生成低质量 LOD，再打包。

常用 LOD 输出参数：

```bash
-C, --lod-chunk-count   近似每个 LOD chunk 的 Gaussian 数量，单位 K，默认 512
-X, --lod-chunk-extent  近似 chunk 世界空间大小，默认 16
```

这两个参数控制“数据块多大”和“空间块多大”的平衡。

## 6. LOD 树如何生成和储存

官方文档明确说：SplatTransform 会从多级 LOD 输入构建带 octree 的流式格式，用于 progressive download。

可以把生成过程理解为：

```text
输入多个 LOD 文件
  |
  v
统一空间范围和坐标
  |
  v
按空间位置构建 octree
  |
  v
每个叶子节点记录 AABB
  |
  v
为每个叶子节点写入各 LOD 的 file / offset / count
  |
  v
输出 lod-meta.json + SOG chunk 文件
```

源码里运行时只保留叶子节点用于快速 LOD 计算；构造 `GSplatOctree` 时会递归读取 `tree`，抽出所有包含 `lods` 的 leaf node，并把每个叶子的 `bound` 转成 `BoundingBox`。

因此 manifest 里存的是完整树结构；运行时热路径主要用扁平化后的叶子数组：

```text
nodes[]
nodeBoundsMinMax[]
files[]
fileRefCounts[]
```

这样做的好处：

- manifest 保留空间层次，便于描述大场景结构。
- 运行时 LOD 选择只扫叶子节点，避免频繁递归。
- `offset/count` 允许多个空间节点共用 chunk，减少小文件数量。

## 7. 浏览器引擎如何加载

PlayCanvas 的 `GSplatHandler` 根据 URL 类型选择 parser：

```text
.ply          -> PlyParser
.sog          -> SogBundleParser
meta.json     -> SogParser
lod-meta.json -> GSplatOctreeParser
```

加载 `lod-meta.json` 时：

```text
1. 下载 lod-meta.json
2. 构造 GSplatOctreeResource
3. 解析 filenames，转成完整 URL
4. 递归 tree，抽取 leaf nodes
5. 为每个叶子建立 lods[fileIndex, offset, count]
6. 创建 octree instance
```

渲染时，`GSplatOctreeInstance` 根据相机更新每个叶子的目标 LOD：

```text
1. 计算相机到叶子 AABB 的最近距离
2. 根据 lodBaseDistance / lodMultiplier 得到最佳 LOD
3. 根据 FOV 做距离补偿
4. 根据 lodRangeMin / lodRangeMax 限制范围
5. 若目标 chunk 未加载，先请求加载
6. 在新 chunk 到达前，可继续显示旧 LOD 或较粗 LOD
7. 新资源可用后替换 placement
8. 不再引用的文件进入 cooldown，之后卸载
```

LOD 距离是几何级数：

```text
LOD 0: distance < lodBaseDistance
LOD 1: lodBaseDistance
LOD 2: lodBaseDistance * lodMultiplier
LOD 3: lodBaseDistance * lodMultiplier^2
...
```

默认概念上是：

```text
近处 -> LOD 0，高质量
远处 -> 更高 LOD 编号，低质量
```

`lodUnderfillLimit` 用来处理“理想 LOD 还没加载完”的情况：可以临时显示较粗的、已经加载好的 LOD，避免黑块或等待。

## 8. 设计理念

PlayCanvas 方案的核心不是做一个通用地理空间标准，而是做一个浏览器友好的高斯点交付系统：

- 用 SOG 把高斯属性压缩成图片/纹理，降低带宽和加载成本。
- 用 octree 把大场景切成空间块，让相机附近先细化。
- 用 `lod-meta.json` 把“空间节点”和“chunk 文件区间”解耦。
- 用引用计数和 cooldown 管理 chunk 生命周期，避免相机轻微移动造成频繁卸载/重载。
- 用 unified rendering 做全局排序和多 splat 统一渲染，减少多个 splat 之间的排序瑕疵。

## 9. 和 Cesium 3D Tiles 的区别

```text
PlayCanvas / SuperSplat:
  lod-meta.json + SOG chunks
  目标是 Web 实时高斯点渲染
  运行时由 PlayCanvas GSplatComponent 管理

Cesium:
  tileset.json + 3D Tiles / glTF extension
  目标是地理空间、全球坐标、城市级数据
  运行时由 Cesium 的 3D Tiles traversal 管理
```

两者都在做“视角驱动的分块 LOD 流式加载”，但文件结构、坐标语义、调度系统都不是一套。

## 10. 主要参考

- PlayCanvas SOG Format: https://developer.playcanvas.com/user-manual/gaussian-splatting/formats/sog/
- PlayCanvas SplatTransform: https://developer.playcanvas.com/user-manual/splat-transform/
- PlayCanvas Streaming LOD Tutorial: https://developer.playcanvas.com/tutorials/gaussian-splat-streaming-lod/
- PlayCanvas GSplatComponent API: https://api.playcanvas.com/engine/classes/GSplatComponent.html
- PlayCanvas Engine source:
  - `src/framework/handlers/gsplat.js`
  - `src/framework/parsers/gsplat-octree.js`
  - `src/scene/gsplat-unified/gsplat-octree.js`
  - `src/scene/gsplat-unified/gsplat-octree-instance.js`
