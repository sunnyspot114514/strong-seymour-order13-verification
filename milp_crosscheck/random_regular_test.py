from __future__ import annotations
import random
import numpy as np

N=13; K=6

def cyclic_tournament(n=13):
    k=(n-1)//2
    A=np.zeros((n,n),dtype=np.uint8)
    for i in range(n):
        for d in range(1,k+1):
            A[i,(i+d)%n]=1
    return A

def max_matching_size(A, x):
    outs=[v for v in range(N) if A[x,v]]
    second=[]
    for z in range(N):
        if z==x or A[x,z]: continue
        if any(A[y,z] for y in outs): second.append(z)
    match={}
    def dfs(a,seen):
        for b in second:
            if A[a,b] and b not in seen:
                seen.add(b)
                if b not in match or dfs(match[b],seen):
                    match[b]=a; return True
        return False
    return sum(dfs(a,set()) for a in outs), len(outs), len(second)

def cycle_flip(A, tries=100):
    for _ in range(tries):
        a,b,c=random.sample(range(N),3)
        if A[a,b] and A[b,c] and A[c,a]:
            B=A.copy()
            for u,v in [(a,b),(b,c),(c,a)]:
                B[u,v]=0;B[v,u]=1
            return B
        if A[b,a] and A[c,b] and A[a,c]:
            B=A.copy()
            for u,v in [(b,a),(c,b),(a,c)]:
                B[u,v]=0;B[v,u]=1
            return B
    return A

A=cyclic_tournament()
print('cyclic degrees',A.sum(1).tolist())
print('cyclic matching', [max_matching_size(A,x) for x in range(N)])
mins=K
non=[]
seen=set()
for t in range(200000):
    A=cycle_flip(A)
    if t%10==0:
        vals=[max_matching_size(A,x)[0] for x in range(N)]
        m=min(vals)
        mins=min(mins,m)
        if m<K:
            non.append((t,vals,A.copy()))
            print('FOUND nonstrong',t,vals)
            break
print('minimum matching observed',mins,'nonstrong count',len(non))
if non:
    _,vals,A=non[0]
    for row in A: print(''.join(map(str,row.tolist())))
