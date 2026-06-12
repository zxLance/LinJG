# PLY 到 W3GS 转换器

这个工具把常见 3D Gaussian Splatting PLY 转换成 W3GS 使用的：

```text
scene.w3gs.json
nodes.w3gs.json
chunks.w3gs.json
payload/chunks-*.bin
```

它是项目中的正式数据工程工具，不是临时脚本。当前重点服务两类 demo：

- `demos/w3gs-experiment-platform/`：验证 node / layer / chunk 调度结构。
- `demos/w3gs-webgpu-viewer/`：验证 SH0/SH3 raw payload 能进入 WebGPU buffer 并形成可见画面。

正式 SH3 profile 规范见 [`../../notes/format-cases/w3gs-0.1-payload-profiles.md`](../../notes/format-cases/w3gs-0.1-payload-profiles.md)。raw float32 profile 是便于验证、保留 Graphdeco SH3 渲染语义的 reference layout，不是生产压缩方案，也不是原 PLY 所有字段的位级副本。

## 推荐用法

论文实验建议使用 `parent-summary`：

```powershell
python convert_ply_to_w3gs.py `
  --input "D:\DATA\3DGS\PLY\point_cloud.ply" `
  --output "..\..\demos\w3gs-from-ply\point_cloud_parent_summary" `
  --max-splats 200000 `
  --lod-mode parent-summary `
  --payload-profile raw-gaussian-sh3-v0
```

保留旧 Prototype 1 baseline：

```powershell
python convert_ply_to_w3gs.py `
  --input "D:\DATA\3DGS\PLY\point_cloud.ply" `
  --output "..\..\demos\w3gs-from-ply\point_cloud" `
  --max-splats 200000 `
  --lod-mode duplicated-parent `
  --payload-profile raw-gaussian-v0
```

查看 PLY header：

```powershell
python convert_ply_to_w3gs.py `
  --input "D:\DATA\3DGS\PLY\point_cloud.ply" `
  --output "..\..\demos\w3gs-from-ply\inspect-unused" `
  --inspect-only
