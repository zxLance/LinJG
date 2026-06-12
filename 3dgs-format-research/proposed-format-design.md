# W3GS 格式设计草案

最后更新：2026-06-09

暂定名称：

```text
W3GS = Web Streaming 3D Gaussian Splatting Format
```

这个名字只是研究阶段占位名，后续可以修改。当前重点不是命名，而是把我们自己的格式思想落成可讨论、可实现、可实验验证的第一版结构。

## 1. 设计定位

W3GS 不是新的 3DGS 重建算法，也不是新的压缩算法或 renderer。

它的定位是：

```text
一种面向 Web 流式渲染的 3DGS 场景组织格式。
```

它重点解决：

- 如何把大规模 3DGS 场景拆成可随机访问的空间节点。
- 如何让同一个空间节点支持 base layer 和 refinement layers。
- 如何把空间层级、渐进层和 payload codec 解耦。
- 如何让浏览器根据相机、网络、显存和 GPU 上传成本调度数据。
- 如何兼容 raw、SPZ、SOG、GLB 或未来 MPEG GSC 等 payload。

一句话：

```text
W3GS = 空间索引容器 + 渐进层组织 + 可插拔 Gaussian payload + Web 调度元数据。
```

## 2. 设计来源

W3GS 吸收了现有格式的优点，但试图避免它们的边界：

| 来源 | 吸收的设计 | 试图改进的问题 |
| --- | --- | --- |
| Spark RAD | 连续数组、低成本 chunk / LoD 引用。 | 避免过度绑定 Spark runtime 和专用 payload。 |
| XGRIDS LCC2 | 每个空间 Node 可索引本层级 3DGS 数据。 | 显式补足 payload schema、替换策略和调度语义。 |
| SOG Streaming | Web-friendly chunk、manifest 和压缩交付。 | 避免 manifest 过度绑定某个 viewer runtime。 |
| Cesium 3D Tiles 3DGS | HLOD、标准容器和 payload 分离。 | 增加 3DGS 专属 LoD contract，而不是只靠通用 SSE。 |
| 前沿论文 | progressive、FoV adaptive、streaming、GPU-aware layout。 | 把这些需求变成格式字段，而不是只留给 runtime 自行猜测。 |

## 3. 核心设计原则

### 3.1 空间层级和渐进层正交

传统 LoD 格式经常把“空间变细”和“精度变高”混在一起。W3GS 把它们拆成两个维度：

```text
空间维度：
  root node -> child node -> leaf node

精度维度：
  base layer -> refinement layer 1 -> refinement layer 2
```

这意味着：

- 远处可以加载大空间节点的 base layer。
- 近处可以加载小空间节点的 base layer。
- 同一个节点也可以先加载 base layer，再继续加载 refinement layers。
- 浏览器可以在空间细化和精度细化之间做调度选择。

### 3.2 容器不绑定 payload codec

W3GS 的 manifest 只描述：

- 数据在哪里。
- 数据是什么层级。
- 数据属于哪个空间节点。
- 数据如何依赖其他数据。
- 数据如何被调度和上传。

至于真实 payload 可以是：

- raw Gaussian binary。
- SPZ。
- SOG。
- GLB + KHR_gaussian_splatting。
- 未来 MPEG Gaussian Splat Coding。

### 3.3 LoD contract 显式写进格式

3DGS 的 LoD 不是简单减少点数。它还涉及透明度、排序、密度、Gaussian 尺度和 SH 细节。

所以 W3GS 需要显式描述：

- 父层和子层是替换关系还是叠加关系。
- refinement layer 是增量数据还是完整替换数据。
- 节点的视觉误差估计。
- 节点的透明排序风险。
- 节点的估计解码成本和 GPU 上传成本。

当前 W3GS 的正式 LoD 生成方向已经从早期的 `duplicated-parent` 原型收敛为：

```text
leaf 保存原始细节 splats；
parent/internal 保存由子树聚合生成的 summary splats；
parent-child refinement 默认采用 replacement；
leaf 内部可选使用 importance-sorted additive prefix。
```

