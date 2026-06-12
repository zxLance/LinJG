# W3GS Format Sample

这是 W3GS 的完整演示数据样本。

当前样本只用于展示格式结构，payload 是假设存在的，不包含真实 3D Gaussian 二进制数据。

## 文件组成

```text
w3gs-format-sample/
  scene.w3gs.json
  nodes.w3gs.json
  chunks.w3gs.json
  payload/
    README.md
```

## 样本目标

这套样本用于说明 W3GS 如何显式表达：

- 顶层场景 manifest。
- 空间 node tree。
- 父子节点连接关系。
- 每个 node 下的 ordered layers。
- base layer 和多个 refinement layers。
- layer 到 chunk 的引用。
- chunk 到假想 payload byte range 的引用。
- payload codec profile。
- LoD contract。
- Web runtime scheduling hints。

## 重要边界

`chunks.w3gs.json` 中的 `uri`、`byteOffset`、`byteLength` 是格式示例，不对应真实二进制文件。

后续 Prototype 1 才会把这些假 chunk 替换为真实 Gaussian payload。

