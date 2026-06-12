# W3GS 独立 Conformance Checker

`validate_w3gs.py` 是一个与 PLY converter、WebGPU viewer 解耦的 W3GS 一致性检查工具。它读取任意 W3GS 数据目录，检查 JSON 文档、空间树、layer/chunk 引用、payload byte range、dependency DAG、codec/schema、startup fallback、refinement 语义和 runtime hints。

它不依赖 `tools/ply-to-w3gs/convert_ply_to_w3gs.py`，也不调用 converter 内部的 `check_consistency()`。这样可以避免 producer 自己生成、自己证明正确的循环验证。

## 依赖

- Python 3.10 或更高版本。
- 只使用 Python 标准库，不需要安装第三方包。

## 基本用法

从 `3dgs-format-research` 目录运行：

```powershell
python tools/w3gs-validator/validate_w3gs.py demos/w3gs-from-ply/point_cloud_parent_summary
```

验证其他 W3GS 目录：

```powershell
python tools/w3gs-validator/validate_w3gs.py D:\path\to\w3gs-sample
```

输出 JSON 报告：

```powershell
python tools/w3gs-validator/validate_w3gs.py `
  demos/w3gs-from-ply/point_cloud_parent_summary `
  --format json
```

同时把 JSON 报告写入文件：

```powershell
python tools/w3gs-validator/validate_w3gs.py `
  demos/w3gs-from-ply/point_cloud_parent_summary `
  --json-output reports/point-cloud-conformance.json
```

## 输出等级与退出码

| 等级 | 含义 |
| --- | --- |
| `ERROR` | 违反当前 W3GS contract，验证失败。 |
| `WARNING` | 结构可能可用，但语义未声明完整、codec 未知或当前字段不足以证明。 |
| `INFO` | 验证边界或非失败性说明。 |

退出码：

| 退出码 | 含义 |
| --- | --- |
| `0` | 没有 `ERROR`；允许存在 warning/info。 |
| `1` | 存在一个或多个 conformance error。 |
| `2` | 由 Python/argparse 报告的命令行使用错误。 |

## 检查范围

### JSON 与版本

- `scene.w3gs.json`、nodes/chunks 文档可以读取为 UTF-8 JSON object。
- scene 必须声明 `format=W3GS`、`version`、scene、bounds、files、codecs、entry。
- nodes/chunks 必须声明 version 和核心顶层字段。
- 三个文档版本必须一致。
- 当前 checker 只覆盖 `0.1`；未知版本会 error，因为该 checker 无法为未支持版本给出 conformance PASS。

### 空间树

- node id 唯一。
- scene root 与 nodes tree root 一致并存在。
- root parent 为 null。
- parent/children 双向一致。
- 不允许重复 child、自父引用、自 child、空间树环或 root 不可达节点。
- AABB 必须有合法 numeric vec3 min/max。

checker 不强制唯一 octree 组织方式，也不要求只有 parent-summary。合法的 BVH、不同 fan-out 或其他 W3GS node tree 仍可通过核心拓扑检查。

### Layer 与 Chunk

- layer id 全局唯一，level/splatCount 类型有效。
- node layer 引用的 chunk 必须存在。
- chunk 的 node/layer 反向引用必须一致。
- chunk 与 layer 的 level、splatCount 必须一致。
- chunk id 唯一。

### Payload URI 与 Byte Range

- URI 必须是当前 W3GS 目录内的安全相对路径。
- 拒绝绝对路径、URL、drive path、`..` traversal、query 和 fragment。
- 非 placeholder payload 文件必须存在，range 不能越过实际文件。
- 部分重叠 range 是 error。
- 完全相同且解码 metadata 一致的 range：
  - 若双方声明 `sharedRange: true` 或 `rangeSharing: shared/alias`，记录 info。
  - 未显式声明共享时记录 warning。
- 完全相同但 codec/schema/splatCount 冲突的 range 是 error。

当 `payloadStatus=placeholder` 时，缺少二进制文件只记 warning。checker 不会假装已验证 placeholder 的物理 range。

### Dependency DAG

- dependency 必须引用存在的 chunk。
- 不允许 self dependency。
- dependency graph 必须是 DAG。
- 重复 dependency 记录 warning。

### Codec 与 Attribute Schema

- codec id 唯一，必须声明 kind 和 attributeSchema。
- chunk codec/schema 引用必须存在并相互一致。
- 固定 `bytesPerSplat` schema 会检查：

```text
byteLength == splatCount * bytesPerSplat
```

- 已知 `raw-gaussian-v0` 固定为 14 个 float32、56 bytes：position 3、scale 3、rotation 4、opacity 1、color 3。
- 已知 `raw-gaussian-sh3-v0` 固定为 59 个 float32、236 bytes：position 3、scale 3、rotation 4、opacity 1、shDc 3、shRest 45。
- SH3 schema 还检查 packed byte offset、little-endian、`wxyz` quaternion、degree 3、Graphdeco channel-major 系数布局、明确的 `R.c1..c15,G.c1..c15,B.c1..c15` 顺序、`position-minus-camera` 方向和 `max(0,0.5+evalSH)` 激活声明。
- 两个 profile 的规范见 `notes/format-cases/w3gs-0.1-payload-profiles.md`。
- 未知 codec 即使声明完整，也只验证通用结构，并报告 `CODEC_UNVERIFIED` warning。
- variable stride codec 报告无法从 splatCount 推导 payload 长度的 warning。

