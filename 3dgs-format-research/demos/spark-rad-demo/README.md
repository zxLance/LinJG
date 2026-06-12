# Spark RAD Demo Sample

本目录保存 Spark RAD 学习过程中使用的真实 `.rad` 样本。

## 本地文件

| 文件 | 大小 | 说明 |
| --- | ---: | --- |
| `coit-40m-sh1-lod.rad` | 1,280,517,688 bytes | Spark 学习 demo 使用的公开远程 RAD 文件的本地副本。 |

## 来源记录

- URL: `https://storage.googleapis.com/forge-dev-public/asundqui/rad/260217/coit-40m-sh1-lod.rad`
- 远程探测曾记录：
  - `Accept-Ranges = bytes`
  - `Content-Length = 1,280,517,688`
  - `Last-Modified = Wed, 18 Feb 2026 04:09:51 GMT`

## 研究用途

这个文件可以用于验证 Spark RAD 的真实二进制结构、header / chunk meta / payload 位置，以及浏览器 Range 请求如何按 chunk 读取数据。

注意：它是大体积下载样本，不建议作为普通 Git blob 提交。后续如果需要公开复现实验，应优先提供下载脚本、Range 片段验证脚本，或使用更小的可复现 RAD 样本。
