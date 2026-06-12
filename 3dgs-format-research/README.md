# 3DGS Format Research

这个文件夹用于沉淀 3D Gaussian Splatting 文件格式相关的学习笔记、源码阅读记录、论文写作素材和实验 demo。

## 目录规划

- `notes/`: 按主题整理的学习笔记。
- `sources/`: 源码、论文、文档等资料来源记录。
- `demos/`: 为理解格式或加载流程写的小实验。
- `diagrams/`: 结构图、流程图、论文配图草稿。
- `paper-drafts/`: 后续论文相关草稿。
- `references/`: 文献、链接、引用信息整理。

## 当前归档

- Spark 源码本地副本：[`sources/spark-src`](./sources/spark-src)
- Spark RAD 流式加载学习 demo：[`demos/spark-learning`](./demos/spark-learning)

## 当前主线

总路线图：

- [项目文件地图](./PROJECT-MAP.md)
- [研究规划：面向 Web 流式渲染的 3D Gaussian Splatting 数据格式设计研究](./research-plan.md)
- [科研周期状态记录](./research-status.md)
- [项目交接说明](./PROJECT-HANDOFF.md)
- [W3GS 格式设计草案](./proposed-format-design.md)
- [W3GS 格式演示数据](./demos/w3gs-format-sample/scene.w3gs.json)
- [W3GS Prototype 0 实验平台](./demos/w3gs-experiment-platform/index.html)

当前主线已经从“比较已有格式”推进到“验证 Web 3DGS 显式 streaming contract”。W3GS 是 reference contract/profile，不预设优于现有格式。

- 字段级 contract gap analysis 已完成第一版。
- W3GS converter、独立 validator、SH0/SH3 profile 和 WebGPU prototype 已实现。
- 统一 SH3 PLY 的 10K/250K 确定性子集已经冻结。
- 当前优先解决 WebGPU SH3 增强 smoke 的 `Target crashed`，随后进入 SOG/RAD 同源转换。

接手项目时不要仅阅读本 README，应先阅读 [PROJECT-HANDOFF.md](./PROJECT-HANDOFF.md)。