也就是说，W3GS 不应把父节点粗层简单实现成“复制一部分子节点 splats”。父节点应是可解释的 synthetic summary，子节点加载后替换父节点 summary，从而避免重复存储和透明度重复贡献。

### 3.4 Web 调度信息一等公民

W3GS 面向浏览器，不应只考虑离线存储。格式中应该保留 Web runtime 需要的调度 hint：

- 首屏推荐加载集合。
- 请求优先级。
- byte range 合并建议。
- 解码成本估计。
- GPU 上传大小。
- 显存预算等级。
- mobile profile。

## 4. 文件组成

第一版 W3GS 建议采用“JSON manifest + 二进制 chunk”的组合：

```text
scene.w3gs.json
nodes.w3gs.json
chunks.w3gs.json
payload/
  chunks-0.bin
  chunks-1.bin
  optional.spz
  optional.sog
```

也可以打包成一个单文件容器，但第一阶段不建议这么做。原因是：

- 分文件更容易调试。
- 更容易观察浏览器请求。
- 更适合论文实验。
- 后续再合并成二进制容器不迟。

## 5. 顶层 Manifest

`scene.w3gs.json` 负责描述整个场景：

```json
{
  "format": "W3GS",
  "version": "0.1",
  "scene": {
    "name": "demo-scene",
    "coordinateSystem": "local",
    "upAxis": "Y",
    "units": "meter"
  },
  "bounds": {
    "type": "aabb",
    "min": [-1.0, -1.0, -1.0],
    "max": [1.0, 1.0, 1.0]
  },
  "nodes": "nodes.w3gs.json",
  "chunks": "chunks.w3gs.json",
  "payloadBaseUri": "payload/",
  "defaultCodec": "raw-gaussian-v0",
  "entry": {
    "rootNode": "n0",
    "startupSet": ["n0.base"]
  },
  "profiles": {
    "desktop": {
      "memoryBudgetMB": 1024,
      "maxConcurrentRequests": 8
    },
    "mobile": {
      "memoryBudgetMB": 256,
      "maxConcurrentRequests": 4
    }
  }
}
```

关键点：

- `nodes` 指向空间节点树。
- `chunks` 指向 chunk table。
- `startupSet` 显式说明首屏推荐加载哪些 layer。
- `profiles` 让格式可以给不同设备预算。

## 6. 空间节点树

`nodes.w3gs.json` 负责描述空间层级。

一个节点不是直接等于一份高斯数据，而是：

```text
Node = 节点 ID + 父节点 ID + 子节点 ID 列表 + 空间范围 + 本节点 layer 列表 + LoD contract
```

也就是说，空间树的连接关系由 `parent` 和 `children` 显式写在格式里：

```text
parent:
  指向父节点 ID。root 节点的 parent 为 null。

children:
  保存子节点 ID 列表。叶子节点的 children 为空数组。
```

示例：

