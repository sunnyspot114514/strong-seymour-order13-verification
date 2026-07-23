#include <bits/stdc++.h>
using namespace std;
struct Clause { vector<int> l; bool learnt=false; };
struct Solver {
 int n=0; vector<Clause> cs; vector<vector<int>> watches;
 vector<int8_t> val; vector<int> lev, reason, trail, trail_lim; size_t qhead=0;
 vector<double> act; double inc=1.0, decay=0.95; vector<int8_t> phase;
 long long conflicts=0, decisions=0, propagations=0; ofstream proof;
 static int lidx(int lit){ int v=abs(lit)-1; return 2*v+(lit<0); }
 int litval(int lit) const { int8_t a=val[abs(lit)]; if(a<0) return -1; bool t=(a==1); return ((lit>0)==t)?1:0; }
 int dl() const { return (int)trail_lim.size(); }
 bool enqueue(int lit,int rsn){ int v=abs(lit), want=lit>0?1:0; if(val[v]>=0) return val[v]==want; val[v]=want; lev[v]=dl(); reason[v]=rsn; phase[v]=want; trail.push_back(lit); return true; }
 int addClause(vector<int> l,bool learnt=false){
   sort(l.begin(),l.end(),[](int a,int b){return abs(a)==abs(b)?a<b:abs(a)<abs(b);});
   vector<int> u; for(int x:l){ if(!u.empty() && u.back()==x) continue; if(!u.empty() && u.back()==-x) return -2; u.push_back(x);} l.swap(u);
   int id=cs.size(); cs.push_back({l,learnt});
   if(l.size()>=2){ watches[lidx(l[0])].push_back(id); watches[lidx(l[1])].push_back(id); }
   else if(l.size()==1){ watches[lidx(l[0])].push_back(id); }
   return id;
 }
 int propagate(){
   while(qhead<trail.size()){
     int p=trail[qhead++]; propagations++;
     int fl=-p, wi=lidx(fl);
     vector<int> cur; cur.swap(watches[wi]);
     for(size_t ii=0;ii<cur.size();++ii){
       int cid=cur[ii]; Clause &c=cs[cid];
       if(c.l.size()==1){ watches[wi].push_back(cid); if(litval(c.l[0])==0){ for(size_t j=ii+1;j<cur.size();++j) watches[wi].push_back(cur[j]); return cid;} continue; }
       if(c.l[0]!=fl){ if(c.l[1]==fl) swap(c.l[0],c.l[1]); else { // stale, keep conservatively
           watches[wi].push_back(cid); continue; } }
       int other=c.l[1];
       if(litval(other)==1){ watches[wi].push_back(cid); continue; }
       bool moved=false;
       for(size_t k=2;k<c.l.size();++k){ if(litval(c.l[k])!=0){ int nl=c.l[k]; c.l[k]=c.l[0]; c.l[0]=nl; watches[lidx(nl)].push_back(cid); moved=true; break; } }
       if(moved) continue;
       watches[wi].push_back(cid);
       int ov=litval(other);
       if(ov==0){ for(size_t j=ii+1;j<cur.size();++j) watches[wi].push_back(cur[j]); return cid; }
       if(!enqueue(other,cid)){ for(size_t j=ii+1;j<cur.size();++j) watches[wi].push_back(cur[j]); return cid; }
     }
   }
   return -1;
 }
 void cancelUntil(int lvl){ if(dl()<=lvl) return; int target=trail_lim[lvl]; for(int i=trail.size()-1;i>=target;--i){int v=abs(trail[i]); val[v]=-1; reason[v]=-1; lev[v]=0;} trail.resize(target); trail_lim.resize(lvl); qhead=trail.size(); }
 pair<vector<int>,int> analyze(int confl){
   vector<int> out(1,0); vector<char> seen(n+1,0); int path=0,p=0,idx=(int)trail.size()-1; int cid=confl;
   do{
     Clause &c=cs[cid];
     for(int q:c.l){ int v=abs(q); if(v==abs(p)) continue; if(!seen[v] && lev[v]>0){ seen[v]=1; act[v]+=inc; if(lev[v]==dl()) path++; else out.push_back(q);} }
     while(idx>=0 && !seen[abs(trail[idx])]) idx--;
     if(idx<0){ cerr<<"analysis failed\n"; exit(3);} p=trail[idx--]; int pv=abs(p); cid=reason[pv]; seen[pv]=0; path--;
     if(path>0 && cid<0){ cerr<<"decision before UIP path="<<path<<"\n"; exit(4);}
   }while(path>0);
   out[0]=-p;
   int back=0, best=1; for(int i=1;i<(int)out.size();++i){ if(lev[abs(out[i])]>back){back=lev[abs(out[i])];best=i;} }
   if(out.size()>1) swap(out[1],out[best]);
   inc/=decay; if(inc>1e100){ for(int v=1;v<=n;v++) act[v]*=1e-100; inc*=1e-100; }
   return {out,back};
 }
 int pick(){ int b=0; double ba=-1; for(int v=1;v<=n;v++) if(val[v]<0 && act[v]>ba){ba=act[v];b=v;} return b; }
 bool solve(){
   // enqueue original units
   for(int i=0;i<(int)cs.size();++i){
     if(cs[i].l.empty()){ proof<<"0\n"; proof.flush(); return false; }
     if(cs[i].l.size()==1 && !enqueue(cs[i].l[0],i)){ proof<<"0\n"; proof.flush(); return false; }
   }
   int confl=propagate(); if(confl>=0){ proof<<"0\n"; proof.flush(); return false; }
   long long restart_lim=100, since_restart=0;
   while(true){
     confl=propagate();
     if(confl>=0){ conflicts++; since_restart++; if(dl()==0){ proof<<"0\n"; return false; }
       auto [learnt,back]=analyze(confl); cancelUntil(back); int id=addClause(learnt,true); if(id<0){cerr<<"bad learnt\n";exit(5);} for(int x:learnt) proof<<x<<' '; proof<<"0\n"; if(!enqueue(learnt[0],id)){cerr<<"enqueue learned fail\n";exit(6);}
       if(since_restart>=restart_lim){ cancelUntil(0); since_restart=0; restart_lim=min<long long>(restart_lim*3/2,5000); }
     }else{
       int v=pick(); if(!v) return true; decisions++; trail_lim.push_back(trail.size()); int lit=phase[v]==1?v:-v; if(!enqueue(lit,-1)){cerr<<"decision fail\n";exit(7);}
     }
     if((conflicts%10000)==0 && conflicts>0) cerr<<"conf="<<conflicts<<" dec="<<decisions<<" clauses="<<cs.size()<<" dl="<<dl()<<"\n";
   }
 }
};
int main(int argc,char**argv){ if(argc<3){cerr<<"usage cnf proof\n";return 2;} ifstream in(argv[1]); string tok; int n,m; vector<vector<int>> cls;
 while(in>>tok){ if(tok=="c"){string s;getline(in,s);continue;} if(tok=="p"){string cnf;in>>cnf>>n>>m;break;} }
 cls.reserve(m); for(int i=0;i<m;i++){vector<int> c;int x;while(in>>x && x)c.push_back(x);cls.push_back(move(c));}
 Solver S;S.n=n;S.watches.resize(2*n);S.val.assign(n+1,-1);S.lev.assign(n+1,0);S.reason.assign(n+1,-1);S.act.assign(n+1,0);S.phase.assign(n+1,0);S.proof.open(argv[2]);
 for(auto &c:cls){ for(int x:c)S.act[abs(x)]+=1.0; int id=S.addClause(c,false); if(id==-2){} }
 auto st=chrono::steady_clock::now(); bool sat=S.solve(); double sec=chrono::duration<double>(chrono::steady_clock::now()-st).count();
 cerr<<(sat?"SAT":"UNSAT")<<" conflicts="<<S.conflicts<<" decisions="<<S.decisions<<" props="<<S.propagations<<" sec="<<sec<<"\n";
 if(sat && argc>=4){ ofstream mf(argv[3]); mf<<"v "; for(int v=1;v<=S.n;v++) mf<<(S.val[v]==1?v:-v)<<" "; mf<<"0\n"; }
 return sat?10:20; }
