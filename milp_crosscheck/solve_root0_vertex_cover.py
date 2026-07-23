from __future__ import annotations

from itertools import combinations
from dataclasses import dataclass
from typing import Dict, Tuple
import sys

import numpy as np
from scipy.optimize import milp, Bounds, LinearConstraint
from scipy.sparse import coo_matrix

N = 13
K = 6
P_CASE = int(sys.argv[1]) if len(sys.argv) > 1 else -1

# Variables:
# o[i,j] for i<j: 1 iff i -> j
# l[x,v]: selected left-cover vertex v (must be x -> v)
# r[x,v]: selected right-cover vertex v (must be v -> x)
idx = {}
names = []

def add_var(name):
    i = len(names)
    names.append(name)
    idx[name] = i
    return i

for i in range(N):
    for j in range(i+1, N):
        add_var(("o", i, j))
for x in range(N):
    for v in range(N):
        if v != x:
            add_var(("l", x, v))
            add_var(("r", x, v))

NV = len(names)

# Return affine expression for indicator u -> v as (const, {var: coeff}).
def arc(u: int, v: int):
    assert u != v
    if u < v:
        return 0.0, {idx[("o", u, v)]: 1.0}
    else:
        # u -> v iff not (v -> u)
        return 1.0, {idx[("o", v, u)]: -1.0}

rows = []
lbs = []
ubs = []

def add_constraint(expr: Dict[int, float], lb=-np.inf, ub=np.inf, const=0.0):
    # lb <= const + sum coeff*x <= ub
    rows.append(expr.copy())
    lbs.append(lb - const if np.isfinite(lb) else -np.inf)
    ubs.append(ub - const if np.isfinite(ub) else np.inf)

# Symmetry breaking: in any regular tournament, relabel a chosen vertex as 0,
# its six out-neighbors as 1..6, and its six in-neighbors as 7..12.
for j in range(1, 7):
    add_constraint({idx[("o", 0, j)]: 1.0}, lb=1.0, ub=1.0)
for j in range(7, 13):
    add_constraint({idx[("o", 0, j)]: 1.0}, lb=0.0, ub=0.0)

# For a fixed case p=0..5, canonicalize a size-5 vertex cover for root 0.
# Any cover of size <=5 can be extended to size 5, and labels may be permuted
# independently inside N+(0)={1..6} and N-(0)={7..12}.
if 0 <= P_CASE <= 5:
    q = 5 - P_CASE
    for v in range(1, 7):
        val = 1.0 if v <= P_CASE else 0.0
        add_constraint({idx[("l", 0, v)]: 1.0}, lb=val, ub=val)
    for off, v in enumerate(range(7, 13), start=1):
        val = 1.0 if off <= q else 0.0
        add_constraint({idx[("r", 0, v)]: 1.0}, lb=val, ub=val)

# Every vertex has outdegree K.
for u in range(N):
    expr = {}
    const = 0.0
    for v in range(N):
        if v == u:
            continue
        c, e = arc(u, v)
        const += c
        for z, a in e.items():
            expr[z] = expr.get(z, 0.0) + a
    add_constraint(expr, lb=K, ub=K, const=const)

# For each root x, choose a vertex cover of the bipartite graph H_x
# (left=N+(x), right=N-(x)) of size at most K-1.
# In a regular tournament, N++(x)=N-(x): if b->x and b dominated all K
# out-neighbors of x, b would have outdegree at least K+1.
for x in [0]:
    cover_expr = {}
    for v in range(N):
        if v == x:
            continue
        li = idx[("l", x, v)]
        ri = idx[("r", x, v)]
        cover_expr[li] = 1.0
        cover_expr[ri] = 1.0

        # l[x,v] <= [x -> v]
        c, e = arc(x, v)
        expr = {li: 1.0}
        for z, a in e.items():
            expr[z] = expr.get(z, 0.0) - a
        add_constraint(expr, ub=0.0, const=-c)

        # r[x,v] <= [v -> x]
        c, e = arc(v, x)
        expr = {ri: 1.0}
        for z, a in e.items():
            expr[z] = expr.get(z, 0.0) - a
        add_constraint(expr, ub=0.0, const=-c)

    add_constraint(cover_expr, ub=K-1)

    # If x->a, b->x, and a->b, then edge a-b is in H_x and must be covered.
    for a in range(N):
        if a == x:
            continue
        for b in range(N):
            if b == x or b == a:
                continue
            # l[x,a] + r[x,b] >= I(x->a)+I(b->x)+I(a->b)-2
            expr = {idx[("l", x, a)]: 1.0, idx[("r", x, b)]: 1.0}
            const = 2.0
            for u, v in ((x, a), (b, x), (a, b)):
                c, e = arc(u, v)
                const -= c
                for z, coef in e.items():
                    expr[z] = expr.get(z, 0.0) - coef
            add_constraint(expr, lb=0.0, const=const)

# Sparse matrix
rr=[]; cc=[]; dd=[]
for i,row in enumerate(rows):
    for j,val in row.items():
        if val:
            rr.append(i); cc.append(j); dd.append(val)
A = coo_matrix((dd,(rr,cc)), shape=(len(rows), NV)).tocsr()
constraints = LinearConstraint(A, np.array(lbs), np.array(ubs))

print(f"case={P_CASE}, variables={NV}, constraints={len(rows)}, nnz={A.nnz}", flush=True)
res = milp(
    c=np.zeros(NV),
    integrality=np.ones(NV),
    bounds=Bounds(np.zeros(NV), np.ones(NV)),
    constraints=constraints,
    options={"time_limit": 300, "mip_rel_gap": 0.0, "presolve": True, "disp": True},
)
print("status", res.status)
print("message", res.message)
print("success", res.success)
print("fun", res.fun)

if res.x is not None:
    sol = np.rint(res.x).astype(int)
    # Print adjacency matrix
    adj = np.zeros((N,N), dtype=int)
    for i in range(N):
        for j in range(i+1,N):
            z=sol[idx[("o",i,j)]]
            adj[i,j]=z
            adj[j,i]=1-z
    print("degrees", adj.sum(axis=1).tolist())
    print("adjacency")
    for row in adj:
        print(''.join(map(str,row.tolist())))
    print("covers")
    for x in range(N):
        L=[v for v in range(N) if v!=x and sol[idx[("l",x,v)]]]
        R=[v for v in range(N) if v!=x and sol[idx[("r",x,v)]]]
        print(x, L, R, len(L)+len(R))