```json
{
  "nodes": [
    {
      "id": "n0",
      "parent": null,
      "children": ["n0_0", "n0_1"],
      "bounds": {
        "type": "aabb",
        "min": [-1.0, -1.0, -1.0],
        "max": [1.0, 1.0, 1.0]
      },
      "layers": [
        {
          "id": "n0.base",
          "kind": "base",
          "chunk": "c0",
          "splatCount": 12000,
          "refinementMode": "replace-by-children"
        },
        {
          "id": "n0.r1",
          "kind": "refinement",
          "chunk": "c1",
          "splatCount": 30000,
          "refinementMode": "additive"
        }
      ],
      "lod": {
        "screenSizeEnter": 0.25,
        "screenSizeExit": 0.18,
        "estimatedError": 0.08,
        "opacityError": 0.05,
        "sortRisk": "medium"
      },
      "runtimeHints": {
        "priority": 100,
        "decodeCost": 1.0,
        "gpuUploadBytes": 768000,
        "cachePolicy": "keep"
      }
    },
    {
      "id": "n0_0",
      "parent": "n0",
      "children": ["n0_0_0"],
      "bounds": {
        "type": "aabb",
        "min": [-1.0, -1.0, -1.0],
        "max": [0.0, 1.0, 1.0]
      },
      "layers": [
        {
          "id": "n0_0.base",
          "level": 0,
          "kind": "base",
          "chunk": "c2",
          "splatCount": 8000,
          "refinementMode": "replace-by-children"
        },
        {
          "id": "n0_0.r1",
          "level": 1,
          "kind": "refinement",
          "chunk": "c3",
          "splatCount": 18000,
          "refinementMode": "additive"
        },
        {
          "id": "n0_0.r2",
          "level": 2,
          "kind": "refinement",
          "chunk": "c4",
          "splatCount": 36000,
          "refinementMode": "additive"
        }
      ]
    },
    {
      "id": "n0_0_0",
      "parent": "n0_0",
      "children": [],
      "bounds": {
        "type": "aabb",
        "min": [-1.0, -1.0, -1.0],
        "max": [-0.5, 0.5, 0.5]
      },
      "layers": [
        {
          "id": "n0_0_0.base",
          "level": 0,
          "kind": "base",
          "chunk": "c5",
          "splatCount": 4000,
          "refinementMode": "additive"
        }
      ]
    }
  ]
}
```

这个例子里：

```text
n0
  parent = null
  children = ["n0_0", "n0_1"]

n0_0
  parent = "n0"
  children = ["n0_0_0"]

n0_0_0
  parent = "n0_0"
  children = []
```

加载器解析后可以建立一个 `id -> node` 的 Map。之后从父节点找子节点不需要遍历整棵树，只需要读取 `children` 里的 ID，再查 Map。

## 7. Base Layer 和 Refinement Layer

W3GS 中每个空间节点可以有多个 layer。

### 7.1 Base Layer

Base layer 的目标是：

```text
尽快让这个空间节点有可见结果。
```

它应该满足：

- 数据量小。
- 可独立渲染。
- 不依赖 refinement。
- 可用于首屏显示或远处显示。

### 7.2 Refinement Layer

Refinement layer 的目标是：

```text
在节点已经可见后，继续提高局部质量。
```

它可以有两种模式：

| 模式 | 含义 | 适用场景 |
| --- | --- | --- |
| `additive` | 在 base layer 基础上追加高斯。 | 渐进增强、低闪烁。 |
| `replacement` | 用更细 layer 替换粗 layer。 | 避免重复贡献、控制透明混合误差。 |

早期 Prototype 1 为了快速验证调度，使用过更简单的：

```text
base layer + additive refinement
```

它的作用是跑通 node / layer / chunk / payload 链路，不应作为论文发布级 LoD 策略。

当前正式建议是：

```text
parent-child: replacement
leaf-internal progressive: optional additive prefix
```

其中：

- `replacement` 用于空间层级之间：加载 children 后隐藏或释放 parent summary。
- `additive` 只建议用于同一个 leaf 内部的 progressive prefix，例如先加载高 importance 的 25%，再加载 50% / 100%。
- 这样可以避免 parent 和 child 同时渲染造成的 alpha 重复、过亮和排序复杂度。

## 8. Chunk Table

`chunks.w3gs.json` 负责描述 payload chunk。

示例：

```json
{
  "chunks": [
    {
      "id": "c0",
      "uri": "chunks-0.bin",
      "byteOffset": 0,
      "byteLength": 384000,
      "codec": "raw-gaussian-v0",
      "splatCount": 12000,
      "attributeSchema": "gaussian-basic-v0",
      "bounds": {
        "type": "aabb",
        "min": [-1.0, -1.0, -1.0],
        "max": [1.0, 1.0, 1.0]
      },
      "dependencies": [],
      "gpuLayout": {
        "preferredOrder": "morton",
        "alignment": 16,
        "interleaved": true
      }
    }
  ]
}
```

