from __future__ import annotations
import sys, json
from pathlib import Path

N=13; K=6
if len(sys.argv) != 4:
    raise SystemExit('usage: generate_extremal_cnf.py MIN_FAILURES P OUT.cnf')
min_fail=int(sys.argv[1]); p=int(sys.argv[2]); out=Path(sys.argv[3])
if not (1 <= min_fail <= N): raise SystemExit('MIN_FAILURES must be 1..13')
if not (0 <= p <= 5): raise SystemExit('P must be 0..5')

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
        # Sinz sequential counter
        s={(i,j):self.var((prefix,i,j)) for i in range(1,n) for j in range(1,k+1)}
        for i in range(1,n): self.add(-lits[i-1], s[i,1])
        for i in range(2,n): self.add(-s[i-1,1],s[i,1])
        for i in range(2,n):
            for j in range(2,k+1):
                self.add(-lits[i-1],-s[i-1,j-1],s[i,j])
                self.add(-s[i-1,j],s[i,j])
        for i in range(2,n+1): self.add(-lits[i-1],-s[i-1,k])
    def atleast(self,lits,k,prefix):
        self.atmost([-x for x in lits],len(lits)-k,prefix)
    def exactly(self,lits,k,prefix):
        self.atmost(lits,k,(prefix,'atmost'))
        self.atleast(lits,k,(prefix,'atleast'))

cnf=CNF()
o={(i,j):cnf.var(('o',i,j)) for i in range(N) for j in range(i+1,N)}
f={x:cnf.var(('fail',x)) for x in range(N)}
l={}; r={}
for x in range(N):
    for v in range(N):
        if v!=x:
            l[x,v]=cnf.var(('l',x,v)); r[x,v]=cnf.var(('r',x,v))

def arc(u,v):
    return o[u,v] if u<v else -o[v,u]

# Choose one failing vertex as root 0. Relabel its six out-neighbours 1..6.
cnf.add(f[0])
for j in range(1,7): cnf.add(arc(0,j))
for j in range(7,13): cnf.add(-arc(0,j))

# Normalize one padded size-five vertex-cover certificate for root 0.
q=5-p
for v in range(1,7): cnf.add(l[0,v] if v<=p else -l[0,v])
for off,v in enumerate(range(7,13),1): cnf.add(r[0,v] if off<=q else -r[0,v])

# 6-regular tournament.
for x in range(N):
    cnf.exactly([arc(x,v) for v in range(N) if v!=x],K,('deg',x))

# Optional non-strong certificates. If fail[x] is true, l/r form a vertex cover
# of size <=5 for the 6x6 matching graph H_x.
for x in range(N):
    cover=[]
    for v in range(N):
        if v==x: continue
        cover += [l[x,v],r[x,v]]
        cnf.add(-l[x,v], arc(x,v))
        cnf.add(-r[x,v], arc(v,x))
    cnf.atmost(cover,5,('cover',x))
    for a in range(N):
        if a==x: continue
        for b in range(N):
            if b==x or b==a: continue
            # fail[x] and x->a and b->x and a->b => l[x,a] or r[x,b]
            cnf.add(-f[x],-arc(x,a),-arc(b,x),-arc(a,b),l[x,a],r[x,b])

# At least min_fail vertices carry valid failure certificates.
cnf.atleast([f[x] for x in range(N)],min_fail,('min_fail',min_fail))

with out.open('w') as fp:
    fp.write(f'c 13-vertex regular tournament with at least {min_fail} non-strong vertices; root cover p={p}\n')
    fp.write(f'p cnf {cnf.nv} {len(cnf.clauses)}\n')
    for c in cnf.clauses: fp.write(' '.join(map(str,c))+' 0\n')
meta={
    'min_failures':min_fail,'root_cover_left_count':p,
    'vars':cnf.nv,'clauses':len(cnf.clauses),
    'orientation_vars':78,'failure_vars':[f[x] for x in range(N)],
}
out.with_suffix('.json').write_text(json.dumps(meta,indent=2))
print(json.dumps(meta))
