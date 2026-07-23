#include <bits/stdc++.h>
using namespace std;

struct Checker {
    int n=0;
    vector<vector<int>> clauses;
    vector<vector<int>> occ; // literal -> clause ids
    vector<int8_t> val;
    vector<int> assigned;
    vector<int> rem;
    vector<uint8_t> sat;

    static int li(int lit){ return 2*(abs(lit)-1)+(lit<0); }
    int eval(int lit) const {
        int8_t v=val[abs(lit)];
        if(v<0) return -1;
        return ((lit>0)==(v==1)) ? 1 : 0;
    }
    bool setlit(int lit){
        int v=abs(lit), x=lit>0;
        if(val[v]>=0) return val[v]==x;
        val[v]=x; assigned.push_back(lit); return true;
    }
    void reset(){ for(int l:assigned) val[abs(l)]=-1; assigned.clear(); }
    int add_clause(vector<int> c){
        sort(c.begin(),c.end());
        c.erase(unique(c.begin(),c.end()),c.end());
        for(int l:c) if(binary_search(c.begin(),c.end(),-l)) return -1;
        int id=clauses.size(); clauses.push_back(move(c));
        if((int)rem.size()<=id){ rem.push_back(0); sat.push_back(0); }
        for(int l:clauses.back()) occ[li(l)].push_back(id);
        return id;
    }
    bool rup(const vector<int>& lemma){
        reset();
        for(int l:lemma) if(!setlit(-l)) return true;
        int m=clauses.size();
        if((int)rem.size()<m){rem.resize(m);sat.resize(m);}
        deque<int> q;
        // Independent full initialization scan.
        for(int id=0;id<m;id++){
            bool s=false; int r=0,last=0;
            for(int l:clauses[id]){
                int e=eval(l);
                if(e==1){s=true;break;}
                if(e<0){r++;last=l;}
            }
            sat[id]=s; rem[id]=r;
            if(!s){
                if(r==0) return true;
                if(r==1) q.push_back(last);
            }
        }
        size_t propagated=assigned.size();
        while(true){
            while(!q.empty()){
                int l=q.front();q.pop_front();
                if(!setlit(l)) return true;
            }
            if(propagated>=assigned.size()) break;
            int p=assigned[propagated++];
            // Clauses containing p become satisfied.
            for(int id:occ[li(p)]) sat[id]=1;
            // Clauses containing -p lose one unassigned literal unless already satisfied.
            for(int id:occ[li(-p)]){
                if(sat[id]) continue;
                if(rem[id]>0) rem[id]--;
                if(rem[id]==0) return true;
                if(rem[id]==1){
                    int u=0;
                    for(int l:clauses[id]) if(eval(l)<0){u=l;break;}
                    if(!u) return true;
                    q.push_back(u);
                }
            }
        }
        return false;
    }
};

static void read_cnf(const char*fn,int &n,vector<vector<int>>&cls){
    ifstream in(fn); string line;
    while(getline(in,line)){
        if(line.empty()||line[0]=='c')continue;
        if(line[0]=='p'){stringstream ss(line);string p,cnf;int m;ss>>p>>cnf>>n>>m;cls.reserve(m);continue;}
        stringstream ss(line);vector<int>c;int x;while(ss>>x&&x)c.push_back(x);cls.push_back(move(c));
    }
}
int main(int ac,char**av){
    if(ac<3){cerr<<"cnf proof\n";return 2;}
    int n=0;vector<vector<int>>orig;read_cnf(av[1],n,orig);
    Checker C;C.n=n;C.occ.resize(2*n);C.val.assign(n+1,-1);
    for(auto &c:orig)C.add_clause(c);
    ifstream in(av[2]);string line;long long step=0;bool empty=false;
    while(getline(in,line)){
        if(line.empty()||line[0]=='c'||line[0]=='d')continue;
        stringstream ss(line);vector<int>c;int x;while(ss>>x&&x)c.push_back(x);
        step++;
        if(!C.rup(c)){cerr<<"SCAN RUP FAIL step="<<step<<" size="<<c.size()<<"\n";return 1;}
        C.add_clause(c);
        if(c.empty()){empty=true;break;}
    }
    cerr<<"SCAN RUP VERIFIED steps="<<step<<" empty="<<empty<<" clauses="<<C.clauses.size()<<"\n";
    return empty?0:1;
}
