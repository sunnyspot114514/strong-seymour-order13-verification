#include <bits/stdc++.h>
using namespace std;
struct Clause{vector<int> l;};
struct Checker{
 int n; vector<Clause> cs; vector<vector<int>> w; vector<int8_t> val; vector<int> trail, units; size_t qhead;
 static int idx(int l){return 2*(abs(l)-1)+(l<0);} int lv(int l){auto a=val[abs(l)]; if(a<0)return -1; return ((l>0)==(a==1));}
 bool enq(int l){int v=abs(l),x=l>0; if(val[v]>=0)return val[v]==x;val[v]=x;trail.push_back(l);return true;}
 int add(vector<int> c){sort(c.begin(),c.end(),[](int a,int b){return abs(a)==abs(b)?a<b:abs(a)<abs(b);});vector<int>u;for(int x:c){if(!u.empty()&&u.back()==x)continue;if(!u.empty()&&u.back()==-x)return -2;u.push_back(x);}int id=cs.size();cs.push_back({u});if(u.size()>=2){w[idx(u[0])].push_back(id);w[idx(u[1])].push_back(id);}else if(u.size()==1){w[idx(u[0])].push_back(id);units.push_back(id);}return id;}
 int prop(){while(qhead<trail.size()){int p=trail[qhead++],fl=-p,wi=idx(fl);vector<int>cur;cur.swap(w[wi]);for(size_t ii=0;ii<cur.size();ii++){int id=cur[ii];auto &c=cs[id].l;if(c.size()==1){w[wi].push_back(id);if(lv(c[0])==0){for(size_t j=ii+1;j<cur.size();j++)w[wi].push_back(cur[j]);return id;}continue;}if(c[0]!=fl){if(c[1]==fl)swap(c[0],c[1]);else{w[wi].push_back(id);continue;}}int oth=c[1];if(lv(oth)==1){w[wi].push_back(id);continue;}bool moved=false;for(size_t k=2;k<c.size();k++)if(lv(c[k])!=0){int nl=c[k];c[k]=c[0];c[0]=nl;w[idx(nl)].push_back(id);moved=true;break;}if(moved)continue;w[wi].push_back(id);if(lv(oth)==0){for(size_t j=ii+1;j<cur.size();j++)w[wi].push_back(cur[j]);return id;}if(!enq(oth)){for(size_t j=ii+1;j<cur.size();j++)w[wi].push_back(cur[j]);return id;}}
 }return -1;}
 void reset(){for(int l:trail)val[abs(l)]=-1;trail.clear();qhead=0;}
 bool rup(const vector<int>&c){reset();for(int id:units)if(!enq(cs[id].l[0]))return true;for(int l:c)if(!enq(-l))return true;return prop()>=0;}
};
static void read_cnf(const char*fn,int &n,vector<vector<int>>&cls){ifstream in(fn);string line;while(getline(in,line)){if(line.empty()||line[0]=='c')continue;if(line[0]=='p'){stringstream ss(line);string p,cnf;int m;ss>>p>>cnf>>n>>m;cls.reserve(m);continue;}stringstream ss(line);vector<int>c;int x;while(ss>>x&&x)c.push_back(x);cls.push_back(c);}}
int main(int ac,char**av){if(ac<3){cerr<<"cnf proof\n";return 2;}int n=0;vector<vector<int>> orig;read_cnf(av[1],n,orig);Checker C;C.n=n;C.w.resize(2*n);C.val.assign(n+1,-1);for(auto &c:orig)C.add(c);ifstream p(av[2]);string line;long long k=0;bool gotempty=false;while(getline(p,line)){if(line.empty()||line[0]=='c'||line[0]=='d')continue;stringstream ss(line);vector<int>c;int x;while(ss>>x&&x)c.push_back(x);k++;if(!C.rup(c)){cerr<<"RUP FAIL step "<<k<<" size "<<c.size()<<"\n";return 1;}C.add(c);if(c.empty()){gotempty=true;break;}}cerr<<"RUP VERIFIED steps="<<k<<" empty="<<gotempty<<" clauses="<<C.cs.size()<<"\n";return gotempty?0:1;}