Chunk table 的作用是：

- 统一管理 byte range。
- 把 node/layer 和真实 payload 解耦。
- 支持不同 codec。
- 给浏览器提供 GPU 上传提示。

## 9. Payload Profile

W3GS 第一版定义一个最小 raw payload profile：

```text
raw-gaussian-v0
```

每个 splat 暂定包含：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| position | 3 x float32 | 中心点位置 |
| scale | 3 x float16 或 float32 | 三轴尺度 |
| rotation | 4 x float16 或 float32 | 四元数 |
| opacity | float16 或 float32 | 不透明度 |
| color | 3 x uint8 或 float16 | 基础颜色 |

第一版可以暂时不包含完整 SH，只做最小可视化；后续再扩展：

```text
gaussian-basic-v0
gaussian-sh-v0
gaussian-quantized-v0
```

这样做的理由：

- 第一版原型能跑起来。
- 格式结构先验证。
- 不被复杂压缩和 SH 编码拖住。

## 10. Gaussian-specific LoD Contract

W3GS 的 LoD contract 用于告诉 runtime：

```text
这个节点什么时候该显示？
什么时候该细化？
细化后应该替换还是叠加？
细化的视觉风险是什么？
```

第一版字段：

```json
{
  "lod": {
    "screenSizeEnter": 0.25,
    "screenSizeExit": 0.18,
    "estimatedError": 0.08,
    "opacityError": 0.05,
    "densityRatio": 0.42,
    "sortRisk": "medium",
    "refinementPolicy": "prefer-children-then-refinement"
  }
}
```

字段含义：

| 字段 | 含义 |
| --- | --- |
| `screenSizeEnter` | 节点投影足够大时进入细化。 |
| `screenSizeExit` | 节点投影变小时退出细化，用于 hysteresis。 |
| `estimatedError` | 粗层相对细层的估计误差。 |
| `opacityError` | 透明度累积误差估计。 |
| `densityRatio` | 当前层相对完整层的 splat 密度比例。 |
| `sortRisk` | 该节点透明排序误差风险。 |
| `refinementPolicy` | 优先加载子节点还是本节点 refinement。 |

## 11. 浏览器加载协议

W3GS runtime 的基本加载流程：

```text
1. 加载 scene.w3gs.json
2. 加载 nodes.w3gs.json 和 chunks.w3gs.json
3. 根据 startupSet 请求 root/base chunk
4. 解码 payload，上传 GPU
5. 每帧计算可见节点和 screen size
6. 根据 lod contract 选择：
   - 加载子节点 base layer
   - 或加载当前节点 refinement layer
7. 合并可合并的 byte range 请求
8. 解码并上传新 chunk
9. 根据 refinementMode 追加或替换旧 layer
10. 根据 memoryBudget 释放远处或低优先级 layer
```

这里的关键不是渲染器有多快，而是：

```text
格式显式告诉 runtime 可以怎样调度。
```

## 12. 从 PLY 生成 W3GS 的 LoD 策略

早期 converter 已经实现了一个 `duplicated-parent` 原型：root、internal node、leaf node 都可从同一批输入 splats 中生成 payload。它能验证调度链路，但会造成父子层级重复存储，不适合作为最终论文策略。

W3GS 当前推荐的正式生成策略是：

```text
Hierarchical Replacement LoD
+ Attribute-Aware Gaussian Summaries
```

### 12.1 基本原则

```text
Input:
  Gaussian PLY

Step 1:
  读取 Gaussian 属性，包括 position、scale、rotation、opacity、color / SH。

Step 2:
  按 position 构建 octree / BVH / Morton hierarchy。

Step 3:
  每个原始 splat 只分配给一个 leaf node。

Step 4:
  leaf 保存原始细节 splats，作为 canonical fine representation。

Step 5:
  internal / parent node 不复制原始 splats，而是从子树聚合生成 synthetic summary splats。

Step 6:
  parent-child refinement 使用 replacement。

Step 7:
  leaf 内部可选按 importance 生成 progressive prefix。

Step 8:
  输出 scene.w3gs.json、nodes.w3gs.json、chunks.w3gs.json 和 payload/chunks-*.bin。
```

