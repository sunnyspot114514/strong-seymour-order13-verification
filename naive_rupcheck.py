from __future__ import annotations
import sys,time

def read_cnf(path):
 n=0; clauses=[]
 for line in open(path):
  if not line.strip() or line[0]=='c':continue
  if line[0]=='p':n=int(line.split()[2]);continue
  clauses.append(tuple(map(int,line.split()[:-1])))
 return n,clauses

def proof_steps(path):
 for line in open(path):
  line=line.strip()
  if not line or line[0] in 'cd':continue
  yield tuple(map(int,line.split()[:-1]))

def rup(clauses,c,n):
 # Deliberately simple full-scan unit propagation, independent of watched-literal checker.
 a=[-1]*(n+1)
 for lit in c:
  lit=-lit;v=abs(lit);want=1 if lit>0 else 0
  if a[v]!=-1 and a[v]!=want:return True
  a[v]=want
 changed=True
 while changed:
  changed=False
  for cl in clauses:
   sat=False; last=0; un=0
   for lit in cl:
    z=a[abs(lit)]
    if z==-1:un+=1;last=lit
    elif (z==1)==(lit>0):sat=True;break
   if sat:continue
   if un==0:return True
   if un==1:
    v=abs(last);want=1 if last>0 else 0
    if a[v]!=-1:
     if a[v]!=want:return True
    else:a[v]=want;changed=True
 return False

def main(cnf,pf):
 n,F=read_cnf(cnf); t=time.time();k=0
 for c in proof_steps(pf):
  k+=1
  if not rup(F,c,n):raise SystemExit(f'FAIL at {k} size={len(c)}')
  F.append(c)
  if not c:
   print(f'NAIVE RUP VERIFIED steps={k} clauses={len(F)} sec={time.time()-t:.3f}')
   return
 raise SystemExit('no empty clause')
if __name__=='__main__':main(sys.argv[1],sys.argv[2])
