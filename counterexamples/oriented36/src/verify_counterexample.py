#!/usr/bin/env python3
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
C=json.loads((ROOT/'construction/construction.json').read_text())
weights=C['cluster_weights']
out_template=[set(C['template_outneighbors'][str(i)]) for i in range(len(weights))]
clusters=[]; vertex_class=[]
for i,w in enumerate(weights):
    clusters.append(list(range(len(vertex_class),len(vertex_class)+w)))
    vertex_class.extend([i]*w)
n=len(vertex_class)
out=[set() for _ in range(n)]
for i,targets in enumerate(out_template):
    for j in targets:
        for u in clusters[i]: out[u].update(clusters[j])

def n2(x):
    r=set()
    for u in out[x]: r.update(out[u])
    return r-out[x]-{x}

def hall_defect(x):
    left=sorted(out[x]); right=n2(x)
    unions=[set() for _ in range(1<<len(left))]
    for mask in range(1,1<<len(left)):
        b=(mask & -mask).bit_length()-1
        unions[mask]=unions[mask^(1<<b)] | (out[left[b]] & right)
        if len(unions[mask])<mask.bit_count():
            return [left[i] for i in range(len(left)) if mask>>i&1],sorted(unions[mask])
    return None

def matching_size(x):
    left=sorted(out[x]); right=sorted(n2(x)); ri={v:i for i,v in enumerate(right)}
    rows=[[ri[v] for v in out[u] if v in ri] for u in left]
    match=[-1]*len(right)
    def augment(i,seen):
        for j in rows[i]:
            if j in seen: continue
            seen.add(j)
            if match[j]<0 or augment(match[j],seen):
                match[j]=i; return True
        return False
    return sum(augment(i,set()) for i in range(len(left)))

# oriented graph checks
for u in range(n):
    assert u not in out[u]
    for v in out[u]: assert u not in out[v]
rows=[''.join('1' if v in out[u] else '0' for v in range(n)) for u in range(n)]
results=[]
for x in range(n):
    d=hall_defect(x); mm=matching_size(x)
    assert d is not None and mm < len(out[x])
    results.append({'vertex':x,'class':vertex_class[x],'out_degree':len(out[x]),
                    'strict_second_neighborhood_size':len(n2(x)),
                    'maximum_matching_size':mm,'hall_S':d[0],'hall_GammaS':d[1]})
# verify advertised class witnesses exactly
for cw in C['class_hall_witnesses']:
    root=cw['root_class']; x=clusters[root][0]
    S=set().union(*(set(clusters[j]) for j in cw['S_classes']))
    G=set()
    for u in S: G |= out[u]&n2(x)
    expected=set().union(*(set(clusters[j]) for j in cw['Gamma_classes']))
    assert G==expected and len(S)==cw['S_weight'] and len(G)==cw['Gamma_weight'] and len(G)<len(S)
payload={'order':n,'arc_count':sum(map(len,out)),'minimum_out_degree':min(map(len,out)),
         'strong_vertex_count':0,'matching_sizes':[r['maximum_matching_size'] for r in results],
         'adjacency_matrix':rows,'vertices':results}
canon='\n'.join(rows)+'\n'
payload['adjacency_matrix_sha256']=hashlib.sha256(canon.encode()).hexdigest()
print(json.dumps(payload,indent=2))
