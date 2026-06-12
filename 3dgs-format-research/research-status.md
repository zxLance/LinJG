# 科研周期状态记录

最后更新：2026-06-12

本文档回答两个问题：研究目前走到哪一步，以及下一步最关键的工作是什么。详细研究逻辑见 `research-plan.md`，接手项目时的操作入口见 `PROJECT-HANDOFF.md`。

## 1. 当前阶段

当前处于：

```text
研究问题与评价体系已经收敛
-> 字段级实验已完成第一版
-> W3GS reference contract 已形成可执行原型
-> 统一数据集与 SH3 基线正在验收
-> 即将进入同源格式转换与受控实验阶段
```

这意味着项目已经离开“选题探索”和“仅做格式笔记”的阶段，但还没有进入可以撰写实验结论的阶段。当前工作的核心是建立公平、可复现的实验基础，而不是证明 W3GS 必然更好。

## 2. 已确定的研究主线

主研究问题：

```text
如何为 Web 3D Gaussian Splatting 定义一个最小、显式、可验证的
streaming contract，使离线 LoD/packing 结果、payload、codec profile
和 runtime scheduling 可以被独立描述、检查和局部替换？
```

W3GS 的定位是 reference contract/profile，不是声称替代 RAD、SOG、LCC2、3D Tiles、glTF 或 SPZ 的新标准，也不把当前 LoD 算法、raw codec 或简化 renderer 当作论文创新点。

## 3. 已完成工作

### 3.1 文献、格式与证据基础

- 已建立 RAD、LCC2、SOG Streaming、Cesium 3D Tiles Gaussian Splat 四个主案例笔记。
- 已建立近年文献综述、发展脉络和前沿格式缺口分析。
- 已保存或抽样四类真实数据，并在 `demos/README.md` 中记录证据边界。
- 已完成字段级 contract gap analysis：`notes/comparisons/existing-format-gap-analysis.md`。

字段级实验的关键结论：

- 四个现有体系都已经显式表达部分 streaming contract，不存在“现有格式完全没有 contract”的结论。
- Cesium 组合在标准化、互操作和 conformance 上最完整。
- RAD、SOG、LCC2 的若干调度或 refinement 语义仍主要位于特定 runtime/toolchain。
- W3GS 字段覆盖较完整，但字段存在不等于性能、可插拔性或 runtime hint 有效性已经被证明。

### 3.2 W3GS reference implementation

当前已有：

- PLY -> W3GS converter：`tools/ply-to-w3gs/`。
- 独立 conformance checker：`tools/w3gs-validator/`。
- 原生 WebGPU prototype viewer：`demos/w3gs-webgpu-viewer/`。
- `duplicated-parent` 与 `parent-summary` 两种 reference LoD 生成模式。
- SH0 `raw-gaussian-v0` 和 SH3 `raw-gaussian-sh3-v0` 两个 raw reference profile。

Conformance 状态：

- Converter tests：6/6 通过。
- Validator tests：19/19 通过。
- 10K SH3 数据：0 error、1 warning、1 info。
- 当前可称为 repository-level independent reference checker and conformance tests。
- 不能称为标准认证级或完整 codec/renderer conformance suite。

### 3.3 统一源数据集

统一源：

```text
D:\DATA\3DGS\PLY\HuCeZhanTing.ply
```

已冻结信息：

| 项目 | 数值 |
| --- | ---: |
| 文件大小 | 701,875,230 bytes / 669.36 MiB |
| Gaussian 数量 | 2,830,135 |
| 属性数 | 62 |
| SH 阶数 | SH3 |
| SHA-256 | `a4624ae67bf4d7f0764b714531f1cc21707ce2b9fa936a5fc6d85dd9cea64cea` |

已实现确定性嵌套采样器：`tools/ply-sampler/`。

- 固定 seed：`20260611`。
- 10K 是 250K 的严格子集。
- 62 个属性、属性顺序和原始 record bytes 保持不变。
- manifest：`datasets/unified-huce-zhanting/dataset-manifest.json`。
- 大型 PLY 与 payload 已加入 `.gitignore`。
- 源数据和派生子集的再分发许可尚未确认，当前只可用于本地研究。

### 3.4 W3GS SH3 基线

正式 profile：`raw-gaussian-sh3-v0`。

- 59 个 little-endian float32。
- 236 bytes/splat。
- 保存 position、linear scale、normalized wxyz rotation、alpha、3 个 DC 系数和 45 个高阶 SH 系数。
- `f_rest` 顺序依据 Graphdeco 官方 save/load：`R.c1..c15, G.c1..c15, B.c1..c15`。
- profile 规范：`notes/format-cases/w3gs-0.1-payload-profiles.md`。

