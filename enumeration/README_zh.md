# 13 阶正则 tournament 完整枚举复核

[US English](README.md) | [CN 中文说明](README_zh.md)

## 结论

本目录给出精确极值定理的第二条计算证明路线：

> 每个 13 阶正则 tournament 至少包含 11 个 strong Seymour 顶点，而且该界可达到。

这条路线不使用 CNF 生成器、失败旗标、基数编码、六个对称分支、SAT 求解器或 RUP 证书。

## 完整数据库

输入为 Brendan McKay 公布的 13 阶正则 tournament 非同构类完整目录，每个同构类恰有一个代表：

- 来源：`https://users.cecs.anu.edu.au/~bdm/data/rt13.txt.gz`；
- 压缩大小：8,498,810 字节；
- SHA-256：
  `df63dbf6d173094b7fc31866f928410bd6738403d06be9b407eb5e28970fd058`；
- 解压记录数：1,495,297。

仓库不转存该第三方数据库，而是在复现时从权威来源下载。详细来源见
[DATASET_PROVENANCE.md](DATASET_PROVENANCE.md)。

## 直接验证方法

对于目录中的每条记录，C++ 验证器：

1. 解码 78 位上三角邻接表示；
2. 检查 13 个顶点的出度是否均为 6；
3. 对每个顶点 `x`，建立从 `N+(x)` 到 `N-(x)` 的 `6 x 6` 二部图；
4. 穷举全部 Hall 子集判断是否存在完美匹配；
5. 另用 Kuhn 增广路算法独立计算最大匹配；
6. 两种算法只要有一次不一致就立即失败。

全部 1,495,297 张图、共 19,438,861 次顶点检查均完成，两种算法零分歧。

## 非同构类分布

| strong 顶点数 | 非同构类数量 |
|---:|---:|
| 11 | 13 |
| 12 | 48 |
| 13 | 1,495,236 |
| **合计** | **1,495,297** |

这是非标号分布：每个同构类只计一次，并未按该类包含的标号 tournament 数加权。

按目录顺序，第一个达到最小值的实例位于第 764,615 条，其最大匹配数为：

```text
[5, 6, 6, 6, 5, 6, 6, 6, 6, 6, 6, 6, 6]
```

它的非 strong 顶点为 0 和 4。完整邻接矩阵及 Hall 缺陷见
[RESULTS.json](RESULTS.json)。另一份 Python 验证器使用穷举部分单射和 Hall
子集重新检查该实例，不调用 C++ 的匹配实现。

## 全部 61 个异常类

[EXCEPTIONAL_CLASSES.jsonl](EXCEPTIONAL_CLASSES.jsonl) 收录全部未达到 13 个
strong 顶点的同构类：13 个 strong 数为 11 的类和 48 个 strong 数为 12
的类。每条记录包含目录索引与编码、全部最大匹配数、每个非 strong 顶点的
Hall 缺陷，以及每个 strong 顶点的一份显式完美匹配。

独立 Python 检查器穷举重算了全部 793 个根匹配实例，并直接检查了 719
份完美匹配证书和 74 份 Hall 缺陷。结果见
[EXCEPTIONAL_VERIFICATION.json](EXCEPTIONAL_VERIFICATION.json)。

## 使用 gentourng 独立重新生成

从官方来源核验并编译 nauty 2.9.3 后运行：

```bash
gentourng -d6 -D6 13
```

生成器重新产生了 1,495,297 个非同构 tournament。将输出流直接送入验证器，
再次得到完整的 `13 / 48 / 1,495,236` 分布。下载目录和重新生成流中的 61
个异常类经 `labelg` 规范标号后集合完全相同，strong 数也逐类一致。详细来源
与日志见 [GENTOURNG_PROVENANCE.md](GENTOURNG_PROVENANCE.md)。

## 从下载目录一键复现

需要 Bash、`curl`、`gzip`、GNU coreutils、支持 C++17 的 `g++`、Python 3
以及 `/usr/bin/time`。

```bash
cd enumeration
bash run_enumeration.sh
```

脚本会下载并核验数据库、编译验证器、完整枚举、比较确定性产物，并独立复核
第一个极值实例和全部 61 个异常类。生成物只写入已被 Git 忽略的
`enumeration/work/`。

## 从生成器源码一键复现

还需要 GNU Make 和 C 编译器。

```bash
cd enumeration
bash run_gentourng.sh
```

该脚本会下载并认证 nauty 2.9.3 源码，编译 `gentourng` 和 `labelg`，重新
生成完整非同构流，检查每个顶点，并规范比较两条路线得到的异常同构类。

## 可信边界

这条路线独立于 SAT 编码，但依赖 McKay 同构类目录的完整性与正确性、公开的 78 位格式以及两套直接图算法。因此它是一条本质不同的强交叉验证，但不是对该数据库本身的独立重新生成。

`gentourng` 运行消除了对已下载静态文件完整性的依赖，但仍属于 McKay/nauty
软件生态。两种枚举方式共同依赖 strong Seymour 条件与根顶点 `6 x 6`
完美匹配条件之间的数学等价。
