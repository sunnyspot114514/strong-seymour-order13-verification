from __future__ import annotations
import sys,json,itertools,hashlib
from pathlib import Path
if len(sys.argv)<3: raise SystemExit('usage: instance.cnf model [out.json]')
cnf=Path(sys.argv[1]); model=Path(sys.argv[2]); out=Path(sys.argv[3]) if len(sys.argv)>3 else None
vals={}
for tok in model.read_text().split():
    if tok in ('v','0'):continue
    z=int(tok);vals[abs(z)]=z>0
# CNF check
bad=[]
for no,line in enumerate(cnf.read_text().splitlines(),1):
    if not line or line[0] in 'cp':continue
    C=[int(x) for x in line.split()[:-1]]
    if not any(vals.get(abs(l),False)==(l>0) for l in C):bad.append(no)
if bad:raise SystemExit(f'bad clauses {bad[:10]} total={len(bad)}')
N=13;adj=[[0]*N for _ in range(N)];v=0
for i in range(N):
    for j in range(i+1,N):
        v+=1;z=vals[v];adj[i][j]=int(z);adj[j][i]=1-int(z)
if [sum(r) for r in adj] != [6]*N:raise SystemExit('not regular')

def match(x):
    A=[a for a in range(N) if adj[x][a]]
    B=[b for b in range(N) if b!=x and not adj[x][b]]
    mate={}
    def aug(a,seen):
        for b in B:
            if not adj[a][b] or b in seen:continue
            seen.add(b)
            if b not in mate or aug(mate[b],seen):mate[b]=a;return True
        return False
    size=sum(aug(a,set()) for a in A)
    pairs=sorted((a,b) for b,a in mate.items())
    return size,A,B,pairs

def hall_witness(x,A,B):
    for r in range(1,len(A)+1):
        for S in itertools.combinations(A,r):
            G=sorted(b for b in B if any(adj[a][b] for a in S))
            if len(G)<len(S):return list(S),G
    return None
records=[]
for x in range(N):
    size,A,B,pairs=match(x);rec={'vertex':x,'matching_size':size,'Nplus':A,'Nminus':B}
    if size==6:rec['perfect_matching']=pairs
    else:
        S,G=hall_witness(x,A,B);rec['hall_defect']={'S':S,'GammaS':G,'size_S':len(S),'size_GammaS':len(G)}
    records.append(rec)
mat=[''.join(map(str,r)) for r in adj];raw='\n'.join(mat)+'\n'
result={'order':13,'degrees':[sum(r) for r in adj],'adjacency_matrix':mat,'matrix_sha256':hashlib.sha256(raw.encode()).hexdigest(),'strong_vertices':[r['vertex'] for r in records if r['matching_size']==6],'non_strong_vertices':[r['vertex'] for r in records if r['matching_size']<6],'strong_count':sum(r['matching_size']==6 for r in records),'non_strong_count':sum(r['matching_size']<6 for r in records),'vertices':records}
text=json.dumps(result,indent=2);print(text)
if out:out.write_text(text)