### Startup Fallback

- `startupSet` 必须是有效 layer id 集合。
- startup chunks 必须 dependency-closed。
- 检查 startup 是否包含 root-node layer；缺少时报告 coverage 无法证明。

当前字段可以证明引用闭包，但不能严格证明任意 decoder 上的视觉完整性、codec 可解码性和 fallback 质量。因此 checker 会明确输出 `STARTUP_FALLBACK_UNPROVABLE` warning，而不是擅自补充格式规则。

### Refinement 与 LoD

W3GS 0.1 将两个维度分开：

- layer `kind`：`base` 或 `refinement`。
- `lodRole`：`summary`、`leaf` 或 reference baseline 使用的 `duplicated-original`。

`summary/leaf` 不能冒充 layer `kind`，否则会重新混合 progressive layer 与 LoD 数据角色。

当前支持的 `refinementMode` 值域：

```text
additive
replacement
replace-by-children
residual
```

- `replace-by-children` 要求 node 实际有 children。
- layer/chunk 同时声明 refinementMode 时必须一致。
- refinementPolicy 必须是非空字符串，但 checker 不把单一 scheduler policy 固化成唯一合法策略。
- `lodRole` 识别 `summary`、`leaf`、`duplicated-original`；未知 role warning。

这意味着 checker 支持 parent-summary、duplicated-parent 和其他 contract-compatible 组织方式，不会把当前 reference converter 的输出结构当成整个 W3GS 的唯一结构。

### Runtime Hints

- priority 必须是有限数值；`[0, 100]` 仅作为当前 reference convention，超出时 warning，不作为 W3GS 0.1 规范错误。
- decodeCost 检查有限且非负。
- gpuUploadBytes 检查非负整数。
- 对两个已知 raw profile，chunk `gpuUploadBytes` 与 `byteLength` 不同时 warning。renderer 可能重排、对齐或增加辅助 GPU 数据，当前 contract 尚未声明强制 direct-upload layout。
- runtime profile 的 memoryBudgetMB、maxConcurrentRequests 和 preferredCodec 做类型、范围和引用检查。

这些检查只证明字段结构有效和部分内部自洽，不能证明 priority/error/decodeCost/gpuUploadBytes 的预测准确度，也不能证明性能更好。

## 测试

运行全部测试：

```powershell
python -m unittest discover -s tools/w3gs-validator/tests -v
```

测试在系统临时目录构建 fixture，不修改真实 W3GS 样本。当前覆盖：

- 合法最小样本。
- 缺失 chunk。
- payload range 越界。
- parent/child 不一致。
- dependency cycle。
- 未知 codec。
- raw stride/byteLength 不匹配。
- 错误 startupSet。
- 合法 SH3 profile。
- SH3 错误 stride、属性缺失/乱序、codec/schema 不匹配。

## 当前仓库样本状态

### `point_cloud_parent_summary`

预期为 `PASS`，当前只报告：

- startupSet 的引用与 dependency closure 有效。
- 现有字段仍不足以严格证明视觉 fallback 完整性，因此有一个 warning。

### `w3gs-format-sample`

这是早期结构 placeholder sample。它当前把一个 32-byte 混合精度 placeholder layout 声明为正式 `raw-gaussian-v0`，但当前 raw profile 已固定为 56-byte、14-float32 layout。因此 checker 会正确报告 conformance error。

同时，因为样本声明 `payloadStatus=placeholder`，缺失 `chunks-*.bin` 只报告 warning，而不是 range 已验证。

这个结果不应通过放宽 `raw-gaussian-v0` 规则来掩盖。后续若要修正该结构样本，应把旧 profile 重命名为明确的 placeholder codec/schema，或把 layout 和 chunk table 更新到正式 56-byte raw profile。

## 尚不能证明的内容

- JSON duplicate key 在标准 `json` parser 读取后无法恢复，当前不能检测源文本中的重复 key。
- codec payload 内容是否能被真实 decoder 解码。
- placeholder payload 的物理 range。
- startupSet 的真实视觉完整性和质量。
- replacement active set 在所有 renderer 中的像素级正确性。
- runtime hint 的预测准确度。
- HTTP Range/CDN/cache 的运行时行为。
- Gaussian 数值是否合法，例如 quaternion 是否归一化、opacity 是否在有效范围；当前 checker 只检查 profile 结构和 byte contract，不逐值解码整个 payload。
- SH 系数是否来自正确训练模型、数值是否视觉正确、方向相关颜色是否与参考 renderer 像素等价。
- 渲染质量、透明排序质量、GPU 峰值和性能。

因此，本工具验证的是 W3GS contract 的结构与跨文件语义一致性，不是 renderer、codec 或性能认证。
