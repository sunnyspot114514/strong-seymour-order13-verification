# 显式反例

[US English](README.md) | [CN 中文说明](README_zh.md)

本目录保存三种可直接复核的构造：

| 构造 | 图类 | 阶数 | strong Seymour 顶点数 |
|---|---|---:|---:|
| [`tournament23/`](tournament23/) | tournament | 23 | 0 |
| [`tournament24/`](tournament24/) | tournament | 24 | 0 |
| [`oriented36/`](oriented36/) | 带独立簇的 oriented graph | 36 | 0 |

23 阶 tournament 给出了当前更强的上界。24 阶和 36 阶构造仍予保留，因为
它们具有非常简洁的加权吹胀结构。

结合另一部分已经验证的 13 阶以下正面结果，当前边界应使用两个不同参数表述：

```text
14 <= n_oriented <= n_tournament <= 23.
```

这里没有证明 23 是最小阶数。14 至 22 阶的精确搜索在得到可检查的 SAT
见证或经过认证的 UNSAT 结果以前，会与已认证结论分开记录。