### 12.2 Parent Summary 生成

parent/internal summary splats 建议用空间网格和属性感知聚类生成：

```text
1. 收集当前 node 子树覆盖的 splats。
2. 在 node 局部空间中建立 voxel / grid。
3. 每个 cell 内按 opacity、scale / footprint、color / SH DC 做轻量聚类。
4. 每个 cluster 生成一个 synthetic summary splat。
```

聚合规则第一版可以采用可解释近似：

| 字段 | Summary 生成方式 |
| --- | --- |
| `position` | opacity / importance 加权均值。 |
| `scale` / covariance | 覆盖 cluster 空间范围的保守估计。 |
| `rotation` | 主方向或加权近似；第一版可先简化。 |
| `opacity` | alpha compositing 近似，并做上限 clamp。 |
| `color` | opacity 加权均值。 |
| `SH` | parent summary 优先降阶，只保留 DC 或低阶；leaf 保留完整 SH。 |
| `sourceCount` | 记录被聚合的原始 splat 数。 |
| `approxError` | 记录 cluster 内位置、颜色、尺度误差估计。 |

### 12.3 LoD Metadata

为了让 LoD 生成策略不是 converter 黑盒，W3GS 应在 node / chunk metadata 中记录生成语义：

| 字段 | 含义 |
| --- | --- |
| `lodRole` | `summary` 或 `leaf`。 |
| `refinementMode` | parent-child 默认 `replacement`；leaf prefix 可为 `additive`。 |
| `summaryMethod` | 例如 `grid-cluster-merge-v0`。 |
| `sourceSplatCount` | 当前 summary 覆盖的原始 splat 数。 |
| `summarySplatCount` | 当前 summary 实际写出的 splat 数。 |
| `gridSize` / `targetRatio` | summary 生成预算。 |
| `opacityWeight` / `scaleWeight` / `colorWeight` | 聚类和 importance 权重。 |
| `shOrder` | parent summary 保留的 SH 阶数。 |
| `approxError` / `geometricError` | 粗层近似误差，用于 runtime 调度和实验评价。 |
| `storageOverhead` | summary 相对 leaf fine data 的额外存储开销。 |

### 12.4 当前保留的 Baseline

当前 converter 中的 `duplicated-parent` 策略应保留为 baseline：

```text
--lod-mode duplicated-parent
```

它用于对比和调试，不作为最终推荐策略。正式实现应新增：

```text
--lod-mode parent-summary
```

并逐步把 `parent-summary` 作为默认模式。

## 13. 最小原型计划

建议原型分三步：

### 13.1 Prototype 0：纯结构验证

目标：

- 手工或脚本生成一个小 `scene.w3gs.json`。
- 不渲染真实 3DGS，只打印 runtime 加载决策。

验证：

- manifest 是否清楚。
- node/layer/chunk 三者是否能互相索引。
- 相机移动时是否能选出正确 chunk。

### 13.2 Prototype 1：Raw Gaussian 可视化

目标：

- 使用 raw-gaussian-v0 payload。
- 浏览器加载 root/base。
- 相机靠近后加载 refinement。
- 用已有 splat renderer 或简化 point/splat renderer 显示。

验证：

- 首屏请求数。
- 首屏字节数。
- refinement 请求数。
- 可见 splat 数变化。

### 13.3 Prototype 2：Codec-independent 试验

目标：

- 同一个 node/layer/chunk 结构，尝试接入 SPZ 或 SOG payload。
- 验证调度层不依赖具体 codec。

验证：

- manifest 是否无需大改。
- runtime 是否只替换 decoder。
- chunk table 是否能继续工作。

## 14. 论文贡献草案

