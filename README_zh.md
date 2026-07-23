# 强 Seymour 猜想：13 阶精确计算验证

本仓库给出下列有限命题的可复现计算机辅助验证：

> 每个 13 阶正则 tournament 都至少包含一个 strong Seymour vertex。

结合 Bai、Li、Park 的论文
[*Towards a strengthening of the second neighborhood conjecture*](https://arxiv.org/abs/2607.18047)
中关于 `δ+(D) ≤ 5` 的定理，可以推出：

> 每个顶点数不超过 13 的 oriented graph 都包含 strong Seymour vertex。

## 数学化约

13 阶 oriented graph 若不能被 `δ+(D) ≤ 5` 的定理覆盖，则每个顶点的
出度至少为 6。出度总和至少为 `13×6=78`，而 13 个顶点之间至多只有
`C(13,2)=78` 条弧。因此所有等号必须同时成立：该图是每个顶点出度都
恰好为 6 的正则 tournament。

在这种 tournament 中固定顶点 `x`：

- `|N+(x)| = |N-(x)| = 6`；
- `N++(x) = N-(x)`；
- `x` 是 strong Seymour vertex，当且仅当从 `N+(x)` 到 `N-(x)` 的
  二部图存在大小为 6 的完美匹配。

由 König 定理，`x` 不是 strong 当且仅当这个二部图存在大小至多为 5
的顶点覆盖。反例要求 13 个顶点全部拥有这种失败证书。

利用重新编号固定顶点 0 的六个出邻点和六个入邻点。把顶点 0 的一个
大小为 5 的覆盖中左侧顶点数记为 `p`，则只需检查：

```text
p = 0, 1, 2, 3, 4, 5
```

这六种证书形状覆盖所有可能。六个 CNF 分支全部不可满足。

## 仓库内容

- `generate_cnf.py`：确定性生成六个 CNF；
- `cdcl.cpp`：输出 RUP 证明的小型 CDCL 求解器；
- `rupcheck.cpp`：watched-literal RUP 检查器；
- `naive_rupcheck.py`：独立的全扫描单位传播检查器；
- `cases/`：公开的 CNF、RUP 证明、元数据与检查日志；
- `generate_control.py`、`verify_control.py`：可满足反向对照；
- `milp_crosscheck/`：顶点覆盖与 Hall 缺陷集两套 MILP 模型；
- `AUDIT_REPORT.md`：Ubuntu 22.04 与第三方检查器的独立复核报告；
- `RESULTS.json`：机器可读结果摘要。

仓库不包含预编译可执行文件、虚拟环境、本机绝对路径、用户名或原工作
目录信息。

## 一键复现 SAT 验证

需要 Python 3、`g++` 和 Bash。在仓库根目录运行：

```bash
./run_all.sh
```

脚本只使用仓库相对路径。它会：

1. 从源码编译求解器和检查器；
2. 重新生成六个 CNF；
3. 重新求解并生成 RUP 证明；
4. 使用两个实现方式不同的检查器核验证明；
5. 验证一个可满足的反向对照；
6. 如果系统 `PATH` 中存在 `drat-trim`，再进行第三方验证。

所有生成物只写入已被 Git 忽略的 `build/` 与 `regenerated/`。

## 复现 MILP 交叉验证

在独立环境中安装 NumPy、SciPy，然后运行：

```bash
./run_milp_all.sh
```

它会执行：

- 顶点覆盖编码的六个分支 `p=0,...,5`；
- Hall 缺陷集编码的六个分支 `|S|=1,...,6`；
- 三个可满足反向对照矩阵的直接匹配与 Hall 子集检查。

十二个完整反例分支均应报告 `status 2` / `infeasible`。

## 结论边界

这证明的是 13 阶及以下的有限情形，不是任意阶 strong Seymour 猜想的
一般证明。RUP 证书证明了公开 CNF 的不可满足性；图论结论还依赖于上述
数学化约和 CNF 生成器的正确性。

若希望进一步缩小可信基，可以生成 LRAT 证书并使用形式化验证过的
LRAT checker。
