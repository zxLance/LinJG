# Spark RAD 文件设计说明：从 PLY 到 LoD 再到 RAD

这份文档只讲一件事：Spark 是怎么把一个最普通的 3DGS `.ply` 文件，变成一个可以流式加载的 `.rad` 文件的。

先给结论：

`.ply` 里原本只有一堆原始高斯点。Spark 的 `build-lod` 会先把这些点读进内存，然后通过合并相近、相似的高斯点生成新的“父高斯点”。这些父高斯点和原始点一起组成一棵 LoD 树。最后，Spark 把这棵树摊平成一个数组，并把每个节点的树关系存成两列：`child_count` 和 `child_start`。RAD 文件里存的就是这个重排后的节点数组，加上每个节点的几何、颜色、SH、LoD 子节点信息。

核心源码入口：

- 普通 3DGS PLY 期望的字段：[ply.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/spark-lib/src/ply.rs:891)
- `build-lod` 主流程：[main.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/build-lod/src/main.rs:99)
- 默认 Quality LoD 生成：[bhatt_lod.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/spark-lib/src/bhatt_lod.rs:12)
- LoD 树重排成 chunk 友好顺序：[chunk_tree.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/spark-lib/src/chunk_tree.rs:408)
- RAD 写入：[rad.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/spark-lib/src/rad.rs:521)
- RAD 读取：[rad.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/spark-lib/src/rad.rs:1361)

## 1. 先看一个最小心智模型

假设 `.ply` 里只有 4 个原始 splat：

```text
PLY 原始点：

A
B
C
D
```

它们一开始没有 LoD 树关系，只是 4 个独立高斯点。Spark 生成 LoD 时，可能会先把 A 和 B 合并成一个父节点 P1，把 C 和 D 合并成一个父节点 P2，再把 P1 和 P2 合并成根节点 Root：

```text
Root
|
+-- P1
|   +-- A
|   +-- B
|
+-- P2
    +-- C
    +-- D
```

这时，内存里不再只有 4 个 splat，而是 7 个 splat：

```text
Root, P1, P2, A, B, C, D
```

注意：P1、P2、Root 不是普通意义上的“空节点”。它们也是高斯点，也有 center、scale、opacity、rgb、orientation。只是它们代表的是更粗的一层近似。

RAD 文件最终要解决的问题是：怎么把上面这棵树存进一个线性的文件里？

Spark 的答案非常简单：

```text
index  node   child_count   child_start
0      Root   2             1
1      P1     2             3
2      P2     2             5
3      A      0             0
4      B      0             0
5      C      0             0
6      D      0             0
```

解释一下：

- Root 的孩子有 2 个，从 index 1 开始，所以孩子是 `[1, 2]`。
- P1 的孩子有 2 个，从 index 3 开始，所以孩子是 `[3, 4]`。
- P2 的孩子有 2 个，从 index 5 开始，所以孩子是 `[5, 6]`。
- A、B、C、D 是叶子，没有孩子，所以 `child_count = 0`。

所以 LoD 树在 RAD 里的核心存法就是两列：

```text
child_count = [2, 2, 2, 0, 0, 0, 0]
child_start = [1, 3, 5, 0, 0, 0, 0]
```

真实文件当然还有 center、rgb、scale、rotation 等属性，但树结构本身就是这样存的。

源码对应：

- 写 `child_count`：[rad.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/spark-lib/src/rad.rs:817)
- 写 `child_start`：[rad.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/spark-lib/src/rad.rs:833)
- 从内存树得到 `child_count` / `child_start`：[gsplat.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/spark-lib/src/gsplat.rs:973)

## 2. 最简单的 PLY 里有什么

普通 3DGS PLY 不是 LoD 文件。它更像一个“裸高斯点列表”。

Spark 期望的普通 3DGS PLY 字段大致是：

```text
element vertex N
property float x
property float y
property float z
property float scale_0
property float scale_1
property float scale_2
property float rot_0
property float rot_1
property float rot_2
property float rot_3
property float opacity
property float f_dc_0
property float f_dc_1
property float f_dc_2
property float f_rest_0
property float f_rest_1
...
```

源码里 PLY writer 也是按这个字段顺序写的：

位置：[ply.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/spark-lib/src/ply.rs:1280)

PLY decoder 会把这些字段映射成内部 splat 属性：

| PLY 字段 | 内部含义 |
| --- | --- |
| `x, y, z` | 高斯中心 `center` |
| `scale_0, scale_1, scale_2` | 三轴尺度 `scale` |
| `rot_0..rot_3` | 旋转四元数 `quat` |
| `opacity` | 不透明度 |
| `f_dc_0..2` | 基础颜色 |
| `f_rest_*` | 球谐高阶颜色系数 |

字段读取位置：[ply.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/spark-lib/src/ply.rs:913)

