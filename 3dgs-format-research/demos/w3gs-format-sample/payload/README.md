# Placeholder Payload Directory

这个目录故意不包含真实 payload。

`../chunks.w3gs.json` 中的 `uri` 字段假设存在：

```text
chunks-0.bin
chunks-1.bin
chunks-2.bin
```

但这些二进制文件当前没有生成。

这样做是为了先把 W3GS 的完整元数据结构固定下来：

- scene manifest
- node tree
- ordered layers
- chunk table
- codec profile
- byte range
- runtime hints

后续 Prototype 1 会把这些 placeholder chunk 替换成真实 Gaussian payload。