```

## CLI 参数

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| `--input` | 必填 | 输入 PLY 文件路径。 |
| `--output` | 必填 | 输出 W3GS sample 目录。 |
| `--max-splats` | `200000` | 最多转换多少个 splat；大型 PLY 会按顶点序号均匀抽样。 |
| `--max-depth` | `4` | octree 最大深度。 |
| `--max-leaf-splats` | `25000` | 节点超过该数量时继续切分，直到达到最大深度。 |
| `--lod-mode` | `duplicated-parent` | LoD 生成模式：`duplicated-parent` 或 `parent-summary`。 |
| `--base-ratio` | `0.25` | 仅 `duplicated-parent` 使用：base layer 保留 top-importance 比例。 |
| `--min-refinement-splats` | `8000` | 仅 `duplicated-parent` 使用：低于该数量只写 base layer。 |
| `--summary-target-ratio` | `0.08` | 仅 `parent-summary` 使用：internal node summary 数量相对 source splat 的目标比例。 |
| `--summary-max-splats` | `12000` | 仅 `parent-summary` 使用：单个 internal node 的 summary splat 上限。 |
| `--payload-profile` | `auto` | `auto`、`raw-gaussian-v0` 或 `raw-gaussian-sh3-v0`。完整 SH3 输入在 auto 下选择 SH3。 |
| `--payload-file-max-mb` | `64` | `payload/chunks-*.bin` 接近该大小时切换到下一个 payload 文件。 |
| `--inspect-only` | 关闭 | 只打印 PLY header 摘要，不执行转换。 |

当前默认仍是 `duplicated-parent`，是为了不破坏已有 demo。论文和后续实验应显式使用 `--lod-mode parent-summary`。

## 支持的 PLY

当前支持：

- `format binary_little_endian 1.0`
- `format ascii 1.0`，仅限标量 vertex 属性

3DGS PLY 需要包含：

```text
x y z
f_dc_0 f_dc_1 f_dc_2
opacity
scale_0 scale_1 scale_2
rot_0 rot_1 rot_2 rot_3
```

profile 选择规则：

- `auto`：恰好包含 `f_rest_0..44` 时选择 SH3；完全没有 `f_rest` 时选择 SH0；残缺或额外的 `f_rest` 集合直接报错。
- `raw-gaussian-sh3-v0`：强制要求完整的 45 个高阶系数。
- `raw-gaussian-v0`：允许显式降阶，丢弃高阶 SH。转换 metadata 会记录 `shDowncast=true`，不会静默发生。

若输入只有残缺或非标准的 `f_rest_*`，`auto`/SH3 会拒绝；只有显式选择 SH0 才允许忽略这些字段。此时 metadata 记录 `inputShState=partial-or-nonstandard`、`inputShDegree=null`、`shDowncast=true` 和 `ignoredShRestCount`。

## raw-gaussian-v0 Payload

每个 splat 是 14 个 little-endian `float32`，共 56 bytes：

| float 偏移 | byte 偏移 | 字段 | 分量数 | 来源 |
| --- | --- | --- | --- | --- |
| 0 | 0 | position | 3 | PLY `x/y/z` |
| 3 | 12 | scale | 3 | `exp(scale_0..2)` |
| 6 | 24 | rotation | 4 | 归一化 `rot_0..3` |
| 10 | 40 | opacity | 1 | `sigmoid(opacity)` |
| 11 | 44 | color | 3 | `clamp(0.5 + C0 * f_dc_*)` |

## raw-gaussian-sh3-v0 Payload

每个 splat 是 59 个 little-endian `float32`，共 236 bytes：

| float 偏移 | byte 偏移 | 字段 | 分量数 | 来源 |
| ---: | ---: | --- | ---: | --- |
| 0 | 0 | position | 3 | PLY `x/y/z` |
| 3 | 12 | scale | 3 | `exp(scale_0..2)` |
| 6 | 24 | rotation | 4 | 归一化 `(w,x,y,z)` |
| 10 | 40 | opacity | 1 | `sigmoid(opacity)` |
| 11 | 44 | shDc | 3 | 原始 `f_dc_0..2` |
| 14 | 56 | shRest | 45 | `R.c1..c15, G.c1..c15, B.c1..c15` |

`f_rest` 的 channel-major 顺序来自 Graphdeco 官方 PLY save/load 实现，不是根据字段名猜测。完整公式、方向和来源链接见 profile 规范。

边界说明：position 与 48 个 SH 系数在 float32 输入上直接写出；scale、opacity、rotation 写出 Graphdeco 激活后的运行时值。当前 `safe_exp` 会把 log-scale 限制到 `[-20,20]` 后再求指数，normal 不写入 payload，因此不要把该 profile 描述为任意 PLY 的“信息等价”转换。

## 空间层级

转换器基于 position 构建简单 octree：

1. `root` 包含全部被选中的 splat。
2. 按节点 AABB 中心切成最多 8 个 octant。
3. 当 `len(node) > --max-leaf-splats` 且未达到 `--max-depth` 时继续切分。
4. `nodes.w3gs.json` 显式写出 `parent` / `children`。

输出坐标保持 PLY 本地坐标，JSON 中记录 3D AABB。

## LoD 模式一：duplicated-parent

这是早期 Prototype 1 baseline。每个 node 都从自己子树覆盖的原始 splats 中直接写 payload：

1. 计算 importance：

```text
importance = sigmoid(opacity) * max(exp(scale_0), exp(scale_1), exp(scale_2))
```

2. 每个 node 按 importance 排序。
3. 如果 node splat 数不少于 `--min-refinement-splats`：
   - `base` 写 top `--base-ratio`
   - `r1` 写剩余 splats
4. 小 node 只写一个 `base`。

这个模式会让同一个输入 splat 出现在 parent、internal、leaf 多个 payload 中。它适合做调度 baseline，不适合作为论文推荐 LoD 策略。

## LoD 模式二：parent-summary

这是当前推荐的正式实验模式。

核心语义：

```text
leaf 保存原始 fine splats；
internal / parent 保存 synthetic summary splats；
parent-child refinement 使用 replacement；
每个原始 splat 只归属一个 leaf。
```

第一版 summary 生成使用 `grid-cluster-merge-v0`：

1. 收集当前 internal node 子树覆盖的原始 splats。
2. 在 node 局部 AABB 中建立三维 grid。
3. grid 尺寸由 `--summary-target-ratio` 和 `--summary-max-splats` 决定。
4. 每个非空 cell 聚合成一个 synthetic summary splat。

聚合规则：

| 字段 | 生成方式 |
| --- | --- |
| position | `opacity * max(scale)^2` 加权均值。 |
| scale | 加权均值、cluster 最大 scale、cluster 空间范围三者取保守较大值。 |
| rotation | 暂取 cluster 中权重最高 splat 的 rotation。 |
| opacity | 使用 alpha compositing 近似 `1 - prod(1 - alpha_i)`，并 clamp 到 `0.98`。 |
| color / SH0 | importance 加权 DC color 均值。 |
| SH3 | 在同一坐标基底中逐系数进行 importance 加权平均，方法标记为 `importance-weighted-coefficient-average-v0`。 |
| sourceCount | 记录 cell 覆盖的原始 splat 数，当前写在 layer/chunk/node 聚合 metadata 中。 |
| approxError | 使用 position RMS + color RMS proxy。 |
| geometricError | 使用 cluster 空间范围和 position RMS 的保守 proxy。 |

这个算法不是最优 3DGS 压缩算法。它的目标是让 W3GS 格式层能显式表达 leaf fine data、parent summary data、replacement refinement 和可解释 LoD metadata。

SH3 summary 虽然保留了 48 个系数的布局，但系数平均不等于对多个 Gaussian 辐射贡献的精确合并。它是 LoD 生成近似，不是 payload profile 的格式规定，也不能据此宣称视觉等价。

## 输出 Metadata

`scene.w3gs.json` 的 `converter.statistics` 会写入：

- `sourceVertexCount`
- `convertedSplats`
- `leafOriginalSplats`
- `internalSummarySplats`
- `totalPayloadSplats`
- `duplicateRatio`
- `originalDuplicateRatio`
- `summaryOverhead`
- `totalStorageOverhead`
- `firstRenderBytes`
- `payloadBytes`
- `nodeCount`
- `chunkCount`

profile 选择还会记录 `inputShState`、`inputShDegree`、`outputShDegree`、`shDowncast` 和 `ignoredShRestCount`，用于区分完整 SH3、纯 SH0 与显式忽略残缺高阶字段的情况。

`parent-summary` 模式还会在 node / layer / chunk 中尽量写入：

- `lodRole`: `summary` 或 `leaf`
- `summaryMethod`: `grid-cluster-merge-v0`
- `summaryShMethod`: `importance-weighted-coefficient-average-v0`（仅 SH3 summary）
- `sourceSplatCount`
- `summarySplatCount`
- `refinementMode`: `replacement`
- `approxError`
- `geometricError`
- `storageOverhead`
- `targetRatio`
- `gridSize`

这些字段都是附加 metadata，不会破坏现有 experiment platform 或 WebGPU viewer 的读取逻辑。

## Git 管理

payload 二进制文件可能很大，仓库应忽略：

```text
3dgs-format-research/demos/w3gs-from-ply/**/payload/*.bin
```

JSON 可作为 demo manifest 保留；payload 默认视为本地生成产物，除非团队明确要发布小型样例。

## 测试

```powershell
python -m unittest discover -s tools/ply-to-w3gs/tests -v
```
