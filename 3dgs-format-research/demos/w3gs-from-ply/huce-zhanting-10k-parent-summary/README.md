# HuCeZhanTing 10K W3GS Smoke Test

这是统一数据集实验第一阶段的 W3GS 10K smoke 输出，不覆盖既有 W3GS 样本。

## 输入

```text
datasets/unified-huce-zhanting/HuCeZhanTing-10k-seed20260611.ply
```

- 10,000 vertices。
- 62 个原始属性。
- SHA-256：`f72bd6268c12a1ddab79d9ebbcdfbbf29c275fc08395656ae9b8ed433f108cb4`。
- 保留 SH3；它是同目录 250K 子集的严格子集。

## 转换命令

```powershell
python tools/ply-to-w3gs/convert_ply_to_w3gs.py `
  --input datasets/unified-huce-zhanting/HuCeZhanTing-10k-seed20260611.ply `
  --output demos/w3gs-from-ply/huce-zhanting-10k-parent-summary `
  --max-splats 10000 `
  --lod-mode parent-summary `
  --max-leaf-splats 2500 `
  --max-depth 4
```

`--max-leaf-splats 2500` 用于确保 10K smoke 实际生成 internal summary，而不是因为默认 25K 阈值退化为单 leaf。

## 结果

| 指标 | 数值 |
| --- | ---: |
| converted splats | 10,000 |
| leaf original splats | 10,000 |
| internal summary splats | 506 |
| nodes / layers / chunks | 25 / 25 / 25 |
| payload bytes | 588,336 |
| startup bytes | 9,744 |
| summary overhead | 0.0506 |
| converter wall time | 0.811498 s |

峰值 RSS 未记录：当前 Windows + Python 标准库/命令级运行无法提供可靠 peak RSS。

## 属性损失

共同 PLY 子集保持原始 SH3，不做降阶。当前 W3GS `raw-gaussian-v0` 只写 position、scale、rotation、opacity 和 DC color，因此：

```text
source: SH3, f_rest_0..44
target: SH0 / DC color
```

normal 和 45 个 `f_rest_*` 不进入 W3GS payload。该损失发生在目标转换链，不发生在共同 PLY 子集。

## 验证

- `validation-report.json`：机器可读 conformance 报告。
- `validation-report.txt`：人类可读报告。
- `smoke-test-report.json`：命令、工具 hash、耗时、大小、属性损失和 viewer 静态兼容检查。
- `converter-run.txt`：converter 原始命令输出摘要。

独立 validator 结果：`PASS`，0 error、1 warning、1 info。warning 是当前格式字段无法严格证明 startup fallback 的视觉完整性。

WebGPU viewer 的 `app.js` 通过 `node --check`；sample 的 JSON 引用、56-byte raw stride、startup chunk 和 payload ranges 均通过静态兼容检查。本次未启动浏览器做真实 WebGPU 绘制。