10K SH3 样本：

```text
demos/w3gs-from-ply/huce-zhanting-10k-parent-summary-sh3/
```

| 指标 | 结果 |
| --- | ---: |
| nodes / layers / chunks | 25 / 25 / 25 |
| leaf splats | 10,000 |
| summary splats | 506 |
| payload | 2,479,416 bytes |
| startup bytes | 41,064 |
| summary overhead | 5.06% |

逐值审计确认 10,000 个 leaf 的 48 个 SH 系数零误差保留。scale、rotation、opacity 只有 float32 量级误差；该样本没有触发 `safe_exp` 截断。

## 4. 当前未完成与阻塞

### 4.1 WebGPU SH3 增强验收未完成

已实现但尚未跑通的增强证据：

- 同一相机、同一 active set 下 full SH3 与 DC-only 截图对照。
- 59-float synthetic fixture 的 CPU Graphdeco reference 与 WGSL compute 数值对照，目标误差 `<= 1e-5`。

最后已知失败命令：

```powershell
node demos/w3gs-webgpu-viewer/webgpu_smoke_test.mjs
```

Chrome 和 Edge 均报告：

```text
Target crashed
```

准确崩溃阶段尚未定位。首要怀疑点是 `verifyShReference()` 中 compute submission、readback 或 `mapAsync` 生命周期，但目前没有运行证据，不能定性。旧 `evidence/webgpu-smoke-report.json` 只是历史的双视角成功报告，不能作为增强 SH3 正确性证据。

### 4.2 同源对比链路尚未生成

当前工具链结论：

| 格式 | 同源 PLY 转换状态 |
| --- | --- |
| W3GS | 10K SH3 格式/属性/conformance 基线已完成；增强浏览器验收待完成。 |
| SOG Streaming | 官方 `@playcanvas/splat-transform@2.5.2` 可行，尚未安装和 smoke test。 |
| Spark RAD | 官方 Spark `build-lod` 可行，尚未安装 Rust、编译和 smoke test。 |
| XGRIDS LCC2 | 未发现公开可复现 PLY -> LCC2 writer，暂不进入同源实验。 |
| Cesium 3D Tiles 3DGS | 未发现公开可复现 PLY Gaussian HLOD tiler，暂不进入同源实验。 |

### 4.3 公平实验尚缺的共同条件

- 统一 SH3 语义与质量目标。
- 相同的 10K、250K 和完整源输入。
- 固定转换器版本、参数和命令。
- 统一网络、缓存、相机路径和测量 instrumentation。
- 区分“格式 contract 实验”和“端到端工具链实验”，不能把 LoD、codec、renderer 差异全部归因于格式。

## 5. 下一步顺序

严格按以下顺序推进：

1. 定位并修复 WebGPU `Target crashed`，完成同相机 full/DC 与 CPU/WGSL fixture 证据。
2. 更新 SH3 样本的 `webgpu-smoke-report.json` 和实验报告，明确旧报告失效。
3. 经用户授权安装 `@playcanvas/splat-transform@2.5.2`，先跑 10K 静态 SOG，再生成真正的 SOG Streaming `lod-meta.json`。
4. 经用户授权安装 Rust stable，在 Spark commit `82fc4a9d9596837ad602637ed7430caa60662331` 上构建 `build-lod`，生成 10K SH3 chunked RAD。
5. 对 W3GS、SOG Streaming、RAD 做 10K 结构与属性 smoke 对齐。
6. 扩大到 250K，记录转换时间、峰值 RSS、临时/最终磁盘、属性保留、chunk 数和 startup bytes。
7. 250K 稳定后再决定是否跑完整 2.83M。
8. 完成 runtime instrumentation 后再做首屏、请求、overfetch、GPU memory 和 time-to-quality 实验。

## 6. 当前不能下的结论

- 不能说 W3GS 是评价体系下最好的格式。
- 不能用 SH0 与其他格式的 SH3 结果做正式容量或画质比较。
- 不能把 raw SH3 payload 当成生产压缩方案。
- 不能说 WebGPU SH3 高阶计算已经通过增强独立验收。
- 不能把 LCC2 或 Cesium 强行纳入当前同源端到端性能排名。
- 不能把 `parent-summary` 写成 W3GS 必须采用或最优的 LoD 算法。

## 7. 当前一句话判断

```text
研究已经完成问题收敛、字段级比较、W3GS contract 原型、独立 validator、
统一数据采样和 SH3 格式基线；当前卡在浏览器 SH3 增强验收，
通过后即可进入 SOG/RAD 同源 10K 转换实验。
```

