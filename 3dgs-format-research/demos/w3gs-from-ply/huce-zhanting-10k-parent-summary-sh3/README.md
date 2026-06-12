# HuCeZhanTing 10K W3GS SH3 实验样本

这是统一 10K PLY 子集的 W3GS `parent-summary` + `raw-gaussian-sh3-v0` 正式实验输出，不覆盖既有 SH0 smoke 数据。

## 生成命令

```powershell
python tools/ply-to-w3gs/convert_ply_to_w3gs.py `
  --input datasets/unified-huce-zhanting/HuCeZhanTing-10k-seed20260611.ply `
  --output demos/w3gs-from-ply/huce-zhanting-10k-parent-summary-sh3 `
  --max-splats 10000 `
  --lod-mode parent-summary `
  --max-leaf-splats 2500 `
  --max-depth 4 `
  --payload-profile raw-gaussian-sh3-v0
```

本次 wall time 为 0.868374 s。Windows 标准库路径未可靠记录 peak RSS。

## 输出统计

| 指标 | SH3 | 既有 SH0 smoke | 变化 |
| --- | ---: | ---: | ---: |
| bytes/splat | 236 | 56 | 4.214286x |
| nodes / layers / chunks | 25 / 25 / 25 | 25 / 25 / 25 | 不变 |
| leaf original splats | 10,000 | 10,000 | 不变 |
| internal summary splats | 506 | 506 | 不变 |
| total payload splats | 10,506 | 10,506 | 不变 |
| payload bytes | 2,479,416 | 588,336 | +1,891,080 |
| startup bytes | 41,064 | 9,744 | +31,320 |
| summary overhead | 0.0506 | 0.0506 | 不变 |

manifest JSON 共 76,228 bytes。payload SHA-256：

```text
3570fb0fd00e4335afbdba939502ade092d9a9085db016abd8fc7a121513b072
```

## SH3 与 Parent Summary

leaf payload 保留输入 PLY 的完整 `f_dc_0..2` 和 `f_rest_0..44`。internal summary 使用 `importance-weighted-coefficient-average-v0`，即在共同 scene 坐标基底中逐系数加权平均 48 个 SH 系数。

该方法保留 SH3 布局，但只是 LoD 近似：多个 Gaussian 的方向相关辐射贡献通常不能由单个“平均系数” Gaussian 精确替代。它不是 `raw-gaussian-sh3-v0` profile 的格式规定。

## 独立验证

```powershell
python tools/w3gs-validator/validate_w3gs.py `
  demos/w3gs-from-ply/huce-zhanting-10k-parent-summary-sh3 `
  --json-output demos/w3gs-from-ply/huce-zhanting-10k-parent-summary-sh3/validation-report.json
```

结果：0 error、1 warning、1 info。warning 是现有字段无法严格证明 startupSet 在所有 decoder 上的视觉 fallback 完整性，不是 payload 结构错误。

## WebGPU 实测

使用 `demos/w3gs-webgpu-viewer/webgpu_smoke_test.mjs` 启动隔离 Chrome profile 和临时静态服务。为避免本机下载管理器接管 `.bin`，测试服务器仅在运行时把 payload 映射到无扩展名内部 URL；磁盘文件和正式 manifest 均不修改。

实测状态：

- WebGPU ready。
- profile `raw-gaussian-sh3-v0`，SH degree 3。
- loaded chunks 25，replacement active chunks 22。
- active splats 10,000，GPU buffer 2,360,000 bytes。
- 0° 和 180° 相机方位均产生非黑屏 canvas，截图 SHA-256 不同；这只能证明两个视角都成功渲染，不能隔离高阶 SH 效应。
- 测试后 Chrome 进程树和临时监听端口均关闭。

证据位于 `evidence/webgpu-smoke-report.json`、`evidence/sh3-azimuth-0.png` 和 `evidence/sh3-azimuth-180.png`。

这个 viewer 仍是圆片近似，不包含协方差投影、椭圆 Gaussian 积分和透明排序。旧的 0°/180° 截图同时改变几何视角和 SH 观察方向，因此只能作为 payload -> WebGPU -> 非黑屏 canvas 的历史 smoke 证据，不能单独证明 SH3 分支正确。

更新后的 runner 已要求两项更强证据：同一相机、同一 active splats 下切换 full SH3 / DC-only 的截图对照，以及固定合成系数的 CPU reference / WGSL compute 数值对照。只有这两项在目标浏览器上实际通过后，才能把浏览器证据升级为 SH3 计算分支验收；现有 `webgpu-smoke-report.json` 仍是旧版历史报告。
