from __future__ import annotations
import sys,json
from pathlib import Path
N=13;K=6;case=int(sys.argv[1]);out=Path(sys.argv[2])
class CNF:
 def __init__(self):self.nv=0;self.c=[];self.names={}
 def var(self,n):
  if n not in self.names:self.nv+=1;self.names[n]=self.nv
  return self.names[n]
 def add(self,*xs):
  s=set(xs)
  if any(-x in s for x in s):return
  self.c.append(list(dict.fromkeys(xs)))
 def atmost(self,L,k,p):
  n=len(L)
  if k>=n:return
  if k==0:
   for x in L:self.add(-x)
   return
  S={(i,j):self.var((p,i,j)) for i in range(1,n) for j in range(1,k+1)}
  for i in range(1,n):self.add(-L[i-1],S[i,1])
  for i in range(2,n):self.add(-S[i-1,1],S[i,1])
  for i in range(2,n):
   for j in range(2,k+1):
    self.add(-L[i-1],-S[i-1,j-1],S[i,j]);self.add(-S[i-1,j],S[i,j])
  for i in range(2,n+1):self.add(-L[i-1],-S[i-1,k])
 def exactly(self,L,k,p):self.atmost(L,k,(p,0));self.atmost([-x for x in L],len(L)-k,(p,1))
cnf=CNF();o={(i,j):cnf.var(('o',i,j)) for i in range(N) for j in range(i+1,N)}
def arc(u,v):return o[u,v] if u<v else -o[v,u]
l={v:cnf.var(('l',v)) for v in range(1,N)};r={v:cnf.var(('r',v)) for v in range(1,N)}
for j in range(1,7):cnf.add(arc(0,j))
for j in range(7,13):cnf.add(-arc(0,j))
p=case;q=5-p
for v in range(1,7):cnf.add(l[v] if v<=p else -l[v])
for off,v in enumerate(range(7,13),1):cnf.add(r[v] if off<=q else -r[v])
for x in range(N):cnf.exactly([arc(x,v) for v in range(N) if v!=x],6,('deg',x))
cover=[]
for v in range(1,N):cover += [l[v],r[v]];cnf.add(-l[v],arc(0,v));cnf.add(-r[v],arc(v,0))
cnf.atmost(cover,5,('cover0',))
for a in range(1,N):
 for b in range(1,N):
  if a!=b:cnf.add(-arc(0,a),-arc(b,0),-arc(a,b),l[a],r[b])
with out.open('w') as f:
 f.write('c negative control: only root 0 must be non-strong\n');f.write(f'p cnf {cnf.nv} {len(cnf.c)}\n')
 for c in cnf.c:f.write(' '.join(map(str,c))+' 0\n')
out.with_suffix('.map.json').write_text(json.dumps({str(k):v for k,v in cnf.names.items()},indent=2))
print(cnf.nv,len(cnf.c))
