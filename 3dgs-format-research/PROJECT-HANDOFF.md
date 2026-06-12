# Project Handoff

最后更新：2026-06-12

本文档面向接手本项目的人。不要从聊天记录倒推状态，先按本页顺序阅读和执行。

## 1. 先读这些文件

1. `../AGENTS.md`：协作规则与 Agent 使用约束。
2. `research-status.md`：当前阶段、已完成证据和阻塞。
3. `research-plan.md`：研究动机、问题、评价体系和实验逻辑。
4. `notes/comparisons/existing-format-gap-analysis.md`：实验 1 的字段级结果。
5. `notes/experiments/unified-ply-conversion-toolchain.md`：同源工具链可行性。
6. `notes/format-cases/w3gs-0.1-payload-profiles.md`：SH0/SH3 payload contract。
7. `demos/README.md`：真实样本清单和证据边界。

## 2. 研究目标

论文不是单纯比较四种格式，也不是证明 W3GS 全面更优。目标是研究 Web 3DGS 离线 packing 与浏览器 runtime 之间需要哪些最小、显式、可机器验证的 streaming contract，并用 W3GS 作为 reference implementation 验证这一边界。

## 3. 当前冻结状态

- 字段级 contract gap analysis 已完成第一版。
- W3GS converter、validator、WebGPU prototype 已实现。
- W3GS SH3 10K 格式、属性保留和 conformance 已验收。
- WebGPU 增强 SH3 正确性 smoke 尚未通过，当前暂停在 `Target crashed`。
- SOG/RAD 依赖尚未安装，同源转换尚未开始。
- 当前没有静态服务器或浏览器测试进程应当运行。

## 4. 当前数据

本地统一源：

```text
D:\DATA\3DGS\PLY\HuCeZhanTing.ply
```

不要改动或覆盖源文件。其 SHA-256 必须是：

```text
a4624ae67bf4d7f0764b714531f1cc21707ce2b9fa936a5fc6d85dd9cea64cea
```

子集 manifest：

```text
datasets/unified-huce-zhanting/dataset-manifest.json
```

10K/250K PLY 被 Git ignore，若本地不存在，应使用 `tools/ply-sampler/sample_ply.py` 和 manifest 中的固定命令、seed 重新生成并核对 hash。数据许可未确认，不得上传或公开派生子集。

## 5. 当前唯一优先任务

先修复：

```powershell
node demos/w3gs-webgpu-viewer/webgpu_smoke_test.mjs
```

已知现象：Chrome 与 Edge `Target crashed`。

必须定位崩溃发生在：

- `verifyShReference()` compute；
- GPU submission/readback/`mapAsync()`；
- scene render；
- `Page.captureScreenshot`；
- 或 GPU/browser process。

必须采集：浏览器 stderr、页面 console/error、CDP close reason、`device.lost` 和具体执行阶段。不要靠增加 sleep 猜测。

验收条件：

1. 10K SH3 scene WebGPU ready、0 error。
2. 同一相机、同一 active chunks/splats 下 full SH3 与 DC-only 产生可解释差异。
3. synthetic fixture 的 CPU/WGSL max abs error `<= 1e-5`。
4. 新报告覆盖旧历史报告，并标明 adapter/browser 信息。
5. 测试结束后无 Chrome/Edge/Node 测试进程和监听端口。

## 6. 下一阶段需要用户授权

WebGPU 阻塞解除后：

- 安装 `@playcanvas/splat-transform@2.5.2`，预计 0.1--0.3 GiB，用于 SOG Streaming 10K smoke。
- 安装 Rust stable 并构建 Spark `build-lod`，预计 1--3 GiB，用于 chunked RAD 10K smoke。

任何安装、网络下载或云端上传都应先获得用户授权。Cesium ion 不得擅自上传统一源数据。

## 7. Agent 复用

Agent ID 见仓库根目录 `AGENT-ROSTER.md`。

| Agent | 建议职责 |
| --- | --- |
| Turing / Ada | Converter、validator、viewer、转换工具链和实验实现。 |
| Hooke | 格式证据、样本审计、规范与实验独立验收。 |
| Friday / Gauss | 文献、标准、论文动机与 related work。 |
| Pasteur | 反方论证、研究问题压力测试。 |
| Gibbs / Feynman | LoD 策略与算法讨论。 |

不要创建新 Agent，除非已有 Agent 都不适合；新建前必须向用户申请。

## 8. 常用验证命令

从 `3dgs-format-research` 目录运行：

```powershell
python -m unittest discover -s tools/ply-sampler/tests -v
python -m unittest discover -s tools/ply-to-w3gs/tests -v
python -m unittest discover -s tools/w3gs-validator/tests -v
python tools/w3gs-validator/validate_w3gs.py demos/w3gs-from-ply/huce-zhanting-10k-parent-summary-sh3 --format json
node --check demos/w3gs-webgpu-viewer/app.js
node --check demos/w3gs-webgpu-viewer/webgpu_smoke_test.mjs
```

当前预期：sampler 6/6、converter 6/6、validator 19/19；SH3 样本 0 error、1 warning、1 info。

## 9. Git 与大文件

- 工作树包含大量尚未纳入正式提交的研究文件，接手者不要使用 `git reset --hard` 或批量清理。
- `.rad`、大型 SOG WebP、统一 PLY 子集和 W3GS payload 均应保持 Git ignore。
- 文档、JSON manifest、测试报告、转换代码和 validator 应纳入版本管理。
- 在提交前先审计当前工作树，按研究阶段拆分提交，不要把 1 GiB 级样本加入普通 Git blob。

## 10. 关键论证边界

- W3GS 是 reference contract，不是已证明最优的新标准。
- raw SH3 是验证布局，不是压缩方案。
- 同源端到端实验目前只计划 RAD、SOG Streaming、W3GS。
- LCC2 与 Cesium 保留在字段分析和原生样本实验中，除非获得公开可复现 writer/tiler。
- 端到端工具链比较必须与受控 contract 实验分开解释。

