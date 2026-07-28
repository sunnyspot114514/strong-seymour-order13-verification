#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
CODE = "110000101011101000010111101010010100010010010"
WEIGHTS = [5,1,2,2,3,1,2,5,1,2]

def construct():
    m=len(WEIGHTS); tout=[0]*m; k=0
    for i in range(m):
        for j in range(i+1,m):
            if CODE[k]=='1': tout[i]|=1<<j
            else: tout[j]|=1<<i
            k+=1
    off=[0]
    for w in WEIGHTS: off.append(off[-1]+w)
    cls=[]
    for i,w in enumerate(WEIGHTS): cls += [i]*w
    n=off[-1]; out=[0]*n
    for u in range(n):
        for j in range(m):
            if (tout[cls[u]]>>j)&1:
                for v in range(off[j],off[j+1]): out[u]|=1<<v
    # transitive orientation inside each class
    for i in range(m):
        for u in range(off[i],off[i+1]):
            for v in range(u+1,off[i+1]): out[u]|=1<<v
    return out,off,cls

def max_matching(rows,R):
    mr=[-1]*R
    def aug(u,seen):
        for v in range(R):
            if (rows[u]>>v)&1 and v not in seen:
                seen.add(v)
                if mr[v]<0 or aug(mr[v],seen):
                    mr[v]=u; return True
        return False
    return sum(aug(u,set()) for u in range(len(rows)))

def main():
    out,off,cls=construct(); n=len(out); allm=(1<<n)-1
    for i in range(n):
        assert not ((out[i]>>i)&1)
        for j in range(i+1,n):
            assert ((out[i]>>j)&1)+((out[j]>>i)&1)==1
    result=[]; strong=0
    for x in range(n):
        O=out[x]; R=0
        for u in range(n):
            if (O>>u)&1: R|=out[u]
        R&=~O; R&=~(1<<x); R&=allm
        L=[u for u in range(n) if (O>>u)&1]
        V=[v for v in range(n) if (R>>v)&1]
        rows=[]
        for u in L:
            b=0
            for j,v in enumerate(V):
                if (out[u]>>v)&1: b|=1<<j
            rows.append(b)
        mm=max_matching(rows,len(V))
        hall=None
        for S in range(1,1<<len(L)):
            G=0
            for i in range(len(L)):
                if (S>>i)&1: G|=rows[i]
            if S.bit_count()>G.bit_count():
                hall=([L[i] for i in range(len(L)) if (S>>i)&1],
                      [V[j] for j in range(len(V)) if (G>>j)&1])
                break
        assert hall is not None and mm<len(L)
        strong += mm==len(L)
        result.append({'vertex':x,'class':cls[x],'outdegree':len(L),
                       'strict_second':len(V),'matching':mm,
                       'hall_S':hall[0],'hall_Gamma':hall[1]})
    matrix='\n'.join(''.join('1' if (out[i]>>j)&1 else '0' for j in range(n)) for i in range(n))+'\n'
    digest=hashlib.sha256(matrix.encode()).hexdigest()
    assert strong==0
    print(json.dumps({'order':n,'strong_vertices':strong,'matrix_sha256':digest,
                      'all_vertices_have_hall_defects':True,'vertices':result},indent=2))
if __name__=='__main__': main()
