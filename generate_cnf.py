from __future__ import annotations
import sys, json
from pathlib import Path

N=13; K=6
case=int(sys.argv[1])
out=Path(sys.argv[2])

class CNF:
    def __init__(self):
        self.nv=0; self.clauses=[]; self.names={}
    def var(self,name):
        if name in self.names: return self.names[name]
        self.nv+=1; self.names[name]=self.nv; return self.nv
    def add(self,*lits):
        c=[]; seen=set()
        for l in lits:
            if l==0: continue
            if -l in seen: return
            if l not in seen: c.append(l); seen.add(l)
        self.clauses.append(c)
    def atmost(self,lits,k,prefix):
        n=len(lits)
        if k>=n: return
        if k<0: self.add(); return
        if k==0:
            for x in lits:self.add(-x)
            return
        # Sinz sequential counter: s[i,j], i=1..n-1, j=1..k
        s={(i,j):self.var((prefix,i,j)) for i in range(1,n) for j in range(1,k+1)}
        # (-x_i or s_i1), i=1..n-1
        for i in range(1,n): self.add(-lits[i-1], s[i,1])
        # monotonic first column
        for i in range(2,n): self.add(-s[i-1,1],s[i,1])
        # higher columns
        for i in range(2,n):
            for j in range(2,k+1):
                self.add(-lits[i-1],-s[i-1,j-1],s[i,j])
                self.add(-s[i-1,j],s[i,j])
        # overflow prevention, i=2..n
        for i in range(2,n+1): self.add(-lits[i-1],-s[i-1,k])
    def exactly(self,lits,k,prefix):
        self.atmost(lits,k,(prefix,'atmost'))
        self.atmost([-x for x in lits],len(lits)-k,(prefix,'atleast'))

cnf=CNF()
o={}
for i in range(N):
    for j in range(i+1,N): o[i,j]=cnf.var(('o',i,j))
l={}; r={}
for x in range(N):
    for v in range(N):
        if v!=x:
            l[x,v]=cnf.var(('l',x,v)); r[x,v]=cnf.var(('r',x,v))

def arc(u,v):
    # literal true iff u->v
    return o[u,v] if u<v else -o[v,u]

# symmetry root 0 out to 1..6 and loses to 7..12
for j in range(1,7): cnf.add(arc(0,j))
for j in range(7,13): cnf.add(-arc(0,j))
# canonical root cover size 5, p left and 5-p right
p=case; q=5-p
for v in range(1,7): cnf.add(l[0,v] if v<=p else -l[0,v])
for off,v in enumerate(range(7,13),1): cnf.add(r[0,v] if off<=q else -r[0,v])
# Also fix impossible-side vars at root explicitly through membership below.

# regularity
for x in range(N):
    lits=[arc(x,v) for v in range(N) if v!=x]
    cnf.exactly(lits,K,('deg',x))

# non-strong certificates: vertex cover size <=5 in H_x
for x in range(N):
    cover=[]
    for v in range(N):
        if v==x: continue
        cover += [l[x,v],r[x,v]]
        cnf.add(-l[x,v], arc(x,v)) # l => x->v
        cnf.add(-r[x,v], arc(v,x)) # r => v->x
    cnf.atmost(cover,5,('cover',x))
    for a in range(N):
        if a==x: continue
        for b in range(N):
            if b==x or b==a: continue
            # if x->a, b->x, a->b then l_xa or r_xb
            cnf.add(-arc(x,a),-arc(b,x),-arc(a,b),l[x,a],r[x,b])

with out.open('w') as f:
    f.write(f'c strong Seymour order-13 regular tournament counterexample, cover case p={case}\n')
    f.write(f'p cnf {cnf.nv} {len(cnf.clauses)}\n')
    for c in cnf.clauses: f.write(' '.join(map(str,c))+' 0\n')
meta={'case':case,'vars':cnf.nv,'clauses':len(cnf.clauses),'orientation_vars':78}
out.with_suffix('.json').write_text(json.dumps(meta,indent=2))
print(meta)
