from __future__ import annotations
import sys

cnf=sys.argv[1] if len(sys.argv)>1 else 'control3.cnf'
model=sys.argv[2] if len(sys.argv)>2 else 'control3.model'
vals={}
for tok in open(model,encoding='utf-8').read().split():
    if tok in ('v','0'): continue
    z=int(tok); vals[abs(z)]=z>0

bad=[]
for no,line in enumerate(open(cnf,encoding='utf-8'),1):
    if not line.strip() or line.startswith(('c','p')): continue
    c=[int(x) for x in line.split()[:-1]]
    if not any(vals.get(abs(l),False)==(l>0) for l in c): bad.append(no)
print('CNF bad clauses',bad[:10],'count',len(bad))
if bad: raise SystemExit(1)

N=13
adj=[[0]*N for _ in range(N)]; vid=0
for i in range(N):
    for j in range(i+1,N):
        vid+=1; z=vals[vid]
        adj[i][j]=int(z); adj[j][i]=1-int(z)
deg=[sum(r) for r in adj]
print('degrees',deg)
if deg != [6]*N: raise SystemExit('not regular')
print('adjacency matrix')
for row in adj: print(''.join(map(str,row)))

def second(x:int)->list[int]:
    A={v for v in range(N) if adj[x][v]}
    return sorted(z for z in range(N) if z!=x and z not in A and any(adj[y][z] for y in A))

def max_matching(x:int):
    A=[v for v in range(N) if adj[x][v]]
    B=second(x)
    mate={}
    def aug(a,seen):
        for b in B:
            if not adj[a][b] or b in seen: continue
            seen.add(b)
            if b not in mate or aug(mate[b],seen):
                mate[b]=a; return True
        return False
    size=sum(aug(a,set()) for a in A)
    return size,A,B

sizes=[]
for x in range(N):
    size,A,B=max_matching(x); sizes.append(size)
    print('x',x,'matching',size,'Nplus',A,'Nplusplus',B)
print('matching sizes',sizes)
if all(s==6 for s in sizes): raise SystemExit('control unexpectedly has no failing vertex')
