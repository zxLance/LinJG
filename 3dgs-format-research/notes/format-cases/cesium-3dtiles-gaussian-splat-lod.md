# Cesium 生态 3D Gaussian Splat + 3D Tiles LOD 简明说明

## 1. 一句话结论

Cesium 生态里的高斯点流式加载不是单独发明一种 `lod-meta.json`，而是把高斯点放进标准 3D Tiles 管线：

```text
tileset.json        -> 空间索引、LOD 树、地理定位、加载调度
tile content .glb   -> 每个瓦片里的高斯点数据
glTF extensions     -> 描述这些点不是普通点云，而是 Gaussian splats
SPZ compression     -> 压缩高斯点属性，降低网络和显存压力
```

可以理解成：

```text
3D Tiles 管树和流式调度
glTF/GLB 管单个瓦片的数据容器
KHR_gaussian_splatting 管高斯点语义
KHR_gaussian_splatting_compression_spz_2 管压缩存储
```

本文已用 Cesium 官方公开 asset `4547222` 做过实测。该数据入口为：

```text
https://assets.ion.cesium.com/us-east-1/4547222/LOD_3DT_Microsoft_SH0/tileset.json?v=2
```

## 2. 整体文件结构

典型目录结构：

```text
tileset/
  tileset.json
  root.glb
  0/
    0.glb
    1.glb
  1/
    0.glb
    1.glb
  ...
```

也可能是：

```text
tileset/
  tileset.json
  tile_0.glb
  ts_0/
    tileset.json
    tile_1.glb
    ts_1/
      tileset.json
      ts_2/
        tileset.json
        tile_2.glb
```

核心入口永远是 `tileset.json`。它描述空间层级、每个 tile 的包围体、误差、refinement 策略和内容 URI。

真实样本中，很多子节点的 `content.uri` 指向另一个外部 `tileset.json`，不是直接指向 `.glb`。因此遍历时必须按 URI 递归解析，不能臆造文件路径。

## 3. tileset.json 关键字段

精简示意：

```json
{
  "asset": {
    "version": "1.0"
  },
  "geometricError": 100.0,
  "root": {
    "boundingVolume": {
      "box": [cx, cy, cz, hx1, hy1, hz1, hx2, hy2, hz2, hx3, hy3, hz3]
    },
    "geometricError": 50.0,
    "refine": "REPLACE",
    "content": {
      "uri": "root.glb"
    },
    "children": [
      {
        "boundingVolume": { "box": [...] },
        "geometricError": 20.0,
        "content": { "uri": "0/0.glb" },
        "children": []
      }
    ]
  }
}
```

字段含义：

- `asset.version`：3D Tiles 版本。
- `geometricError`：该层内容的几何误差，用于屏幕空间误差 SSE 计算。
- `root`：LOD 树根节点。
- `boundingVolume`：tile 的空间范围，可用 `box`、`sphere`、`region`。
- `transform`：tile 到父坐标系的矩阵，子节点继承父变换。
- `refine`：细化策略，常见为 `REPLACE` 或 `ADD`。
- `content.uri`：当前 tile 的实际内容文件，3DGS 场景中通常是 `.glb`。
- `children`：更细一级的 tile。
- `extensions.3DTILES_content_gltf`：声明 tile content 是 glTF，并列出 glTF 内使用/必需的扩展。

`REPLACE` 表示子 tile 足够精细时替换父 tile；`ADD` 表示子 tile 叠加在父 tile 上。3DGS LOD 场景通常更接近 HLOD：粗 tile 先显示，细 tile 加载后按 3D Tiles refinement 规则替换或补充。

## 4. LOD 树如何生成和储存

Cesium 官方公开的是结果格式和运行时逻辑；Cesium ion / iTwin Capture 的具体 3DGS tiler 算法细节不是完整公开规格。

从 3D Tiles 角度看，生成过程可以理解为：

```text
照片 / 重建输入
  |
  v
3D Gaussian reconstruction
  |
  v
空间划分
  |
  v
为每个空间块生成一个或多个 LOD 内容
  |
  v
计算每个 tile 的 boundingVolume / geometricError
  |
  v
写入 tileset.json 树
  |
  v
每个 tile 写一个 GLB payload
```

树的储存方式有两种常见形态：

```text
显式树:
  children 直接写在 tileset.json 里，或通过 content.uri 串到外部 tileset.json

隐式树:
  tileset.json 描述模板
  subtree 文件记录哪些节点存在
```