这一阶段得到的是一个 `splats` 数组。此时它还不是 LoD 树，没有父子关系。

## 3. build-lod 主流程

`.ply -> .rad` 的主流程在 `build-lod` 里。

位置：[main.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/build-lod/src/main.rs:99)

可以按这条线理解：

```text
读取 .ply
  |
  v
得到原始 splats 数组
  |
  v
过滤无效 splat
  |
  v
生成 LoD 树，给数组追加父节点
  |
  v
重排树节点，让父子节点更适合 chunk 加载
  |
  v
把树关系转成 child_count / child_start
  |
  v
把所有属性写入 RAD chunk
```

源码里对应的几个关键步骤：

- 读取输入文件：[main.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/build-lod/src/main.rs:100)
- 过滤 opacity、scale、quat 无效的 splat：[main.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/build-lod/src/main.rs:146)
- 选择 LoD 方法：[main.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/build-lod/src/main.rs:212)
- 调用默认 Quality LoD：[main.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/build-lod/src/main.rs:226)
- 调用 `chunk_tree` 重排：[main.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/build-lod/src/main.rs:240)
- 创建 `RadEncoder`：[main.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/build-lod/src/main.rs:317)

## 4. LoD 树到底是怎么生成的

Spark 默认的 LoD 方法是 `BhattLod { lod_base: 1.75 }`，也就是源码里的 Quality 模式。

位置：[main.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/build-lod/src/main.rs:212)

它的核心思路是：

1. 按 `feature_size` 从小到大排序原始 splat。
2. 从最小尺度开始，一层一层扩大搜索尺度。
3. 在当前尺度下，把 splat 放进 3D 网格。
4. 对每个活跃 splat，只在自己所在格子和周围 26 个邻居格子里找合并对象。
5. 找到最相似的邻居后，两个 splat 合并成一个新的 splat。
6. 新 splat 被追加到数组末尾，并记录它的孩子是哪两个旧 splat。
7. 重复直到只剩一个根节点。

源码里的关键变量：

- `feature_size = 2.0 * max_scale * lod_opacity()`：[tsplat.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/spark-lib/src/tsplat.rs:36)
- 网格坐标 `grid = floor(center / step_size)`：[tsplat.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/spark-lib/src/tsplat.rs:40)
- 默认 Quality 的每层 `step = 2^level`：[bhatt_lod.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/spark-lib/src/bhatt_lod.rs:37)
- 搜索 3x3x3 邻域：[bhatt_lod.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/spark-lib/src/bhatt_lod.rs:78)
- 根据 `similarity` 找最佳合并对象：[bhatt_lod.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/spark-lib/src/bhatt_lod.rs:85)
- 合并生成新 splat：[bhatt_lod.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/spark-lib/src/bhatt_lod.rs:98)

这里的“合并”不是简单取平均位置。`new_merged` 会用面积乘 opacity 作为权重，计算新的 center、rgb、协方差、scale、rotation、opacity。

位置：[gsplat.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/spark-lib/src/gsplat.rs:291)

合并后的节点会被加入 `splats` 数组末尾：

位置：[gsplat.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/spark-lib/src/gsplat.rs:407)

同时记录它的孩子：

位置：[gsplat.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/spark-lib/src/gsplat.rs:408)

所以 LoD 树不是凭空来的。它是在原始 PLY splat 之上，不断追加“合并 splat”形成的。

## 5. LoD 树生成后还会被裁剪

上面说的是“先生成一棵比较完整的合并树”。但 Spark 不会把所有中间合并节点都保留下来。

默认 Quality LoD 后面还有一个 pruning 过程：

```text
叶子节点一定保留
根节点一定保留
中间节点只有足够“比孩子更粗”时才保留
```

判断条件是：

```text
当前节点 feature_size >= 最大孩子 feature_size * lod_base
```

默认 `lod_base = 1.75`。

位置：[bhatt_lod.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/spark-lib/src/bhatt_lod.rs:174)

如果某个中间节点不够“有层级差”，Spark 会把它删掉，让它的孩子直接往上接。这样最终树不是严格二叉树，一个父节点可能有多个孩子。

这解释了一个很重要的问题：为什么最后 RAD 里只需要 `child_count`，而不是固定写两个孩子？因为 pruning 后的 LoD 树不保证每个内部节点都是 2 个孩子。

源码还限制了一个节点孩子数量不能超过 65535，因为 `child_count` 用 `u16` 存：

位置：[bhatt_lod.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/spark-lib/src/bhatt_lod.rs:179)

## 6. 树怎么被摊平成数组

LoD 生成后，Spark 要把树摊平成数组。这样 RAD 才能按 chunk 存储。

前面那个小例子：

```text
Root
|
+-- P1
|   +-- A
|   +-- B
|
+-- P2
    +-- C
    +-- D
```