如果后续实验跑通，论文贡献可以写成：

1. 提出 W3GS，一种面向 Web 流式渲染的 3DGS 数据格式，将空间索引、渐进层和 Gaussian payload 解耦。
2. 设计 spatial node + base/refinement layers 的正交层级结构，支持首屏粗显示和局部渐进细化。
3. 提出 codec-independent Gaussian chunk profile，使 raw、SPZ、SOG 或未来 codec 可作为可插拔 payload。
4. 定义 Gaussian-specific LoD contract 和 Web runtime hints，用于指导浏览器加载、解码、GPU 上传和显存管理。
5. 通过最小原型验证该格式支持视角相关的 chunk 请求和渐进加载。

## 15. 当前未定问题

需要后续继续收敛的问题：

1. parent summary 的聚类参数如何选，例如 grid size、target ratio、max cluster size。
2. `approxError` / `geometricError` 哪些可以由 converter 稳定计算，哪些只能作为 hint。
3. leaf 内部 progressive prefix 是否进入第一版实现。
4. 第一版 payload 是否只支持 raw，还是同时支持 SPZ。
5. WebGPU viewer 如何支持 replacement refinement，而不是只把所有 chunk 追加进一个 buffer。
6. 实验对比基线如何组织：`duplicated-parent`、`parent-summary`、full loading、spatial-only、progressive-only。
7. 新格式是否要长期兼容 glTF / 3D Tiles，还是只作为独立研究原型。

## 16. 下一步

建议下一步拆成两个任务：

```text
任务 A：格式规范细化
  把 manifest/node/chunk/payload schema 写得更严格。

任务 B：最小原型设计
  决定输入数据、转换脚本、浏览器 demo 和实验指标。
```

完成这两项后，再重写 `research-plan.md`，把论文主线正式改成：

```text
基于现有格式和前沿论文缺口，提出并验证一种新的 Web 流式 3DGS 数据格式。
```

当前 `research-plan.md` 已经完成第一轮主线重写，Prototype 1 也已经跑通真实 PLY -> W3GS -> WebGPU raw viewer 链路。下一步应进入 LoD 生成策略 V2。

Prototype 1 不需要一次实现 W3GS 的所有字段，优先实现三组能支撑论文主张的核心字段：

| 优先级 | 字段组 | 为什么优先 |
| --- | --- | --- |
| P0 | `nodes[].parent`、`nodes[].children`、`nodes[].layers[]` | 证明空间节点树和 ordered progressive layers 是显式解耦的。 |
| P0 | `chunks[].uri`、`byteOffset`、`byteLength`、`codec`、`attributeSchema` | 证明 layer 指向 payload chunk，而不是绑定某一种数据编码或 renderer。 |
| P0 | `nodes[].lod`、`nodes[].runtimeHints` | 证明格式字段可以直接参与 Web 加载调度，包括 priority、decode cost、GPU upload bytes 和 refinement policy。 |
| P1 | `scene.profiles`、`startupSet`、`memoryBudgetMB` | 证明同一份数据可以面向 desktop / mobile 采用不同预算策略。 |
| P1 | renderer adapter / decode target | 证明 W3GS 不绑定单一 renderer，但第一版可以先用 placeholder viewer。 |

Prototype 1 的最低验收标准：

```text
浏览器能读取 W3GS sample JSON，
建立 node map / layer map / chunk map，
根据相机和预算选择 chunk，
并在界面上展示加载顺序、请求统计和当前可见 layer。
```

LoD 生成策略 V2 的最低验收标准：

```text
converter 支持 --lod-mode duplicated-parent 和 --lod-mode parent-summary；
parent-summary 模式中原始 splat 只归属 leaf；
internal node 生成 synthetic summary splats；
parent-child refinement 使用 replacement；
输出 metadata 记录 summary 方法、sourceCount、summaryCount、approxError 和 storage overhead；
生成统计能报告 duplicate ratio、summary overhead、first render bytes 和 local refinement bytes。
```
