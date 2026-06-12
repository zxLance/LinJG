# 可复现嵌套 PLY 采样器

`sample_ply.py` 用于从大型、固定记录长度的 `binary_little_endian` PLY 中生成确定性、无放回、相互嵌套的共同实验子集。

它不会解析或重编码 vertex 属性，而是逐条复制原始二进制记录。因此 position、normal、SH、opacity、scale、rotation 等属性的类型、顺序和原始字节保持不变。输出 header 只修改 `element vertex` 数量，其余 header 行和 comment 原样保留。

## 依赖

- Python 3.10 或以上。
- 仅使用标准库。
- 不需要把整个 PLY 载入内存。

## 采样算法

当前算法标识为：

```text
splitmix64-priority-bottom-k-v1
```

对每个源 vertex index 计算：

```text
priority = SplitMix64(index XOR seed)
```

选取 priority 最小的最大规模 `K` 个 index。更小规模使用同一排名的前缀，因此：

```text
10K 是 250K 的严格子集
```

与每隔固定步长取一点相比，该方法不会直接继承源 PLY 的空间排序、训练排序或 Morton 顺序偏差。它是固定 seed 的确定性伪随机无放回样本；不是密码学随机数，也不声称替代统计抽样审计。

输出记录按源 vertex index 升序排列，保证文件字节顺序确定。

## 使用方法

从 `3dgs-format-research` 目录运行：

```powershell
python tools/ply-sampler/sample_ply.py `
  --input "D:\DATA\3DGS\PLY\HuCeZhanTing.ply" `
  --output-dir "datasets/unified-huce-zhanting" `
  --counts 10k 250k `
  --seed 20260611
```

输出：

```text
datasets/unified-huce-zhanting/
  HuCeZhanTing-10k-seed20260611.ply
  HuCeZhanTing-250k-seed20260611.ply
  dataset-manifest.json
  README.md
```

## 输入限制

当前版本有意采用严格边界：

- 只支持 `binary_little_endian`。
- vertex 必须全部是固定长度标量 property。
- 不支持 vertex list property。
- 如果出现 face、edge 或其他非 vertex element，工具明确拒绝。
- 文件大小必须严格等于 `header + vertexCount * recordSize`。

这些限制是为了避免在不知道其他 element 数据布局时静默丢失或破坏数据。未来如果需要 mesh PLY，应单独设计保留其他 element 的模式。

## 可复现记录

`dataset-manifest.json` 记录：

- 源路径、完整 SHA-256、大小、vertex 数。
- header comment、全部 property 名称、类型和字节数。
- `f_rest_*` 数量和可推导的 SH 阶数。
- 算法、seed、输出顺序和 block size。
- 每个输出的点数、大小、SHA-256。
- 选中 index 的 min/max、首尾摘要和 uint64-LE index digest。
- 10K/250K 的严格 index subset 和 raw record byte 比较结果。
- selection、扫描/写出/hash 和总 wall time。
- 工具 SHA-256、Python 版本和生成命令。

Windows Python 标准库不能可靠读取当前进程 peak RSS，因此 manifest 中该值为 `null`，并明确记录不可用原因。不要用估算值冒充测量值。

## 测试

```powershell
python -m unittest discover -s tools/ply-sampler/tests -v
```

测试覆盖：

- 固定 seed 的确定性。
- 多规模严格嵌套。
- property、comment 和原始记录字节保持。
- header 只改变 vertex count。
- ASCII 输入拒绝。
- 非 vertex element 拒绝。

## 数据许可

采样器代码可以独立发布，但输入数据和生成子集的许可需要单独确认。

当前 `HuCeZhanTing.ply` 的许可与派生子集再分发授权尚未记录。因此生成的 10K/250K PLY 默认仅供本地研究，不应直接上传、提交 Git 或随论文公开。manifest 中保留路径和 hash 不等于获得再分发许可。
