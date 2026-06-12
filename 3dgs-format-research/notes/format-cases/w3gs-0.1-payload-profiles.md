# W3GS 0.1 Raw Gaussian Payload Profiles

本文定义 W3GS 0.1 的两个无压缩 reference payload profile。它们用于格式验证、转换链路和公平实验，不是生产压缩方案。`raw-gaussian-sh3-v0` 的目标是保留 Graphdeco 渲染所需的完整 SH3 语义，不应简称为输入 PLY 的逐字段“信息等价”副本。

## Profile 标识与版本

- `raw-gaussian-v0`：既有 SH0 profile，56 bytes/splat。
- `raw-gaussian-sh3-v0`：新增完整 SH3 profile，236 bytes/splat。

profile id 是解码契约的一部分。新增字段、改变排列或改变数据域时必须使用新 id，不能在原 id 下静默扩展。

## 共同数据域

两个 profile 都使用 little-endian、紧密排列的 IEEE 754 `float32`；字段按 4 bytes 对齐，记录内部没有 padding。

| 字段 | 数据域 |
| --- | --- |
| position | PLY `x/y/z` 原值，保持 scene 声明的坐标空间。 |
| scale | 线性主轴尺度 `exp(scale_0..2)`，不是 PLY 中的 log-scale。 |
| rotation | 归一化 quaternion，顺序 `(w, x, y, z)`，对应 PLY `rot_0..3`。 |
| opacity | `sigmoid(PLY opacity)` 后的线性 alpha，范围 `[0,1]`。 |

## raw-gaussian-v0

| byte offset | 字段 | 类型 | components |
| ---: | --- | --- | ---: |
| 0 | position | float32 | 3 |
| 12 | scale | float32 | 3 |
| 24 | rotation | float32 | 4 |
| 40 | opacity | float32 | 1 |
| 44 | color | float32 | 3 |

stride 为 56 bytes。`color` 是已经由 DC 系数恢复并 clamp 的 SH0 线性 RGB：

```text
color = clamp(0.5 + C0 * f_dc, 0, 1)
C0 = 0.28209479177387814
```

## raw-gaussian-sh3-v0

| byte offset | float offset | 字段 | 类型 | components |
| ---: | ---: | --- | --- | ---: |
| 0 | 0 | position | float32 | 3 |
| 12 | 3 | scale | float32 | 3 |
| 24 | 6 | rotation | float32 | 4 |
| 40 | 10 | opacity | float32 | 1 |
| 44 | 11 | shDc | float32 | 3 |
| 56 | 14 | shRest | float32 | 45 |

stride 为 236 bytes，共 59 个 float32。`shDc` 和 `shRest` 保存训练/PLY 中的原始 SH 系数，不预先恢复为 RGB。

position 与 SH 系数在 float32 输入上可逐值保留；scale、opacity 和 rotation 则分别经过 `exp`、`sigmoid` 和 quaternion normalize 后写入。PLY normal 不属于 Graphdeco Gaussian rasterization 的运行时属性，也不进入该 profile。具体 converter 还必须披露任何数值保护或截断；当前 reference converter 的 `safe_exp` 对 log-scale 使用 `[-20,20]` 保护，因此 profile 可称“渲染语义保留”，不能笼统称为任意输入上的位级或信息等价。

### SH 排列

每个颜色通道有 16 个系数，基函数序号为 `c0..c15`，degree 分段为 `1 + 3 + 5 + 7`。payload 排列为：

```text
shDc   = [R.c0, G.c0, B.c0]
shRest = [R.c1..R.c15, G.c1..G.c15, B.c1..B.c15]
```

这与官方 Graphdeco 3D Gaussian Splatting PLY 导出一致：内部 `_features_rest` 为 `[N, 15, 3]`，保存时执行 `transpose(1, 2).flatten(start_dim=1)`，因此 `f_rest_0..44` 是 channel-major；读取时也先 reshape 为 `[N, 3, 15]` 再 transpose 回内部布局。

### 方向、基函数与颜色恢复

观察方向必须在 Gaussian position 与 camera position 所在的同一坐标空间中计算：

```text
dir = normalize(position - cameraPosition)
```

即 camera-to-Gaussian 方向，不是其相反方向。实 SH 基函数及正负号严格采用 Graphdeco `utils/sh_utils.py::eval_sh` 的 degree 0..3 顺序。设 `x=dir.x, y=dir.y, z=dir.z`：

```text
Y0  =  C0
Y1  = -C1*y
Y2  =  C1*z
Y3  = -C1*x
Y4  =  C2[0]*x*y
Y5  =  C2[1]*y*z
Y6  =  C2[2]*(2*z*z-x*x-y*y)
Y7  =  C2[3]*x*z
Y8  =  C2[4]*(x*x-y*y)
Y9  =  C3[0]*y*(3*x*x-y*y)
Y10 =  C3[1]*x*y*z
Y11 =  C3[2]*y*(4*z*z-x*x-y*y)
Y12 =  C3[3]*z*(2*z*z-3*x*x-3*y*y)
Y13 =  C3[4]*x*(4*z*z-x*x-y*y)
Y14 =  C3[5]*z*(x*x-y*y)
Y15 =  C3[6]*x*(x*x-3*y*y)
```

常量：

```text
C0 = 0.28209479177387814
C1 = 0.4886025119029199
C2 = [1.0925484305920792, -1.0925484305920792,
      0.31539156525252005, -1.0925484305920792,
      0.5462742152960396]
C3 = [-0.5900435899266435, 2.890611442640554,
      -0.4570457994644658, 0.3731763325901154,
      -0.4570457994644658, 1.445305721320277,
      -0.5900435899266435]
```

每通道颜色为：

```text
linearRgb = max(0, 0.5 + sum(ci * Yi, i=0..15))
```

最终 framebuffer/display 输出可再 clamp 到 `[0,1]`；sRGB 编码属于 renderer/presentation，不属于 payload profile。

## 兼容与降阶

- SH3 reader 必须依据 codec/schema 分派，不能把 236-byte 记录当成 SH0。
- SH3 降为 SH0 时丢弃 `c1..c15`，并按 `clamp(0.5 + C0*c0, 0, 1)` 生成 `raw-gaussian-v0.color`。
- SH0 不能无损升级为 SH3。需要形式升级时可令高阶系数为 0，但必须标记为 synthesized/SH0-derived，不能声称保留原始 SH3。

## Parent Summary 约定边界

profile 只规定单个 splat 的编码，不规定 LoD summary 算法。当前 converter 的 `parent-summary` 对 SH3 使用 `importance-weighted-coefficient-average-v0`：在同一 scene 坐标基底中逐系数加权平均全部 48 个 SH 系数。它保持完整 SH3 布局，但只是 LoD 近似，不保证合并后辐射场与原 Gaussian 集合视觉等价。

## 依据

- Graphdeco Gaussian model PLY save/load：<https://github.com/graphdeco-inria/gaussian-splatting/blob/main/scene/gaussian_model.py>
- Graphdeco quaternion/scaling activation：<https://github.com/graphdeco-inria/gaussian-splatting/blob/main/utils/general_utils.py>
- Graphdeco SH 常量、顺序和公式：<https://github.com/graphdeco-inria/gaussian-splatting/blob/main/utils/sh_utils.py>
- Graphdeco renderer 的观察方向和 `+0.5`/clamp：<https://github.com/graphdeco-inria/gaussian-splatting/blob/main/gaussian_renderer/__init__.py>
