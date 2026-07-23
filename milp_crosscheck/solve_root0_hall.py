from __future__ import annotations
import sys
from typing import Dict
import numpy as np
from scipy.optimize import milp, Bounds, LinearConstraint
from scipy.sparse import coo_matrix

N=13; K=6
S_CASE=int(sys.argv[1]) if len(sys.argv)>1 else -1
idx={}; names=[]
def add(name): idx[name]=len(names); names.append(name); return idx[name]
for i in range(N):
    for j in range(i+1,N): add(('o',i,j))
for x in range(N):
    for v in range(N):
        if v!=x:
            add(('s',x,v))   # Hall-deficient subset S_x of N+(x)
            add(('n',x,v))   # its out-neighborhood inside N-(x)
NV=len(names)

def arc(u,v):
    if u<v: return 0.0,{idx[('o',u,v)]:1.0}
    return 1.0,{idx[('o',v,u)]:-1.0}

rows=[]; lbs=[]; ubs=[]
def con(expr:Dict[int,float],lb=-np.inf,ub=np.inf,const=0.0):
    rows.append(dict(expr)); lbs.append(lb-const if np.isfinite(lb) else -np.inf); ubs.append(ub-const if np.isfinite(ub) else np.inf)

# Symmetry: root 0 has outneighbors 1..6 and inneighbors 7..12.
for j in range(1,7): con({idx[('o',0,j)]:1},lb=1,ub=1)
for j in range(7,13): con({idx[('o',0,j)]:1},lb=0,ub=0)

# Canonicalize root-0 Hall witness by its size: selected A vertices are 1..S_CASE.
if 1<=S_CASE<=6:
    for v in range(1,7):
        val=1 if v<=S_CASE else 0
        con({idx[('s',0,v)]:1},lb=val,ub=val)

# Regularity.
for u in range(N):
    expr={}; c0=0.0
    for v in range(N):
        if u==v: continue
        c,e=arc(u,v); c0+=c
        for z,a in e.items(): expr[z]=expr.get(z,0)+a
    con(expr,lb=K,ub=K,const=c0)

# Every root x has a Hall-deficient set S_x.
for x in [0]:
    size_expr={}
    for v in range(N):
        if v==x: continue
        sv=idx[('s',x,v)]; nv=idx[('n',x,v)]
        size_expr[nv]=size_expr.get(nv,0)+1
        size_expr[sv]=size_expr.get(sv,0)-1

        # s[x,v] only if x->v
        c,e=arc(x,v); expr={sv:1}
        for z,a in e.items(): expr[z]=expr.get(z,0)-a
        con(expr,ub=0,const=-c)
        # n[x,v] only if v->x
        c,e=arc(v,x); expr={nv:1}
        for z,a in e.items(): expr[z]=expr.get(z,0)-a
        con(expr,ub=0,const=-c)

    # |N(S)| <= |S|-1
    con(size_expr,ub=-1)

    # If a in S, b->x, and a->b, then b is in N(S).
    for a in range(N):
        if a==x: continue
        for b in range(N):
            if b==x or b==a: continue
            # n_b - s_a - I(b->x) - I(a->b) +2 >=0
            expr={idx[('n',x,b)]:1, idx[('s',x,a)]:-1}
            c0=2.0
            for u,v in ((b,x),(a,b)):
                c,e=arc(u,v); c0-=c
                for z,q in e.items(): expr[z]=expr.get(z,0)-q
            con(expr,lb=0,const=c0)

rr=[];cc=[];dd=[]
for i,row in enumerate(rows):
    for j,val in row.items():
        if val: rr.append(i);cc.append(j);dd.append(val)
A=coo_matrix((dd,(rr,cc)),shape=(len(rows),NV)).tocsr()
print(f'case={S_CASE} vars={NV} cons={len(rows)} nnz={A.nnz}',flush=True)
res=milp(c=np.zeros(NV),integrality=np.ones(NV),bounds=Bounds(np.zeros(NV),np.ones(NV)),constraints=LinearConstraint(A,np.array(lbs),np.array(ubs)),options={'time_limit':300,'mip_rel_gap':0.0,'presolve':True,'disp':True})
print('status',res.status); print('message',res.message); print('success',res.success)
if res.x is not None:
    sol=np.rint(res.x).astype(int); adj=np.zeros((N,N),dtype=int)
    for i in range(N):
        for j in range(i+1,N):
            z=sol[idx[('o',i,j)]];adj[i,j]=z;adj[j,i]=1-z
    print('degrees',adj.sum(1).tolist())
    for row in adj: print(''.join(map(str,row.tolist())))
    for x in range(N):
        S=[v for v in range(N) if v!=x and sol[idx[('s',x,v)]]]
        R=[v for v in range(N) if v!=x and sol[idx[('n',x,v)]]]
        print('witness',x,S,R)
