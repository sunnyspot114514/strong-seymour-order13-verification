# Strong Seymour 猜想的 24 阶 tournament 反例

本目录给出一个结构化、可人工复核的 **24 阶 tournament**，其中没有任何 strong Seymour vertex。

这同时说明：

1. strong Seymour 猜想对一般 oriented graph 为假；
2. 即使限制在 tournament 上，该强化猜想仍然为假；
3. 结合此前至多 13 阶的正面验证，最小 tournament 反例阶数目前满足 `14 <= n_min <= 24`。

## 构造摘要

以 10 顶点 tournament 模板

```text
110000101011101000010111101010010100010010010
```

为基础，使用权重

```text
(5,1,2,2,3,1,2,5,1,2)
```

替换其顶点。簇间方向继承模板，簇内使用传递 tournament。总阶数为 24。

关键的“传递补全引理”说明：非末位簇内顶点具有一个单点 Hall 缺陷，末位顶点继承类级加权 Hall 缺陷。完整人工证明见 [`docs/PROOF_zh.md`](docs/PROOF_zh.md)。

## 独立验证

- Python：逐顶点计算严格二阶邻域、最大匹配并穷举 Hall 缺陷；
- C++：独立重建 tournament，并用增广路匹配和 Hall 子集检查；
- 两者均确认 24 个顶点全部非 strong。

邻接矩阵 SHA-256：

```text
d3b70f40dd3cc33f66ba23dcbb99138580d6cd6d6684e3658028606d680d23ed
```

## 复现

```bash
bash run_all.sh
```

## 文件

- `data/adjacency_matrix.txt`：完整 24×24 邻接矩阵；
- `data/full_verification.json`：逐顶点匹配数和 Hall 证书；
- `src/verify.py`：Python 验证器；
- `src/verify.cpp`：独立 C++ 验证器；
- `audit/independent_audit.py`：有限状态 DP 审计器，可选调用 NetworkX；
- `audit/AUDIT_REPORT.md`：独立复核报告；
- `docs/PROOF_zh.md`：人工证明；
- `RESULTS.json`：结果摘要。

## 可信边界

这是一个显式有限反例，不依赖 SAT 不可满足结论。结合单独的 13 阶以下
正面验证，当前边界应写成

```text
14 <= n_oriented <= n_tournament <= 24.
```

正确性依赖构造数据、严格二阶邻域定义、Hall 定理和公开验证器。目前尚未
同行评审，也没有证明 24 为最小阶数。
