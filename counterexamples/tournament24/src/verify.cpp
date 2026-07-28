#include <array>
#include <cstdint>
#include <functional>
#include <iostream>
#include <numeric>
#include <sstream>
#include <string>
#include <vector>
using namespace std;
static int matching(const vector<uint32_t>& rows,int R){vector<int> mr(R,-1);function<bool(int,uint32_t&)> aug=[&](int u,uint32_t&seen){uint32_t a=rows[u]&~seen;while(a){int v=__builtin_ctz(a);a&=a-1;seen|=1u<<v;if(mr[v]<0||aug(mr[v],seen)){mr[v]=u;return true;}}return false;};int z=0;for(int u=0;u<(int)rows.size();++u){uint32_t seen=0;if(aug(u,seen))++z;}return z;}
int main(){const string code="110000101011101000010111101010010100010010010";const vector<int>w={5,1,2,2,3,1,2,5,1,2};int m=w.size(),k=0;vector<uint16_t>tout(m);for(int i=0;i<m;i++)for(int j=i+1;j<m;j++){if(code[k++]=='1')tout[i]|=1u<<j;else tout[j]|=1u<<i;}vector<int>off(m+1),cl;for(int i=0;i<m;i++){off[i+1]=off[i]+w[i];for(int r=0;r<w[i];r++)cl.push_back(i);}int n=off.back();vector<uint32_t>out(n);for(int u=0;u<n;u++)for(int j=0;j<m;j++)if((tout[cl[u]]>>j)&1)for(int v=off[j];v<off[j+1];v++)out[u]|=1u<<v;for(int i=0;i<m;i++)for(int u=off[i];u<off[i+1];u++)for(int v=u+1;v<off[i+1];v++)out[u]|=1u<<v;
for(int i=0;i<n;i++){if((out[i]>>i)&1)return 2;for(int j=i+1;j<n;j++)if(((out[i]>>j)&1)+((out[j]>>i)&1)!=1)return 3;}uint32_t all=(1u<<n)-1;for(int x=0;x<n;x++){uint32_t O=out[x],R=0,t=O;while(t){int u=__builtin_ctz(t);t&=t-1;R|=out[u];}R&=~O;R&=~(1u<<x);R&=all;vector<int>L,V;for(int u=0;u<n;u++){if((O>>u)&1)L.push_back(u);if((R>>u)&1)V.push_back(u);}vector<uint32_t>rows(L.size());for(int i=0;i<(int)L.size();i++)for(int j=0;j<(int)V.size();j++)if((out[L[i]]>>V[j])&1)rows[i]|=1u<<j;int mm=matching(rows,V.size());bool defect=false;for(uint32_t S=1;S<(1u<<L.size());S++){uint32_t G=0;for(int i=0;i<(int)L.size();i++)if((S>>i)&1)G|=rows[i];if(__builtin_popcount(S)>__builtin_popcount(G)){defect=true;break;}}if(!defect||mm==(int)L.size())return 4;cerr<<"v="<<x<<" d="<<L.size()<<" n2="<<V.size()<<" matching="<<mm<<"\n";}cout<<"order="<<n<<" strong_vertices=0 verified=true\n";return 0;}
