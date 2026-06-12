# 3DGS 数据格式设计相关文献综述

这份笔记基于 Friday 的调研结果整理，用于支撑论文《面向 Web 流式渲染的 3D Gaussian Splatting 数据格式设计研究》的 Related Work 章节。

核心思路：

```text
不要只写 3DGS 原始论文。
Related Work 应该把：

表示参数
  -> 压缩编码
  -> 渐进 / LoD / Streaming
  -> Web 渲染工程
  -> 标准容器与互操作

串成一条数据格式演进线。
```

## 1. 3DGS 表示与实时渲染

### 必读：3D Gaussian Splatting for Real-Time Radiance Field Rendering, 2023

链接：[arXiv](https://arxiv.org/abs/2308.04079)

核心内容：

提出现代 3D Gaussian Splatting 表示，用各向异性 3D Gaussian 存储位置、协方差 / 旋转尺度、不透明度、球谐颜色，并用 tile-based visibility-aware rasterization 实现实时渲染。

和本文关系：

这是所有格式设计的参数源头。后续格式里的 position、scale、rotation、opacity、SH coefficients、排序和 alpha blending，都来自这套表示。

### 必读：Mip-Splatting: Alias-free 3D Gaussian Splatting, 2024

链接：[arXiv](https://arxiv.org/abs/2311.16493)，[CVF](https://openaccess.thecvf.com/content/CVPR2024/papers/Yu_Mip-Splatting_Alias-free_3D_Gaussian_Splatting_CVPR_2024_paper.pdf)

核心内容：

解决 3DGS 多尺度观看时的 aliasing 问题，用 3D smoothing filter 和 2D mip filter 改善远近尺度渲染。

和本文关系：

Web 流式格式中的 LoD 不能只理解为“少传一些点”。粗层和细层切换时，还要考虑抗混叠和多尺度一致性。

### 必读：Scaffold-GS: Structured 3D Gaussians for View-Adaptive Rendering, 2024

链接：[arXiv](https://arxiv.org/abs/2312.00109)

核心内容：

用 anchor 组织 Gaussians，基于视角和距离动态生成或选择局部高斯，减少冗余。

和本文关系：

提供了 “anchor + local attributes / generated Gaussians” 的结构化思路，对未来格式中的可扩展编码、视角自适应 streaming 有启发。

### 可读：gsplat: An Open-Source Library for Gaussian Splatting, 2024

链接：[arXiv](https://arxiv.org/abs/2409.06765)，[GitHub](https://github.com/nerfstudio-project/gsplat)

核心内容：

开源高性能 3DGS 训练 / 渲染库。

和本文关系：

可作为训练输出、参数组织和 rasterization pipeline 的工程背景。

## 2. 压缩、编码、量化与存储

### 必读：3DGS.zip: A survey on 3D Gaussian Splatting Compression Methods, 2024

链接：[arXiv](https://arxiv.org/abs/2407.09510)

核心内容：

系统综述 3DGS 压缩方法，并提供统一评价视角。

和本文关系：

适合作为压缩小节的综述入口，用来梳理 pruning、quantization、entropy coding、structured representation 等路线。

### 必读：LightGaussian, 2024

链接：[arXiv](https://arxiv.org/abs/2311.17245)，[NeurIPS PDF](https://papers.nips.cc/paper_files/paper/2024/file/fd881d3b625437354d4421818f81058f-Paper-Conference.pdf)

核心内容：

用重要性剪枝、SH 蒸馏、向量量化压缩 unbounded scenes，报告约 15x 压缩并提升 FPS。

和本文关系：

说明 Web 格式需要同时优化传输体积和运行时 Gaussian 数量。

### 必读：Compact3D / CompGS, 2024

链接：[arXiv](https://arxiv.org/abs/2311.18159)，[ECCV PDF](https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/04735.pdf)

核心内容：

用 K-means / codebook 量化 Gaussian 参数，并压缩索引，减少存储和渲染开销。

和本文关系：

对格式设计直接相关：字段可以拆成 codebook + index stream，支持 GPU 解码或离线解码。

### 必读：HAC: Hash-grid Assisted Context for 3D Gaussian Splatting Compression, 2024

链接：[ECCV PDF](https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/01178.pdf)

核心内容：

用 hash-grid assisted context 建模属性分布，进行上下文熵编码。

和本文关系：

提示格式可以包含空间上下文和熵模型，但 Web 端解码复杂度需要权衡。

### 必读：PCGS: Progressive Compression of 3D Gaussian Splatting, 2025

链接：[arXiv](https://arxiv.org/abs/2503.08511)

核心内容：

同时控制 Gaussian 数量和属性质量，形成渐进 bitstream；先粗后细，适合 on-demand applications。

和本文关系：

和 Web 流式渲染数据格式高度相关，是 progressive streaming 设计的直接对照。

### 可读：EAGLES, 2024

链接：[arXiv](https://arxiv.org/abs/2312.04564)

核心内容：

用量化 embeddings 和 coarse-to-fine training 降低每点存储，减少 Gaussians 数量。

和本文关系：

适合讨论轻量编码和移动 / Web 端内存约束。

### 可读：CompGS: Efficient 3D Scene Representation via Compressed Gaussian Splatting, 2024

链接：[arXiv](https://arxiv.org/abs/2404.09458)

核心内容：

Anchor primitives + residual representation + rate-constrained optimization。

和本文关系：

对渐进式、分块式格式有启发：基础 anchor 可先传，残差细节后传。

### 可读：FCGS, 2024

链接：[arXiv](https://arxiv.org/abs/2410.08017)

核心内容：

用 feed-forward 模型快速压缩已有 3DGS，避免每场景长时间优化。

和本文关系：

如果论文讨论生产管线中的快速转码，这篇较相关。

### 可读：CodecGS, 2025

链接：[CVF PDF](https://openaccess.thecvf.com/content/ICCV2025/papers/Lee_Compression_of_3D_Gaussian_Splatting_with_Optimized_Feature_Planes_and_ICCV_2025_paper.pdf)

核心内容：

将 3DGS 属性映射到优化 feature planes，并利用标准视频编码器压缩。

和本文关系：

可用于讨论复用成熟 Web 视频解码栈的可能性，但随机访问和空间选择不如 tile / LoD manifest 直接。

### 背景：CAT-3DGS, 2025

链接：[ICLR](https://proceedings.iclr.cc/paper_files/paper/2025/hash/41e638f36d9cb052669d30f559e7c0b7-Abstract-Conference.html)

核心内容：

用多尺度 triplane 和上下文自回归编码做率失真优化。

和本文关系：

适合放在 learned compression 背景，不一定适合轻量 Web 解码。

## 3. 层次化表示、LoD 与大场景流式渲染

### 必读：Octree-GS, 2024

链接：[arXiv](https://arxiv.org/abs/2403.17898)

核心内容：

用 octree 组织多分辨率 anchor / Gaussian，动态选择合适 LoD。

和本文关系：

数据格式中的空间索引、层级块、LoD selection 可直接参考。

### 必读：CityGaussian, 2024

链接：[arXiv](https://arxiv.org/abs/2404.01133)，[项目页](https://dekuliutesla.github.io/citygs/)

核心内容：

面向城市级场景，用分治训练、融合和 block-wise LoD 渲染。

和本文关系：

支持论文讨论大场景、数字孪生、园区 / 城市级数据中的分块和 LoD 需求。

### 必读：VastGaussian, 2024

链接：[arXiv](https://arxiv.org/abs/2402.17427)，[CVF](https://openaccess.thecvf.com/content/CVPR2024/papers/Lin_VastGaussian_Vast_3D_Gaussians_for_Large_Scene_Reconstruction_CVPR_2024_paper.pdf)

核心内容：

大场景 progressive partitioning、cell-based training 和 appearance decoupling。

和本文关系：

支持讨论大场景切块、跨块一致性和并行训练结果如何变成可流式数据。

### 必读：A LoD of Gaussians, 2025

链接：[arXiv](https://arxiv.org/abs/2507.01110)

核心内容：

外存 / out-of-core 场景下的 Gaussian hierarchies 和 Sequential Point Trees，动态 streaming 相关 Gaussians。

和本文关系：

和 out-of-core + streaming + LoD 高度相关，适合引出显存预算驱动加载。

### 必读：L3GS: Layered 3D Gaussian Splats for Efficient 3D Scene Delivery, 2025

链接：[arXiv](https://arxiv.org/abs/2504.05517)，[MobiCom PDF](https://jiasi.engin.umich.edu/wp-content/uploads/sites/81/2025/05/L3GS_mobicom_25.pdf)

核心内容：

把 3DGS 组织为 layered delivery，面向网络传输和移动端体验。

和本文关系：

与首屏速度、移动网络和层级增量传输直接相关。

### 必读：3DGStreaming, 2025

链接：[HKUST 页面](https://researchportal.hkust.edu.hk/en/publications/3dgstreaming-spatial-heterogeneity-aware-3-d-gaussian-splatting-c/)

核心内容：

空间异质性感知分区、多码率渐进场景生成、FoV-based bitrate adaptation。

和本文关系：

可作为自适应流媒体章节的核心对照，尤其适合讨论 QoE、viewport / FoV 和 bitrate selection。

### 可读：STREAMINGGS, 2025

链接：[arXiv](https://arxiv.org/abs/2506.09070)

核心内容：

Voxel-based streaming、内存优化和架构支持。

和本文关系：

用于补充硬件 / 内存层面的 streaming 设计约束。

## 4. Web / GPU / Browser 渲染与工程格式

### 必读：WebSplatter, 2026

链接：[arXiv](https://arxiv.org/abs/2602.03207)

核心内容：

WebGPU 原生浏览器 3DGS 渲染框架，包含层级排序、opacity culling 等。

和本文关系：

直接对应 Web 渲染环境，适合引用来说明浏览器端排序、GPU buffer 和跨设备限制。

### 必读：antimatter15/splat, 2023-

链接：[GitHub](https://github.com/antimatter15/splat)

核心内容：

早期广泛传播的 WebGL 3DGS viewer，强调 WebGL 兼容性与浏览器限制。

和本文关系：

说明 Web 端 3DGS 最初以 `.ply/.splat` 等轻量工程格式传播，排序和纹理打包多为实现约定。

### 必读：PlayCanvas SuperSplat / SuperSplat Viewer, 2024-2026

链接：[产品页](https://dev.playcanvas.com/products/supersplat)，[Viewer GitHub](https://github.com/playcanvas/supersplat-viewer)，[文档](https://developer.playcanvas.com/user-manual/supersplat/viewer/)

核心内容：

浏览器内编辑、优化、发布和嵌入 3D Gaussian Splats，支持 WebGPU、WebXR、PLY、compressed PLY、SOG 等。

和本文关系：

Web 端生产级格式 / 工具链的重要样本。

### 必读：PlayCanvas SOG / Splat Optimized Graphics, 2025-2026

链接：[格式文档](https://developer.playcanvas.com/user-manual/gaussian-splatting/formats/)，[SOG 说明](https://developer.playcanvas.com/user-manual/gaussian-splatting/formats/sog/)，[splat-transform GitHub](https://github.com/playcanvas/splat-transform)

核心内容：

SOG 是面向 Web runtime / delivery 的压缩 3DGS 容器；splat-transform 支持 PLY、compressed PLY、SOG、SPZ、GLB、LoD、WebP 等。

和本文关系：

与论文主题高度贴合，可作为 Web-first 3DGS 格式设计的工程标杆。

### 可读：FlashGS, 2025

链接：[CVF PDF](https://openaccess.thecvf.com/content/CVPR2025/papers/Feng_FlashGS_Efficient_3D_Gaussian_Splatting_for_Large-scale_and_High-resolution_Rendering_CVPR_2025_paper.pdf)

核心内容：

优化大规模高分辨率 3DGS 渲染，改善 tile / intersection / sorting 等性能瓶颈。

和本文关系：

格式设计要考虑 renderer access pattern，尤其是按 tile、depth、visibility 组织数据。

### 背景：GauRast, 2025

链接：[NVIDIA Research](https://research.nvidia.com/publication/2025-06_gaurast-enhancing-gpu-triangle-rasterizers-accelerate-3d-gaussian-splatting)

核心内容：

从硬件 rasterizer 角度加速 3DGS。

和本文关系：

说明长期看 3DGS 可能进入硬件 / 图形 API 支持，格式应避免绑定单一软件排序策略。

## 5. 标准、容器与互操作

### 必读：KHR_gaussian_splatting glTF Extension, 2026 Release Candidate

链接：[Khronos GitHub Spec](https://github.com/KhronosGroup/glTF/blob/main/extensions/2.0/Khronos/KHR_gaussian_splatting/README.md)，[Khronos 新闻](https://www.khronos.org/news/press/gltf-gaussian-splatting-press-release?khr-2026-000=khr-2026-001)

核心内容：

定义 glTF 中存储 3D Gaussian splats 的基础扩展，字段包括 position、rotation、scale、opacity、SH；以 point primitive 作为 fallback，强调算法无关和可扩展。

和本文关系：

这是标准化基线。论文应说明 Web 流式格式与 glTF 扩展之间的兼容、差异和分工。

### 必读：KHR_gaussian_splatting_compression_spz_2 / Cesium 3D Tiles 集成, 2026

链接：[Cesium 博文](https://cesium.com/blog/2026/04/27/3d-gaussian-splats-lod/)，[Cesium 文档](https://cesium.com/learn/cesiumjs/ref-doc/GaussianSplat3DTileContent.html)

核心内容：

Cesium 将 3DGS 接入 3D Tiles：3D Tiles 作空间索引和 LoD，glTF 作 payload，SPZ 作压缩。

和本文关系：

这是 Web 流式 3DGS 格式的产业级方案之一，必须作为主对照系统。

### 必读：OGC 3D Tiles 1.1 / 3D Tiles Standard

链接：[OGC 标准页](https://www.ogc.org/standards/3DTiles/)，[CesiumGS/3d-tiles](https://github.com/CesiumGS/3d-tiles)

核心内容：

面向海量 3D 地理空间内容的层级 streaming 结构，支持 tileset、bounding volume、geometric error、refinement。

和本文关系：

Web streaming / LoD 格式可以借鉴 3D Tiles 的空间层级、误差度量、请求调度，而不是只定义单文件结构。

### 必读：SPZ, 2024-2026

链接：[GitHub](https://github.com/nianticlabs/spz)

核心内容：

Niantic 开源压缩 3DGS 格式，支持 SH、量化、压缩和 vendor extensions。

和本文关系：

SPZ 是重要的轻量互操作压缩格式之一，也已进入 glTF / Cesium 生态。

### 必读：glTF 2.0 Specification

链接：[Khronos spec](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html)，[Khronos glTF](https://www.khronos.org/gltf/)

核心内容：

实时 3D asset delivery 标准，支持 binary GLB、buffers / accessors、extensions、PBR 等。

和本文关系：

3DGS 扩展的容器基础；论文应说明为什么选择扩展 glTF，或为什么采用自定义流格式再做 glTF 兼容桥。

### 可读：MPEG-I Gaussian Splat Coding / GSC, 2025-2026

链接：[MPEG Explorations](https://www.mpeg.org/standards/Explorations/45/)，[GSC 概览](https://mpeg.expert/gsc/index.html)

核心内容：

MPEG 正在推进 Gaussian Splat Coding，包括 common test conditions、requirements、基于 V-PCC / G-PCC 的短期路径和后续联合探索。

和本文关系：

如果论文涉及编码标准化，MPEG GSC 是必须提到的方向。

### 必读：OpenUSD 26.03 / UsdVolParticleField3DGaussianSplat, 2026

链接：[OpenUSD API](https://openusd.org/dev/api/class_usd_vol_particle_field3_d_gaussian_splat.html)，[CG Channel 报道](https://www.cgchannel.com/2026/03/openusd-26-03-adds-support-for-3d-gaussian-splats/)

核心内容：

OpenUSD 新增 3D Gaussian Splat schema 和 reference renderer，作为 USD prim type 表示 3DGS。

和本文关系：

生产、VFX、数字内容管线可能走 USD；可作为离线资产交换和 DCC 工作流背景。

## 6. 建议的 Related Work 结构

建议论文 Related Work 分成六个小节：

```text
1. 3D Gaussian Splatting 表示与实时渲染
2. 3DGS 数据规模、压缩与量化编码
3. 层次化表示、LoD 与大场景流式渲染
4. Web 端 3DGS 渲染与工程格式
5. 标准化与互操作容器
6. 本文定位
```

本文定位应该明确：

```text
本文不是提出新的 3DGS 重建算法，
而是研究面向 Web 流式渲染的数据组织、分层传输、解码和互操作格式设计。
```

## 7. 最先阅读的资料

建议优先阅读以下 12 篇 / 项：

1. 3D Gaussian Splatting for Real-Time Radiance Field Rendering
2. KHR_gaussian_splatting glTF Extension
3. Cesium: 3D Gaussian Splats with Hierarchical LOD Using 3D Tiles
4. SPZ GitHub specification
5. PCGS: Progressive Compression of 3D Gaussian Splatting
6. Octree-GS
7. CityGaussian
8. A LoD of Gaussians
9. L3GS
10. WebSplatter
11. PlayCanvas SOG / SuperSplat / splat-transform
12. 3DGS.zip survey