不管哪种，浏览器看到的抽象都是 tile tree：

```text
tile node
  boundingVolume
  geometricError
  content.uri
  children
```

和 PlayCanvas 的 `lod-meta.json` 不同，Cesium/3D Tiles 通常是“父 tile 可以有自己的粗内容，子 tile 有更细内容”。因此低细节时渲染的是父 tile 的 GLB；细节要求提高后，加载并切换到子 tile。

但不是每个中间节点都一定有 `.glb`。真实样本中：

```text
root
  content: tile_0.glb
  child content: ts_0/tileset.json

ts_0/root
  content: tile_1.glb
  children: ts_1/tileset.json, ts_22/tileset.json, ...

ts_0/ts_1/root
  no content
  children: ts_2/tileset.json, ts_7/tileset.json, ...

ts_0/ts_1/ts_2/root
  content: tile_2.glb
  children: ts_3/tileset.json, ...
```

所以更准确的说法是：3D Tiles 树负责 HLOD refinement；节点可以有 GLB 内容，也可以只是分组/中转节点。

## 5. 单个 GLB 里 3D 高斯如何储存

`KHR_gaussian_splatting` 把高斯点作为 glTF mesh primitive 的 `POINTS` 来存。

精简示意：

```json
{
  "meshes": [
    {
      "primitives": [
        {
          "mode": 0,
          "attributes": {
            "POSITION": 0,
            "KHR_gaussian_splatting:ROTATION": 1,
            "KHR_gaussian_splatting:SCALE": 2,
            "COLOR_0": 3
          },
          "extensions": {
            "KHR_gaussian_splatting": {
              "extensions": {
                "KHR_gaussian_splatting_compression_spz_2": {
                  "bufferView": 0
                }
              }
            }
          }
        }
      ]
    }
  ],
  "extensionsUsed": [
    "KHR_gaussian_splatting"
  ]
}
```

字段含义：

- `mode: 0`：glTF `POINTS` primitive。
- `POSITION`：Gaussian 中心点。
- `KHR_gaussian_splatting:ROTATION`：局部主轴方向，四元数。
- `KHR_gaussian_splatting:SCALE`：三轴尺度。
- `COLOR_0`：真实 Cesium SH0 样本里使用的颜色/透明度路径。
- `KHR_gaussian_splatting:OPACITY`：规范中的透明度语义，具体数据不一定单独作为该 attribute 暴露。
- `KHR_gaussian_splatting:SH_DEGREE_0_COEF_0`：规范中的 0 阶球谐颜色系数语义。
- `SH_DEGREE_1/2/3...`：可选更高阶球谐。
- `kernel`：当前基础规范定义 `ellipse`。
- `colorSpace`：颜色空间。
- `projection`：投影方式，默认 `perspective`。
- `sortingMethod`：排序方式，默认 `cameraDistance`。

每个 Gaussian 的索引就是 point primitive 的第 `i` 个点：

```text
Gaussian i
  POSITION[i]
  ROTATION[i]
  SCALE[i]
  COLOR_0[i] 或 OPACITY/SH_COEF[i]
```

所以它不是靠独立索引表描述每个高斯，而是靠所有 accessor 的同序数组对齐。

## 6. SPZ 压缩如何放进 GLB

CesiumJS 当前的高斯点 tile content 路径主要面向：

```text
KHR_gaussian_splatting
+ KHR_gaussian_splatting_compression_spz_2
```

基础扩展定义“解码后的语义应该是什么”；SPZ 压缩扩展定义“这些属性如何压缩存放”。

未压缩概念上是：

```text
POSITION accessor
ROTATION accessor
SCALE accessor
OPACITY accessor
SH accessor
```

SPZ 路径概念上是：

```text
compressed SPZ payload in bufferView
  -> decode
  -> 得到 position / rotation / scale / opacity / SH
  -> 作为 Gaussian splat 渲染
```

这样做的原因很直接：

- 原始高斯属性体积巨大。
- Web 流式场景更需要压缩传输。
- glTF 保留语义和扩展机制，SPZ 负责压缩细节。

需要注意：`KHR_gaussian_splatting` 目前仍是 release candidate；Cesium 的支持也经历过旧实验扩展到当前扩展组合的迁移。写 pipeline 时应以当前 CesiumJS 版本支持的扩展为准。

真实样本 `tile_0.glb` 的实测结构：

