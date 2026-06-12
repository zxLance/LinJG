# W3GS Experiment Platform

这是 W3GS 的 Prototype 1 实验平台。

Prototype 1 不再把 `app.js` 顶部的内置模拟数据作为主数据源。页面启动时会通过 `fetch` 读取：

```text
../w3gs-format-sample/scene.w3gs.json
../w3gs-format-sample/nodes.w3gs.json
../w3gs-format-sample/chunks.w3gs.json
```

读取成功后，平台把 sample 中的 scene / node / layer / chunk 字段转换为运行时模拟器使用的内部结构，再运行四种加载策略对比。

## 运行方式

需要用静态 HTTP 服务打开，不能只双击 `index.html`。因为浏览器通常会阻止 `file://` 页面通过 `fetch` 读取相邻 JSON。

推荐从 `3dgs-format-research/demos` 目录启动：

```powershell
cd D:\Documents\Project\Python_project\LinJG\3dgs-format-research\demos
python -m http.server 8766
```

然后打开：

```text
http://127.0.0.1:8766/w3gs-experiment-platform/
```

页面的 Loaded Sample 面板应显示：

```text
Source: W3GS sample JSON
Name: w3gs-demo-room
Nodes: 8
Chunks: 22
Codecs: raw-gaussian-v0, spz-placeholder-v0
```

如果 sample fetch 失败，平台会退回内置 Prototype 0 fallback，并在 Source 中显示 fallback 状态。

## 字段映射

| W3GS sample 字段 | Runtime 内部字段 | 用途 |
| --- | --- | --- |
| `scene.scene.name` | `scene.source.sampleName` | UI 展示已加载样本名。 |
| `scene.bounds.min/max` | `scene.world` | 生成 2D 画布投影范围。Prototype 1 使用 X/Z 平面显示 AABB。 |
| `scene.files.nodes` | fetch URL | 读取 node tree。 |
| `scene.files.chunks` | fetch URL | 读取 chunk table。 |
| `scene.codecs[].id` | `scene.source.codecList` | UI 展示 codec 列表。 |
| `nodes.nodes[].id/parent/children` | `node.id/parent/children` | 建立 `nodeMap` 和空间层级。 |
| `nodes.nodes[].bounds` | `node.bounds` | 2D AABB 可视化和可见性测试。 |
| `nodes.nodes[].layers[]` | `node.layers[]` 与 `layerMap` | 节点 ordered layers；每个 layer 通过 `chunk` 指向 chunk table。 |
| `nodes.nodes[].layers[].chunk` | `layer.chunkId` | 调度时请求的 chunk id。 |
| `chunks.chunks[].id` | `chunk.id` 与 `chunkMap` | 建立 chunk lookup。 |
| `chunks.chunks[].byteLength` | `chunk.byteLength` | 网络下载时间和 downloaded bytes 指标。 |
| `chunks.chunks[].splatCount` | `chunk.splats` | 可见 splat 数估计。 |
| `chunks.chunks[].runtimeHints.decodeCost` | `chunk.decodeCost` | 模拟 decode 时间。 |
| `chunks.chunks[].runtimeHints.gpuUploadBytes` | `chunk.gpuBytes` | Peak GPU 指标。 |
| `chunks.chunks[].codec` | `chunk.codec` | codec 统计和日志。 |

运行时会建立三个 Map：

```text
nodeMap: node id -> runtime node
layerMap: layer id -> runtime layer
chunkMap: chunk id -> runtime chunk
```

## 当前对比策略

| 策略 | 含义 |
| --- | --- |
| Full loading | 一开始请求 sample 中所有真实 chunk。 |
| Spatial-only | 只按空间可见性加载，但可见 node 一次加载到当前需求层级。 |
| Progressive-only | 消融基线：sample 没有全局 progressive chunks，因此平台把所有 level 0/1/2 layer 分别聚合成 `progressive.level0/1/2` 三个模拟全局层。它不是 W3GS 格式中的真实 chunk。 |
| W3GS scheduling | 同时使用空间 node、ordered layers、chunk table、startup set 和 runtime hints。 |

## 当前指标

| 指标 | 含义 |
| --- | --- |
| First render | 第一次有可见数据可显示的模拟时间。 |
| Downloaded | 总下载字节数。 |
| Requests | chunk 请求数量。 |
| Overfetch | 下载了但当前相机路径几乎用不到的数据比例。 |
| Local detail | 目标区域达到高细节层级的时间。 |
| Peak GPU | 模拟 GPU buffer 峰值。 |
| Quality area | 沿相机路径累积的可见质量面积。 |

## 研究边界

这个平台仍然只验证“格式结构是否支持 Web streaming 调度”，不声称：

- W3GS 已经完成真实 3D Gaussian 渲染。
- W3GS 压缩率更高。
- W3GS 已经超过真实工业格式。

Prototype 1 的 payload 仍是 placeholder，当前画布只做 2D AABB 可视化。
