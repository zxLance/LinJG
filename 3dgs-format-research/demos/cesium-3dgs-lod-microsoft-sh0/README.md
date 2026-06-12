# Cesium 3DGS LOD Demo Layout

这个目录分成两部分：

```text
data/
  从 Cesium ion 公开 asset 4547222 下载/解析出来的真实数据样本。
  包括 tileset.json、tile_*.glb、外部 ts_*/tileset.json、解析 summary 等。

demo/
  用来渲染和调试该 asset 的本地演示文件。
  包括 viewer.html、start-viewer.ps1、serve-viewer.mjs、debug-cdp.mjs。
```

正常查看演示时运行：

```powershell
.\demo\start-viewer.ps1
```

不要直接双击 `viewer.html`，固定走本地 HTTP 地址：

```text
http://127.0.0.1:8765/demo/viewer.html
```

`viewer.html` 默认从本地样本加载：

```js
Cesium.Cesium3DTileset.fromUrl("../data/tileset.json")
```

页面里的 `Ion Online` 按钮只用于和 Cesium ion 在线 asset `4547222` 做对照。
