# XGRIDS LCC2 文件格式设计说明

这份笔记记录其域创新 XGRIDS 的 LCC2 格式。重点是讲清楚：文件内部结构、LoD 树怎样存、为什么它能分层加载、浏览器引擎大概怎样加载。

重要修正：我们查看真实 LCC2 文件后确认，**不是只有叶子节点才索引 3D 高斯数据，而是每个节点都可以索引该层级的 3D 高斯数据**。这点非常关键，否则 LCC2 就无法实现真正的分层加载。

主要资料来源：

- [XGRIDS LCC2Whitepaper](https://github.com/xgrids/LCC2Whitepaper)
- [XGRIDS LCC-Web-SDK](https://github.com/xgrids/LCC-Web-SDK)
- [LCC Web SDK 中文说明](https://docs.xgrids.cloud/zh/lcc/lcc-web.html)
- 工作目录中的真实 `.lcc2` 文件观察结论：`3dgs-format-research/demos/qiyu-lcc2-demo/data/K1-LuoJiaShiYanShi.lcc2`

## 1. 一句话理解 LCC2

LCC2 不是一个单独的大二进制高斯文件，而是一个“大场景 LoD 索引包”：

```text
scene.lcc2
  描述 LoD 树、每个节点的包围盒、每个节点引用哪段高斯数据

data/3dgs/*
  真正的 3D Gaussian 数据文件

data/mesh/*
  可选 mesh 数据
```

最重要的结构是：

```text
LoD Node = 空间块 + 该层级可渲染高斯数据索引 + 子节点
```

也就是说，一个节点既是空间索引节点，也可以是一个可渲染 LoD 层级。

## 2. LCC2 文件夹结构

一个典型 LCC2 导出目录大概是：

```text
MyScene/
  MyScene.lcc2
  data/
    3dgs/
      0.spz
      1.spz
      2.spz
    mesh/
      0.ply
```

其中：

- `.lcc2` 是 JSON 索引文件。
- `data/3dgs/*` 是真正的高斯数据，可能是 `.ply`、`.spz`、`.sog` 等。
- `data/mesh/*` 是可选 mesh。

所以 LCC2 的重点不是重新定义所有高斯点怎么二进制编码，而是定义一个大场景怎样分层、怎样索引、怎样流式加载。

## 3. `.lcc2` 顶层结构

`.lcc2` 是 JSON。顶层一般包含：

```json
{
  "version": "0.0.3",
  "name": "SceneName",
  "splatType": ".spz",
  "totalSplats": 12345678,
  "totalLevels": 4,
  "lodSplats": [100000, 500000, 2000000, 9000000],
  "splatFiles": [
    "data/3dgs/0.spz",
    "data/3dgs/1.spz"
  ],
  "root": {
    "...": "LoD tree"
  }
}
```

几个关键字段：

| 字段 | 含义 |
| --- | --- |
| `version` | LCC2 格式版本。 |
| `name` | 场景名称。 |
| `splatType` | 底层高斯文件格式，例如 `.spz`。 |
| `totalSplats` | 总高斯数量。 |
| `totalLevels` | LoD 层数。 |
| `lodSplats` | 各层级高斯数量统计。 |
| `splatFiles` | 真实高斯数据文件列表。 |
| `root` | LoD 树根节点。 |

`lodSplats` 很重要。它说明 LCC2 不是只有最底层才有数据，而是按层级组织了不同精度的数据量。

## 4. Node 是核心单位

一个 LCC2 Node 可以理解为：

```text
Node {
  id
  boundingBox
  data
  childNum
  child
}
```

### 4.1 `id`

`id` 表示层级路径，例如：

```text
0
0-1
0-1-3
```

这种命名让人能看出父子关系，但运行时不一定靠字符串搜索节点。加载器可以在解析 `.lcc2` 后把树转成数组或 Map。

### 4.2 `boundingBox`

每个节点都有包围盒：

```json
{
  "boundingBox": {
    "min": [x0, y0, z0],
    "max": [x1, y1, z1]
  }
}
```

浏览器用它判断：

- 节点是否在视野内。
- 节点离相机多远。
- 节点投影到屏幕上有多大。
- 是否需要展开到更细层级。

### 4.3 `data`

这是我们这次修正的重点。

真实 LCC2 文件显示：**内部节点也会索引 3DGS 数据**。一个节点的数据引用大概是：

```json
{
  "data": {
    "3dgs": {
      "name": 3,
      "start": 500000,
      "count": 80000
    }
  }
}
```

含义是：

```text
文件路径 = splatFiles[3]
数据范围 = 从第 500000 个 splat 开始，读取 80000 个 splat
```

所以 `data.3dgs.name/start/count` 是节点到真实高斯数据的索引。

下面是来自真实文件 `3dgs-format-research/demos/qiyu-lcc2-demo/data/K1-LuoJiaShiYanShi.lcc2` 的证据摘录。这个节点的 `childNum` 是 `2`，说明它不是叶子节点；但它同时有 `data.3dgs.name/start/count`，说明内部节点本身也索引了一段 3DGS 数据：

```json
{
  "id": "0_4_0_2",
  "boundingBox": {
    "min": "-14.1703401875 2.75297865000003 -9.3454823",
    "max": "-3.54555446874998 14.066732075 10.40614795"
  },
  "childNum": 2,
  "child": {
    "0": {
      "id": "0_4_0_2_0",
      "childNum": 0,
      "data": {
        "3dgs": {
          "name": 5,
          "start": 0,
          "count": 391276
        }
      }
    },
    "1": {
      "id": "0_4_0_2_1",
      "childNum": 0,
      "data": {
        "3dgs": {
          "name": 5,
          "start": 391276,
          "count": 227241
        }
      }
    }
  },
  "data": {
    "3dgs": {
      "name": 2,
      "start": 393880,
      "count": 113873
    }
  }
}
```

因此，“每个 Node 都可以索引该层级的 3DGS 数据”不是我们的推断，而是来自真实 LCC2 样本的解析结论。

### 4.4 `childNum` 和 `child`

如果节点还有更细层级，就会有子节点：

```json
{
  "childNum": 2,
  "child": {
    "0": { "id": "0-0" },
    "1": { "id": "0-1" }
  }
}
```

这说明 LCC2 是 N 叉树，不是固定二叉树，也不一定是固定八叉树。

## 5. LoD 树怎样实现分层加载

因为每个节点都可以索引自己的高斯数据，所以 LCC2 的分层加载逻辑可以成立。

一个简化树：

```text
Root
  data = 全场景粗层高斯
  |
  +-- A
  |   data = A 区域中层高斯
  |   |
  |   +-- A0
  |   |   data = A0 区域细层高斯
  |   |
  |   +-- A1
  |       data = A1 区域细层高斯
  |
  +-- B
      data = B 区域中层高斯
```

浏览器可以这样加载：

```text
1. 初始状态
   加载 Root.data
   先显示全场景粗略结果

2. 相机靠近 A 区域
   加载 A.data
   用 A 的中层数据替换 Root 中对应区域的粗数据

3. 相机继续靠近 A0
   加载 A0.data
   用 A0 的细层数据替换 A 中对应区域的中层数据
```

这才是真正的 LoD streaming：

```text
远处用浅层节点数据
近处用深层节点数据
深层数据加载完成后替换浅层数据
```

如果内部节点没有数据，那它只能当目录，分层加载就会退化成空间分块加载。真实文件证明 LCC2 不是这种弱形式。

## 6. LoD 树怎样生成

公开白皮书没有给出完整生成算法源码，所以不能像 Spark RAD 那样精确到某个 `feature_size` 或合并函数。

但根据文件结构和真实样本，可以确定生成结果遵循这些规则：

1. 场景被组织成一棵空间层级树。
2. 每个节点都有自己的 `boundingBox`。
3. 每个节点可以索引一段该层级的 3DGS 数据。
4. 子节点表示更小空间范围或更高精度层级。
5. `lodSplats` 记录各层级高斯数量。
6. `splatFiles` 存储真实高斯数据，节点通过 `name/start/count` 指向其中一段。

一个合理的生成链路是：

```text
输入扫描 / 重建数据
  |
  v
生成完整 3DGS 场景
  |
  v
按空间范围构建层级 Node 树
  |
  v
为不同层级生成对应精度的高斯数据
  |
  v
把各层级数据写入 data/3dgs 文件
  |
  v
在 .lcc2 中记录每个节点的 boundingBox 和 data.3dgs 索引
```

这里要区分“能确认”和“不能确认”：

- 能确认：LCC2 的结果是空间树 + 每节点数据索引。
- 不能确认：官方具体用什么切分阈值、降采样算法、误差度量或聚类算法。

所以现在不能简单说它只是“二分降采样”或“简单空间裁切”。更稳妥的说法是：

```text
LCC2 的公开结果形态是空间 LoD 树；
具体构建算法没有完全公开。
```

## 7. 浏览器引擎怎样加载

LCC Web SDK 支持 Three.js 和 Cesium.js。公开文档没有完全展开内部算法，但基于 LCC2 结构，加载流程应该是：

```text
1. 请求 scene.lcc2
2. 解析 JSON
3. 把 root/child 树转成运行时节点结构
4. 初始加载 root 或浅层可见节点的数据
5. 每帧根据相机和 boundingBox 判断是否展开
6. 对需要细化的节点，请求其 child 节点 data 对应的 splat 文件段
7. 解码高斯数据，上传 GPU
8. 用更深层节点替换浅层节点显示
9. 远离相机后释放或缓存旧节点数据
```

注意，运行时不应该每帧在 JSON 里按字符串 id 全树搜索。更合理的做法是加载 `.lcc2` 后建立内部索引：

```text
id -> node Map
node.children 数组
node.loading / loaded / visible 状态
```

从节点找到高斯数据本身也不是复杂搜索：

```text
node.data.3dgs.name  -> splatFiles 数组下标
node.data.3dgs.start -> 起始 splat
node.data.3dgs.count -> splat 数量
```

这是直接索引。

## 8. 和 Spark RAD 的关键区别

| 对比点 | Spark RAD | XGRIDS LCC2 |
| --- | --- | --- |
| 文件形态 | 单个或分块二进制容器 | JSON 索引 + 多个高斯数据文件 |
| LoD 节点 | 父节点本身是合并高斯点 | 节点是空间块，并索引该层级高斯数据 |
| 树关系 | `child_count` / `child_start` 属性列 | `.lcc2` JSON 的 `child` 递归结构 |
| 数据读取单位 | 固定 chunk，默认 65536 splats | 节点引用的 `name/start/count` 数据段 |
| 设计重点 | 二进制流式渲染效率 | 大场景空间层级管理和跨平台加载 |

最重要的区别：

```text
Spark RAD:
  LoD 树是“高斯点合并树”。
  父节点本身就是一个粗高斯。

LCC2:
  LoD 树是“空间块层级树”。
  每个节点索引该空间块在该层级的高斯数据。
```

## 9. 设计理念总结

LCC2 的核心设计可以总结成：

```text
树在 .lcc2
点在 data/3dgs
每个节点都有空间范围
每个节点可索引本层级高斯数据
浏览器按相机视角逐层替换加载
```

它的优势：

- JSON 索引可读、可检查、可扩展。
- 高斯数据和 LoD 组织解耦。
- 适合大场景、测绘、数字孪生类数据。
- 可以先显示粗层，再逐步加载细层。

它的代价：

- 初次加载要解析 `.lcc2` 树。
- 运行时需要把 JSON 转成高效内部结构。
- 具体生成算法不在公开白皮书中，依赖 LCC Studio / XGRIDS 工具链。

一句话：

```text
LCC2 是一种用 JSON 描述空间 LoD 树、
让每个节点索引对应层级 3DGS 数据、
并面向浏览器大场景流式加载的 3DGS 组织格式。
```
