# 显式反例

[US English](README.md) | [CN 中文说明](README_zh.md)

本目录保存两种可直接复核的构造：

| 构造 | 图类 | 阶数 | strong Seymour 顶点数 |
|---|---|---:|---:|
| [`tournament24/`](tournament24/) | tournament | 24 | 0 |
| [`oriented36/`](oriented36/) | 带独立簇的 oriented graph | 36 | 0 |

24 阶 tournament 给出了更强的上界。36 阶构造仍予保留，因为它具有非常简洁
的六簇加权吹胀结构，并能按比例扩展成显式无限反例族。

结合另一部分已经验证的 13 阶以下正面结果，当前边界应使用两个不同参数表述：

```text
14 <= n_oriented <= n_tournament <= 24.
```

这里没有证明 24 是最小阶数。14 至 23 阶的启发式搜索不属于已认证结论。
