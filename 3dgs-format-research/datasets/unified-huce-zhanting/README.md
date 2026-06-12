# HuCeZhanTing 统一实验子集

本目录保存统一源 PLY 的本地生成子集及可追踪 manifest。

统一源：

```text
D:\DATA\3DGS\PLY\HuCeZhanTing.ply
```

生成命令与完整 hash 见 `dataset-manifest.json`。二进制 PLY 文件被 `.gitignore` 排除；manifest 和本 README 可以提交，用于复现实验和确认本地数据是否一致。

## 许可边界

当前未确认源数据许可和派生子集的公开再分发权。10K 与 250K 文件只作为本地研究基准，不应自动上传、公开或随代码仓库分发。

## 属性边界

采样阶段完整保留源文件全部 62 个属性和 SH3 数据。后续目标格式如果只支持 SH0，属性损失发生在目标格式转换链，不应回写或修改这里的共同 PLY 子集。
