# 最小 tournament 反例研究

[US English](README.md) | [CN 中文说明](README_zh.md)

本目录包含继续压缩当前最小已知 tournament 反例的可复现实验代码。22 阶精确
搜索在 `d=9,p=2` 分支找到一个模型；删去其中的 universal source 后得到一张
经过独立验证的 21 阶反例。冻结复现包位于
[`counterexamples/tournament21/`](../../counterexamples/tournament21/)。
搜索失败和求解超时都不等于不存在证明。

## 精确编码

对 tournament 中的根顶点 `r`，匹配图存在边 `y--z` 当且仅当
`r -> y -> z -> r` 构成有向三角形。由 König 定理，`r` 非 strong 当且仅当该二部图存在大小至多为 `d+(r)-1` 的顶点覆盖。

`generate_tournament_cnf.py` 对每个根同时编码这一条件，并完整处理：

- 将一个最小出度顶点重标为 0；
- 固定其出邻居、入邻居的编号区间；
- 对所有顶点强制相同的最小出度下界；
- 按根覆盖中出邻域顶点数 `p` 作规范分支；
- 在四个可自由重标的成员块内固定有向 Hamilton 路，作为不漏解的对称性破除。

23 阶 tournament 的最小出度不超过 11；结合已知的 `δ+(D) <= 5` 定理，完整搜索范围为

```text
d = 6,...,11
p = max(0, 2d-23),...,d-1.
```

示例：

```bash
python generate_tournament_cnf.py 23 7 work/n23_d7_p3.cnf \
  --encoding cover --root-cover-left 3
kissat work/n23_d7_p3.cnf > work/n23_d7_p3.model
python verify_tournament_model.py \
  work/n23_d7_p3.json work/n23_d7_p3.model work/verified.json
```

模型复核器不信任 SAT 模型中的覆盖变量，而是重新计算全部严格二阶邻域、最大匹配和 Hall 缺陷。

此外：

- `solve_tournament_milp.py` 提供紧凑的 HiGHS 0–1 MILP 编码；
- `solve_tournament_cpsat.py` 提供 OR-Tools CP-SAT 编码；
- `solve_with_pysat.py` 可调用 Glucose3、Glucose4、Minisat22 等 PySAT 后端。

可选依赖：

```bash
python -m pip install scipy python-sat ortools
```

## 构造搜索

`search_tournament.cpp` 从 24 阶反例的删点子图出发，同时使用单边翻转和保持所有出度不变的有向三角形反转。每个候选都对全部根顶点执行精确最大匹配。

```bash
g++ -O3 -std=c++17 -Wall -Wextra -Wpedantic -Werror \
  search_tournament.cpp -o search_tournament
./search_tournament \
  ../../counterexamples/tournament24/data/adjacency_matrix.txt \
  30 250000 779 4 0 7
```

`analyze_tournament.py` 可独立分析任意邻接矩阵，输出 strong 顶点、最小覆盖以及距离 Hall 缺陷最近的大小 `d-1` 覆盖。

`search_weighted_templates.py` 则搜索 tournament 模板的传递吹胀：逐根枚举 Pareto 极大的加权 Hall 证书，再用整数规划选择正整数簇权。

## 当前结果

截至 2026-07-29：

- 22 阶 `d=9,p=2` 分支为 SAT；删去模型中的 universal source 后，得到一张
  经过验证、strong 顶点数为 0 的 21 阶反例；
- 当前严格边界为 `14 <= n_min <= 21`；
- 精确最小阶数搜索已经下移到 20 阶；
- 固定 24 阶反例的 SAT、MILP、CP-SAT 正对照全部通过，并由独立匹配程序复核；
- 13 阶正则 tournament 的六个控制分支全部 UNSAT；
- 原 10 点模板以及距离它至多两条边的全部 1,036 个模板，在总权不超过 23 时均不可行；
- 另检查了距离 3 的 2,000 个固定样本和 1,000 个随机 10 点模板，均未找到总权 23 的构造；详见 `STRUCTURED_RESULTS.json`。

21 阶见证是经过检查的反例，不是由限时运行推断出的结论。只有当某个
更小阶数的全部完备分支结束，并且所有 UNSAT 证明由标准检查器复核后，才会
把该阶数纳入已排除的下界。
