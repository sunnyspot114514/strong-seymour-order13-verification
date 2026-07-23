# 13 阶正则 tournament 中 strong Seymour 顶点数量的精确极值

[US English](README.md) | [CN 中文说明](README_zh.md)

本仓库给出以下精确有限结论的可复现计算机辅助验证：

> **每个 13 阶正则 tournament 至少包含 11 个 strong Seymour 顶点，而且这个下界是紧的。**

等价地说，非 strong Seymour 顶点最多有 2 个，并且仓库中给出了一张恰好达到 2 个的 tournament。

强化实验、证书与紧致实例位于 [`extremal/`](extremal/)。

## 证据摘要

上界实验检验是否存在至少 3 个非 strong 顶点的 13 阶正则 tournament。任选一个失败顶点作为根，并规范化其补齐到大小 5 的顶点覆盖后，所有候选反例必落入 `p=0,...,5` 六个分支之一。六个分支全部 UNSAT：

| 根分支 `p` | 结果 | RUP 证明行数（含终止空子句 `0`） |
|---:|---|---:|
| 0 | UNSAT | 1 |
| 1 | UNSAT | 1 |
| 2 | UNSAT | 19031 |
| 3 | UNSAT | 19236 |
| 4 | UNSAT | 1 |
| 5 | UNSAT | 1 |

每份证明均通过：

- 包内 watched-literal C++ RUP 检查器；
- 独立实现的 full-scan/occurrence C++ RUP 检查器；
- 上游官方 `drat-trim` 提交
  `2e3b2dc0ecf938addbd779d42877b6ed69d9a985`，以 GCC 11.4.0 从源码编译并在
  RUP-only 模式（`-U`）运行：六个分支全部报告 `s VERIFIED`，RAT 引理数均为 0；
- 另一轮审计使用 Debian `drat-trim` 0.0~git20240428.effa1dc-2，同样全部通过。

达到下界的实例的 13 个最大匹配数为：

```text
[5, 6, 6, 6, 6, 5, 6, 6, 6, 6, 6, 6, 6]
```

所以只有顶点 0 和 5 非 strong，其他 11 个顶点均为 strong；两者的显式 Hall 缺陷证书均已公开。

## 独立完整枚举

第二条证明路线完全绕过 SAT 编码，直接枚举 Brendan McKay 目录中全部
1,495,297 个 13 阶正则 tournament 非同构类，并分别用 Hall 子集穷举和最大匹配算法检查。两种实现对全部 19,438,861 次顶点检查零分歧。

得到的非标号分布为：

| strong 顶点数 | 非同构类数量 |
|---:|---:|
| 11 | 13 |
| 12 | 48 |
| 13 | 1,495,236 |

源码、固定的数据来源信息、完整结果、日志和一键复现脚本见
[`enumeration/`](enumeration/)。

全部 61 个未达到 13 个 strong 顶点的同构类均已公开，并附 Hall 缺陷与完美
匹配证书。此外，从认证源码编译的 nauty 2.9.3 `gentourng` 独立重新生成了
全部 1,495,297 个类，得到相同分布；`labelg` 规范比较也确认两条路线得到
完全相同的 61 个异常同构类。

## 一键复现强化实验

需要 Python 3、Bash 和支持 C++17 的 `g++`。`drat-trim` 可选但建议安装。

```bash
cd extremal
bash run_all.sh
```

脚本从源码重新编译，重新生成全部 CNF、证明、模型与分析文件，运行两套内置证明检查器及可选的 `drat-trim`，并逐一比较发布文件与重生成文件。

数学归约见 [`extremal/README_zh.md`](extremal/README_zh.md)，独立 WSL/Ubuntu 复核见 [`extremal/AUDIT_REPORT.md`](extremal/AUDIT_REPORT.md)。

## 保留的早期基线实验

仓库根目录仍保留早期“至少存在 1 个 strong 顶点”的验证包及其 MILP 交叉验证：

```bash
bash run_all.sh
bash run_milp_all.sh
```

结合 Bai、Li、Park 论文
[*Towards a strengthening of the second neighborhood conjecture*](https://arxiv.org/abs/2607.18047)
中的定理，可推出所有不超过 13 个顶点的 oriented graph 至少有一个 strong Seymour vertex。强化后的“至少 11 个”只适用于 13 阶正则 tournament，不能直接推广到所有小阶 oriented graph。

## 结论边界

这是尚未经过同行评审的有限计算机辅助结果。RUP 证书证明所发布 CNF 不可满足；图论结论还依赖于文档中的数学归约以及 CNF 生成器的正确性。
