# Project Map

这份文件是项目的“文件地图”。它只记录当前资料应该放在哪里、从哪里开始读；具体研究内容仍然放在 `research-plan.md`、`research-status.md`、`proposed-format-design.md` 和 `notes/` 里。

## 推荐阅读入口

0. `../AGENTS.md`：先看本项目的人机协作方式，尤其是主线程和子 Agent 的分工。
1. `PROJECT-HANDOFF.md`：接手项目时先看冻结状态、阻塞和可执行命令。
2. `research-status.md`：看我们现在处在科研周期的哪一步。
3. `research-plan.md`：看研究问题、评价体系和实验路线。
4. `proposed-format-design.md`：看当前 W3GS 设计草案。
5. `notes/00-index.md`：按主题进入已有笔记。
6. `demos/README.md`：确认每个格式结论对应哪些本地样本或 demo。

## 顶层文件

| 路径 | 作用 |
| --- | --- |
| `../AGENTS.md` | 项目协作规则，规定用户、Codex 主线程和子 Agent 的职责边界。 |
| `README.md` | 项目总入口，适合给未来的自己快速回忆项目目标。 |
| `PROJECT-HANDOFF.md` | 项目交接快照，记录冻结状态、当前阻塞、命令和下一步授权。 |
| `PROJECT-MAP.md` | 当前文件地图，说明资料如何摆放。 |
| `research-plan.md` | 研究总计划，后续核心决策和实验设计优先写到这里。 |
| `research-status.md` | 科研周期状态记录，随着阶段推进持续更新。 |
| `proposed-format-design.md` | W3GS 自有格式设计草案。 |

## 目录分工

| 目录 | 放什么 | 不放什么 |
| --- | --- | --- |
| `notes/` | 源码阅读、格式分析、文献综述、缺口分析、比较分析。 | 不放可运行 demo，不放大体积原始数据。 |
| `demos/` | 可打开的 HTML demo、真实样本、解析脚本、实验平台。 | 不放纯文字综述，不放浏览器 profile/cache。 |
| `sources/` | 外部源码库、本地镜像、来源说明。 | 不放我们自己写的论文草稿。 |
| `references/` | 文献引用、BibTeX、链接清单。 | 不放已经消化后的长篇分析。 |
| `diagrams/` | 论文图、结构图、流程图草稿。 | 不放核心文字论证。 |
| `paper-drafts/` | 论文正文草稿、章节草稿。 | 不放 demo 数据和源码镜像。 |
| `datasets/` | 统一实验数据的 manifest、README 与本地生成子集。 | 不把未获许可的大型 PLY 提交到普通 Git。 |
| `tools/` | 采样、转换、验证等可复现实验工具。 | 不放一次性手工脚本和大体积输出。 |

## Notes 分区

`notes/00-index.md` 是笔记总入口，具体笔记按研究用途分类。

| 子目录 | 作用 |
| --- | --- |
| `notes/format-cases/` | 单个格式的案例分析：RAD、LCC2、SOG Streaming、Cesium 3D Tiles Gaussian Splat。 |
| `notes/comparisons/` | 横向比较、案例比较草稿、现有格式缺口分析。 |
| `notes/literature/` | 文献综述、发展脉络图谱、前沿论文格式缺口。 |
| `notes/convergence/` | 候选创新方向和研究收敛过程。 |
| `notes/experiments/` | 实验设计、统一数据集和工具链可行性记录。 |

## Demo 分区

| 目录 | 作用 |
| --- | --- |
| `demos/spark-learning/` | Spark RAD 流式加载学习 demo。 |
| `demos/spark-rad-demo/` | Spark RAD 样本/验证相关资料。 |
| `demos/qiyu-lcc2-demo/` | XGRIDS LCC2 真实样本和解析依据。 |
| `demos/playcanvas-roman-parish-lod/` | PlayCanvas / SuperSplat SOG Streaming 样本。 |
| `demos/cesium-3dgs-lod-microsoft-sh0/` | Cesium 3D Tiles Gaussian Splat 抽样。 |
| `demos/w3gs-format-sample/` | 我们自有 W3GS 格式的演示数据。 |
| `demos/w3gs-experiment-platform/` | W3GS Prototype 0 实验平台。 |
| `demos/w3gs-webgpu-viewer/` | W3GS SH0/SH3 WebGPU reference viewer 与自动 smoke。 |
| `demos/w3gs-from-ply/` | 真实 PLY 转换得到的 W3GS 实验输出与报告。 |

## 清理规则

- 浏览器运行缓存、调试 profile、依赖目录和构建产物不进入研究资料。
- 超过 GitHub 普通仓库承载能力的大体积样本只保留本地副本和来源说明，后续用下载脚本或 Git LFS 管理。
- 大体积真实样本要在对应 demo README 中说明来源、大小、是否完整。
- 新增核心研究结论优先更新 `research-plan.md` 或 `research-status.md`，避免散落成很多孤立文档。
- 新增格式样本时，同时更新 `demos/README.md`，说明它能直接支撑什么结论、不能支撑什么结论。
