from __future__ import annotations
from itertools import combinations

MATRICES = {
    'cover_case2': [
'0111111000000','0000100110111','0100000110111','0110010111000','0011001111000','0110101011000','0111000111000','1000010001111','1000000101111','1110000000111','1001111000001','1001111000100','1001111000010'],
    'hall_case3': [
'0111111000000','0010111010001','0001111010001','0100111010001','0000000111111','0000100111101','0000110101110','1111000000011','1000001101110','1111000100010','1111000101000','1111010000100','1000001011110'],
    'hall_case4': [
'0111111000000','0010011101010','0001011101010','0100101101010','0110010101010','0001000011111','0000110010111','1000011010101','1111100000100','1000001110101','1111100000001','1000000111101','1111100010000'],
}

def parse(rows):
    A=[[int(c) for c in row] for row in rows]
    n=len(A)
    assert all(len(r)==n for r in A)
    for i in range(n):
        assert A[i][i]==0
        for j in range(i+1,n):
            assert A[i][j]+A[j][i]==1
    return A

def neighborhoods(A,x):
    n=len(A)
    out=[v for v in range(n) if A[x][v]]
    second=[]
    for z in range(n):
        if z==x or A[x][z]:
            continue
        if any(A[y][z] for y in out):
            second.append(z)
    return out,second

def max_matching(A,x):
    L,R=neighborhoods(A,x)
    mate={}
    def aug(a,seen):
        for b in R:
            if A[a][b] and b not in seen:
                seen.add(b)
                if b not in mate or aug(mate[b],seen):
                    mate[b]=a
                    return True
        return False
    size=sum(aug(a,set()) for a in L)
    return size,L,R,mate

def hall_defect(A,x):
    L,R=neighborhoods(A,x)
    best=None
    for r in range(1,len(L)+1):
        for S in combinations(L,r):
            N=tuple(b for b in R if any(A[a][b] for a in S))
            deficit=len(S)-len(N)
            if deficit>0:
                cand=(deficit,len(S),S,N)
                if best is None or cand[:2]>best[:2]:
                    best=cand
    return best

for name,rows in MATRICES.items():
    A=parse(rows)
    deg=[sum(r) for r in A]
    assert deg==[6]*13, (name,deg)
    print(f'[{name}] regular degrees: {deg}')
    strong=[]
    for x in range(13):
        m,L,R,_=max_matching(A,x)
        h=hall_defect(A,x)
        if m==len(L): strong.append(x)
        print(f'  x={x:2d}: |N+|={len(L)}, |N++|={len(R)}, max_matching={m}, hall={h}')
    print('  strong vertices:',strong)
    print()
