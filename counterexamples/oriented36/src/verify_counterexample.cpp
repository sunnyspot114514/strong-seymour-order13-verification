#include <array>
#include <bitset>
#include <cstdint>
#include <iostream>
#include <vector>
using namespace std;
int main(){
 constexpr int M=6,N=36; const array<int,M>w={11,7,3,3,3,9};
 const array<unsigned,M> tout={ (1u<<1)|(1u<<2)|(1u<<4), (1u<<3)|(1u<<4)|(1u<<5),
   (1u<<1)|(1u<<5), (1u<<0)|(1u<<2), (1u<<2)|(1u<<3)|(1u<<5), (1u<<0)|(1u<<3)};
 array<vector<int>,M> cls;array<int,N> type{};int z=0;for(int i=0;i<M;i++)for(int k=0;k<w[i];k++){cls[i].push_back(z);type[z++]=i;}
 array<uint64_t,N> out{};for(int i=0;i<M;i++)for(int j=0;j<M;j++)if(tout[i]>>j&1)for(int u:cls[i])for(int v:cls[j])out[u]|=1ULL<<v;
 for(int u=0;u<N;u++){if(out[u]>>u&1){cerr<<"loop\n";return 1;}for(int v=0;v<N;v++)if((out[u]>>v&1)&&(out[v]>>u&1)){cerr<<"2-cycle\n";return 1;}}
 vector<int> sizes;int mindeg=N;
 for(int x=0;x<N;x++){
   uint64_t L=out[x],R=0;for(int u=0;u<N;u++)if(L>>u&1)R|=out[u];R&=~L;R&=~(1ULL<<x);R&=(1ULL<<N)-1;
   vector<int> lv,rv;for(int i=0;i<N;i++){if(L>>i&1)lv.push_back(i);if(R>>i&1)rv.push_back(i);}mindeg=min(mindeg,(int)lv.size());
   int match[36];fill(begin(match),end(match),-1);int ms=0;
   auto aug=[&](auto&&self,int u,uint64_t&seen)->bool{uint64_t q=out[u]&R;while(q){int v=__builtin_ctzll(q);q&=q-1;if(seen>>v&1)continue;seen|=1ULL<<v;if(match[v]<0||self(self,match[v],seen)){match[v]=u;return true;}}return false;};
   for(int u:lv){uint64_t seen=0;if(aug(aug,u,seen))ms++;}sizes.push_back(ms);
   bool defect=false;uint64_t lim=1ULL<<lv.size();for(uint64_t sm=1;sm<lim&&!defect;sm++){uint64_t g=0;for(size_t i=0;i<lv.size();i++)if(sm>>i&1)g|=out[lv[i]]&R;if(__builtin_popcountll(g)<__builtin_popcountll(sm))defect=true;}
   if(!defect||ms==(int)lv.size()){cerr<<"vertex "<<x<<" unexpectedly strong\n";return 1;}
 }
 cout<<"VERIFIED order=36 min_out_degree="<<mindeg<<" matching_sizes=[";for(size_t i=0;i<sizes.size();i++){if(i)cout<<',';cout<<sizes[i];}cout<<"]\n";
}