可以摊平成：

```text
index: 0     1   2   3  4  5  6
node:  Root  P1  P2  A  B  C  D
```

摊平后，每个节点的孩子必须尽量变成连续的一段。因为只有连续，才能用 `child_start + child_count` 表示。

Spark 在两个地方会调整孩子索引：

1. `bhatt_lod` 输出阶段会先把 root 放到 index 0，并递归重写 children。
2. `chunk_tree` 会再次重排，让父子关系更适合 65536 splat 的 chunk 加载。

`bhatt_lod` 输出 root-first 顺序的位置：

位置：[bhatt_lod.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/spark-lib/src/bhatt_lod.rs:224)

重写 children 为连续 index 的位置：

位置：[bhatt_lod.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/spark-lib/src/bhatt_lod.rs:211)

`chunk_tree` 也会做同样的连续化：

位置：[chunk_tree.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/spark-lib/src/chunk_tree.rs:431)

最后 `splats.permute(&indices)` 会真的按新顺序重排整个 splat 数组：

位置：[chunk_tree.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/spark-lib/src/chunk_tree.rs:488)

这一步非常关键。RAD 文件里没有保存复杂的指针树，它只保存“已经被整理好的数组”。因为数组顺序已经整理好了，所以一个节点只需要记：

```text
child_start = 第一个孩子的数组下标
child_count = 一共有几个连续孩子
```

## 7. RAD 是怎么存这棵树的

现在回到文件。

如果最终 splat 数组是：

```text
index  node
0      Root
1      P1
2      P2
3      A
4      B
5      C
6      D
```

那么 RAD 不会写一段类似这样的嵌套 JSON：

```json
{
  "Root": ["P1", "P2"],
  "P1": ["A", "B"],
  "P2": ["C", "D"]
}
```

它会把树当成 splat 的两个属性列写进 chunk：

```text
child_count: 2, 2, 2, 0, 0, 0, 0
child_start: 1, 3, 5, 0, 0, 0, 0
```

编码器只有在 `getter.has_lod_tree()` 为 true 时才写这两个属性：

位置：[rad.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/spark-lib/src/rad.rs:891)

其中：

- `child_count` 编码成 `u16`。
- `child_start` 编码成 `u32`。
- 两者都会作为独立 property payload 压缩写入。

写入函数：

- `encode_chunk_child_count`：[rad.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/spark-lib/src/rad.rs:817)
- `encode_chunk_child_start`：[rad.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/spark-lib/src/rad.rs:833)

读取时，decoder 反过来读这两列：

- 读 `child_count`：[rad.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/spark-lib/src/rad.rs:1768)
- 读 `child_start`：[rad.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/spark-lib/src/rad.rs:1775)

内存里重建 children 时，也是通过“从 child_start 开始连续 child_count 个 index”恢复：

位置：[gsplat.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/spark-lib/src/gsplat.rs:875)

## 8. RAD 文件本身长什么样

现在可以再看 RAD 文件结构。它分两层。

第一层是 `.rad` 文件头：

```text
RAD_MAGIC
global_meta_json_length
global_meta_json
padding_to_8_bytes
chunk_0
chunk_1
...
```

外层 meta 里最重要的是 chunk 表：

```json
{
  "version": 1,
  "type": "gsplat",
  "count": 7,
  "maxSh": 3,
  "lodTree": true,
  "chunkSize": 65536,
  "chunks": [
    { "offset": 0, "bytes": 12345 }
  ]
}
```

真实文件里 `count` 通常很大，这里用 7 只是为了对应前面的小树。

第二层是每个 RADC chunk：

```text
RAD_CHUNK_MAGIC
chunk_meta_json_length
chunk_meta_json
padding_to_8_bytes
payloadBytes
payload for center
payload for alpha
payload for rgb
payload for scales
payload for orientation
payload for sh1/sh2/sh3
payload for child_count
payload for child_start
```

chunk meta 会说明每个 payload 在哪里、多少字节、怎么解码：

```json
{
  "version": 1,
  "base": 0,
  "count": 7,
  "payloadBytes": 9999,
  "maxSh": 3,
  "lodTree": true,
  "properties": [
    { "offset": 0, "bytes": 1000, "property": "center", "encoding": "f32_lebytes", "compression": "gz" },
    { "offset": 1000, "bytes": 300, "property": "alpha", "encoding": "r8", "compression": "gz", "min": 0, "max": 2 },
    { "offset": 1300, "bytes": 800, "property": "rgb", "encoding": "r8_delta", "compression": "gz", "min": 0, "max": 1 },
    { "offset": 2100, "bytes": 700, "property": "scales", "encoding": "ln_0r8", "compression": "gz", "min": -12, "max": 9 },
    { "offset": 2800, "bytes": 600, "property": "orientation", "encoding": "oct88r8", "compression": "gz" },
    { "offset": 3400, "bytes": 100, "property": "child_count", "encoding": "u16", "compression": "gz" },
    { "offset": 3500, "bytes": 100, "property": "child_start", "encoding": "u32", "compression": "gz" }
  ]
}
```