```json
{
  "extensionsUsed": [
    "KHR_materials_unlit",
    "KHR_gaussian_splatting",
    "KHR_gaussian_splatting_compression_spz_2"
  ],
  "extensionsRequired": [
    "KHR_gaussian_splatting",
    "KHR_gaussian_splatting_compression_spz_2"
  ],
  "primitiveMode": 0,
  "pointCount": 22178,
  "attributes": {
    "POSITION": 0,
    "COLOR_0": 1,
    "KHR_gaussian_splatting:SCALE": 2,
    "KHR_gaussian_splatting:ROTATION": 3
  },
  "compression": {
    "bufferView": 0
  }
}
```

采样到的几个真实 GLB：

```text
tile_0.glb                         397,300 bytes   22,178 points
ts_0/tile_1.glb                  1,860,776 bytes  103,522 points
ts_0/ts_1/ts_2/tile_2.glb          601,152 bytes   33,108 points
```

## 7. 浏览器引擎如何加载

CesiumJS 的运行时流程可以概括为：

```text
1. 加载 tileset.json
2. 构建 3D Tiles tile tree
3. 每帧根据相机和 boundingVolume 计算可见性
4. 根据 geometricError 计算 screen-space error
5. SSE 超过 maximumScreenSpaceError 时细化到子 tile
6. 请求需要的 content.uri
7. 下载 GLB tile content
8. 检查 glTF Gaussian extensions
9. 解码 SPZ / 建立高斯渲染资源
10. 按 tile refinement 规则渲染父或子内容
11. 根据内存预算卸载不再需要的 tile
```

核心控制参数：

- `maximumScreenSpaceError`：越小越清晰，但加载更多 tile。
- `maximumMemoryUsage` / cache budget：控制缓存规模。
- `debugShowBoundingVolume`：显示当前可见 tile 包围盒。
- `debugShowGeometricError`：显示 tile 几何误差。
- `debugColorizeTiles`：给不同 tile 上色，观察 LOD 切换。

CesiumJS 里 `GaussianSplat3DTileContent` 表示使用 `KHR_gaussian_splatting` 和 `KHR_gaussian_splatting_compression_spz_2` 的 glTF/GLB tile content。它的 `pointsLength` 等于 tile 内高斯点数量；`trianglesLength` 为 0，因为高斯点不是三角网格。

## 8. 和 PlayCanvas 方案的核心区别

```text
PlayCanvas / SuperSplat:
  lod-meta.json + SOG chunks
  leaf node 上挂多个 LOD offset/count
  运行时在 leaf 上切换不同精度的 chunk 区间

Cesium / 3D Tiles:
  tileset.json + tile tree + GLB payload
  父 tile 可保存粗内容，子 tile 保存细内容
  运行时通过 SSE 决定是否 refine 到子 tile
```

因此，Cesium 更像地理空间 HLOD 系统；PlayCanvas 更像为浏览器高斯点渲染定制的 SOG streaming 系统。

## 9. 设计理念

Cesium 方案的重点是把 3DGS 纳入现有地理空间流式生态：

- 3D Tiles 负责全球坐标、空间索引、HLOD、缓存和调度。
- glTF 负责单个 tile 的资产表达。
- `KHR_gaussian_splatting` 负责标准化高斯点语义。
- SPZ 负责高斯点压缩。
- Cesium ion 负责从照片到可流式 tileset 的生产管线。

这套设计的优势是能直接复用 3D Tiles 已有能力：地理配准、跨平台流式加载、LOD refinement、视锥裁剪、缓存管理和调试工具。

## 10. 主要参考

- Cesium: 3D Gaussian Splats with Hierarchical LOD using 3D Tiles  
  https://cesium.com/blog/2026/04/27/3d-gaussian-splats-lod/
- CesiumJS tutorial: View 3D Gaussian Splat Tilesets with LODs  
  https://cesium.com/learn/cesiumjs-learn/3d-guassian-splat-tilesets-lods/
- CesiumJS `GaussianSplat3DTileContent` API  
  https://cesium.com/learn/cesiumjs/ref-doc/GaussianSplat3DTileContent.html
- Khronos `KHR_gaussian_splatting` specification  
  https://github.com/KhronosGroup/glTF/blob/main/extensions/2.0/Khronos/KHR_gaussian_splatting/README.md
- OGC 3D Tiles specification  
  https://docs.ogc.org/cs/22-025r4/22-025r4.html
