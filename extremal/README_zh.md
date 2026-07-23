# 13 阶正则 tournament 中 strong Seymour 顶点数量的精确极值

[US English](README.md) | [CN 中文说明](README_zh.md)

## 核心结论

本包给出一个可复核的计算机辅助证明：

> **每个 13 阶正则 tournament 至少包含 11 个 strong Seymour 顶点，而且这个下界是紧的。**

等价地说：

> 一张 13 阶正则 tournament 中，非 strong Seymour 顶点最多只有 2 个；并且确实存在恰有 2 个非 strong 顶点的例子。

这严格强化了“至少存在一个 strong Seymour 顶点”的先前计算结论。

## 数学归约

在 13 阶正则 tournament 中，每个顶点有 6 个出邻居和 6 个入邻居，而且

\[
N^{++}(x)=N^-(x).
\]

所以，固定顶点 \(x\) 后，strong Seymour 条件等价于一个 \(6\times6\) 二部图存在完美匹配。

顶点 \(x\) 非 strong，当且仅当这个二部图存在大小至多 5 的顶点覆盖。SAT 编码为每个被声明为非 strong 的顶点附带一个这样的覆盖证书。

为了证明非 strong 顶点最多有 2 个，我们反设至少有 3 个。选择其中一个失败顶点作为根 0，并把其出邻居重标为 1–6、入邻居重标为 7–12。根的一个大小至多 5 的覆盖可补成大小恰好 5。若该覆盖左侧选了 \(p\) 个点，则 \(p\in\{0,1,2,3,4,5\}\)。在左右两侧内部重新标号后，所有潜在反例至少落入六个规范化分支之一。

六个分支全部 UNSAT，因此不可能存在 3 个非 strong 顶点。

## UNSAT 证书

“至少 3 个非 strong 顶点”的六个分支结果为：

| 根覆盖左侧数 \(p\) | 状态 | RUP 证明行数（含终止空子句 `0`） |
|---:|---|---:|
| 0 | UNSAT | 1 |
| 1 | UNSAT | 1 |
| 2 | UNSAT | 19031 |
| 3 | UNSAT | 19236 |
| 4 | UNSAT | 1 |
| 5 | UNSAT | 1 |

每个证明均通过两套实现方式不同的 RUP 检查器：

1. watched-literal C++ 检查器；
2. full-scan/occurrence C++ 检查器。

若系统安装了 `drat-trim`，`run_all.sh` 还会自动以 `-U` 模式执行第三方 RUP 检查。

独立审计还以 GCC 11.4.0 从源码编译了上游官方检查器提交
`2e3b2dc0ecf938addbd779d42877b6ed69d9a985`。六份证明在 RUP-only
模式（`-U`）下均以退出码 0 结束并报告 `s VERIFIED`，RAT 引理数均为 0。
逐分支完整日志和构建来源见 `upstream_drat_trim/`。

## 紧致实例

`tight/m2_p2.model` 给出一张合法的 13 阶正则 tournament。独立最大匹配检查结果为：

```text
[5, 6, 6, 6, 6, 5, 6, 6, 6, 6, 6, 6, 6]
```

因此只有顶点 0 和 5 非 strong，其他 11 个顶点均为 strong。

顶点 0 的 Hall 缺陷证书为：

\[
S=\{3,4,5,6\},\qquad \Gamma(S)=\{7,8,9\},
\]

所以 \(|\Gamma(S)|=3<4=|S|\)。

顶点 5 的 Hall 缺陷证书为：

\[
S=\{3,4,6\},\qquad \Gamma(S)=\{7,9\},
\]

所以 \(|\Gamma(S)|=2<3=|S|\)。

完整匹配和邻接矩阵见 `tight/tight_instance_analysis.json`。

## 一键复现

Ubuntu 22.04 / Debian 类环境：

```bash
sudo apt install g++ python3 drat-trim
bash run_all.sh
```

`drat-trim` 是可选项；没有安装时，两套内置 RUP 检查器仍会执行。

## 文件说明

- `src/generate_extremal_cnf.py`：生成“至少 m 个非 strong 顶点”的六分支 CNF；
- `src/cdcl.cpp`：生成 SAT 模型或 RUP 证明；
- `src/rupcheck.cpp`：watched-literal RUP 检查器；
- `src/scan_rupcheck.cpp`：独立 full-scan/occurrence RUP 检查器；
- `src/analyze_tight_instance.py`：独立检查紧致实例的正则性、匹配和 Hall 缺陷；
- `certificates/`：六个 UNSAT 实例和 RUP 证明；
- `tight/`：达到下界 11 的 SAT 实例；
- `upstream_drat_trim/`：上游官方检查器来源、构建信息和六份完整日志；
- `RESULTS.json`：机器可读结果摘要。

## 结论的准确表述

推荐在论文中写成：

> Every regular tournament on 13 vertices contains at least eleven strong Seymour vertices, and this bound is sharp.

这是一项经过可检查 SAT 证书支持的计算机辅助结果，尚未经过同行评审，也不是定理证明器中的完全形式化证明。