这只是结构示意，不是真实字节数。

写 chunk meta 和 payload 的位置：

位置：[rad.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/spark-lib/src/rad.rs:904)

## 9. 为什么 RAD 要分 chunk

RAD 默认每 65536 个 splat 一个 chunk。

位置：[rad.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/spark-lib/src/rad.rs:523)

原因是 Spark runtime 不想一开始加载完整模型。它会先读 `.rad` 文件开头的 global meta，知道每个 chunk 的位置和大小。之后根据相机位置和 LoD 遍历结果，只请求当前需要的 chunk。

浏览器端读取 header 的地方：

位置：[SplatPager.ts](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/src/SplatPager.ts:112)

如果 header 不够，它会尝试读取 64 KiB、256 KiB、1 MiB：

位置：[SplatPager.ts](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/src/SplatPager.ts:132)

请求具体 chunk 时，如果 chunk 内嵌在同一个 `.rad` 文件中：

```text
真实 offset = chunksStart + meta.chunks[chunk].offset
读取长度 = meta.chunks[chunk].bytes
```

位置：[SplatPager.ts](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/src/SplatPager.ts:176)

然后通过 HTTP Range 请求：

位置：[SplatPager.ts](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/src/SplatPager.ts:1543)

这就是 RAD 格式和浏览器流式加载直接绑定的地方。

## 10. 单文件 RAD 和拆分 RAD

Spark 支持两种 RAD 输出：

```text
--rad
```

生成一个 `.rad` 文件。global meta 后面直接跟所有 RADC chunk。

```text
--rad-chunked
```

生成一个主 `.rad` 文件和多个 `.radc` 文件。主 `.rad` 文件只放 global meta，每个 chunk 的 bytes 写到单独 `.radc` 文件中。

源码位置：[main.rs](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/rust/build-lod/src/main.rs:359)

区别在 global meta 的 `chunks` 表：

单文件 RAD：

```json
{ "offset": 0, "bytes": 12345 }
```

拆分 RAD：

```json
{ "offset": 0, "bytes": 12345, "filename": "model-lod-0.radc" }
```

浏览器端看到 `filename` 后，会直接请求外部 `.radc` 文件：

位置：[SplatPager.ts](D:/Documents/Project/Python_project/LinJG/3dgs-format-research/sources/spark-src/src/SplatPager.ts:178)

## 11. RAD 的设计理念

现在把它压缩成一句话：

RAD 是一个“先用 JSON 建目录，再用二进制 chunk 存属性列，并把 LoD 树压成 `child_count` / `child_start` 两列”的 3DGS 流式容器格式。

它和普通 PLY 的差异可以这样理解：

| 格式 | 主要形态 | 是否天然适合流式 LoD |
| --- | --- | --- |
| 普通 PLY | 一行一个原始 splat | 不适合 |
| Spark RAD | 一组 chunk，每个 chunk 里是属性列和 LoD 树关系 | 适合 |

普通 PLY 关注的是“把训练出来的高斯点保存下来”。RAD 关注的是“浏览器如何快速看到粗略结果，再随着相机视角加载细节”。

所以 RAD 做了三件 PLY 没有做的事：

1. 它增加了离线生成的 LoD 父节点。
2. 它把树关系存成紧凑的连续数组引用。
3. 它把文件切成可以按需请求的 chunk。

## 12. 最后再串一次完整流程

从 `.ply` 到 `.rad`，可以这样记：

```text
1. PLY 读入
   原始点 A, B, C, D

2. LoD 生成
   A + B -> P1
   C + D -> P2
   P1 + P2 -> Root

3. 树裁剪
   删除不值得保留的中间节点，让层级更简洁

4. 树重排
   Root, P1, P2, A, B, C, D

5. 树关系变成两列
   child_count = [2, 2, 2, 0, 0, 0, 0]
   child_start = [1, 3, 5, 0, 0, 0, 0]

6. RAD chunk 写入
   center
   alpha
   rgb
   scales
   orientation
   sh1/sh2/sh3
   child_count
   child_start

7. 浏览器加载
   先读 RAD header
   再根据相机和 LoD 遍历结果请求需要的 chunk
```

如果只记一个最重要的点，就是：

RAD 里的 LoD 树不是单独一坨树 JSON，也不是指针结构。它是“已经排好顺序的 splat 数组 + 每个节点两列孩子信息”。这个设计让 runtime 可以用很少的数据判断：当前节点要不要展开，展开时应该请求哪些 chunk。

