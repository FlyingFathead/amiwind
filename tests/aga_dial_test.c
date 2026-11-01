/* SPDX-License-Identifier: GPL-2.0-or-later
 * The dialogue table (engine/aga/src/aw_dial.c, DIALOGUE-57) with the shared condition evaluator (aw_glut.c),
 * compiled natively (tests/test_dialogue_lut.py) on the builder's own files:
 *   aga_dial_test DIALOGUE.LUT NPC-VOICES.LUT EXPECTATIONS
 * tab-separated lines:
 *   row ID NPC TOPIC,..|-                     the voice table's row of ID is NPC; its dialogue row lists these topics
 *   answer ID TOPIC DISP CHOICE RANDOM ENTRY TEXT SCRIPT LINKS   the answer (Info Refusal rule applied), its text,
 *                                                                 its script ('|' for line ends) and its links
 * The conversation is read through a read function over the file in memory, the engine's way (no other access). */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "aw_dial.h"

static unsigned char *slurp(const char *path,long *size) {
    FILE *f=fopen(path,"rb");unsigned char *d;
    assert(f);fseek(f,0,SEEK_END);*size=ftell(f);fseek(f,0,SEEK_SET);
    d=(unsigned char *)malloc((size_t)*size);assert(d);
    assert((long)fread(d,1,(size_t)*size,f)==*size);fclose(f);
    return d;
}
typedef struct {const unsigned char *data;long size;long reads;} file_t;
static int read_mem(void *user,long offset,void *out,long bytes) {
    file_t *f=(file_t *)user;
    if(offset<0 || bytes<0 || offset+bytes>f->size)return 0;
    memcpy(out,f->data+offset,(size_t)bytes);f->reads++;
    return 1;
}
static void string_at(const file_t *f,long offset,char *out,int capacity) {
    int n=0;
    if(offset<0){strcpy(out,"-");return;}
    while(offset+n<f->size && f->data[offset+n] && n<capacity-1){out[n]=f->data[offset+n]=='\n'?'|':(char)f->data[offset+n];n++;}
    out[n]=0;
}

/* the live state stubs (aw_glut_live): name -> value tables filled by "set" lines */
#define LIVE_ROWS 32
static struct {char kind[8],name[64];long value;} live_rows[LIVE_ROWS];static int live_count;
static int same(const char *a,const char *b){for(;*a && *b;a++,b++)if((*a|32)!=(*b|32))return 0;return *a==*b;}
static int live_find(const char *kind,const char *name,long *out){
    int i;*out=0;
    for(i=0;i<live_count;i++)if(!strcmp(live_rows[i].kind,kind) && same(live_rows[i].name,name)){*out=live_rows[i].value;break;}
    return 1;
}
static int lj(const char *n,long *o){return live_find("journal",n,o);}
static int ld(const char *n,long *o){return live_find("dead",n,o);}
static int li(const char *n,long *o){return live_find("item",n,o);}
static int lr(const char *n,long *o){int i;for(i=0;i<live_count;i++)if(!strcmp(live_rows[i].kind,"rank") && same(live_rows[i].name,n)){*o=live_rows[i].value;return 1;}*o=-1;return 1;}
static int lg(const char *n,float *o){long v;int i;for(i=0;i<live_count;i++)if(!strcmp(live_rows[i].kind,"global") && same(live_rows[i].name,n)){live_find("global",n,&v);*o=(float)v;return 1;}return 0;}
static int lf(const aw_glut_cond_t *c,unsigned fn,long *o){(void)c;(void)fn;(void)o;return 0;}
static int ll(const aw_glut_cond_t *c,int slot,int is_float,float *o){char n[16];long v;(void)c;(void)is_float;sprintf(n,"%d",slot);live_find("local",n,&v);*o=(float)v;return 1;}
static const aw_glut_live_t stub_live={lj,ld,li,lr,lg,lf,ll};
/* the player's ranks of a "disp" line: faction:rank:expelled,... */
static unsigned char known_rows[64];      /* topicmap: the script topic rows known */
static int row_known(int row){return row>=0 && row<64 && known_rows[row];}
static char disp_ranks[512];
static int disp_rank(const char *faction,int *expelled){
    const char *p=disp_ranks;size_t n=strlen(faction);
    while(*p){
        if(!strncmp(p,faction,n) && p[n]==':'){int r=atoi(p+n+1);const char *e=strchr(p+n+1,':');*expelled=e?atoi(e+1):0;return r;}
        p=strchr(p,',');if(!p)break;p++;
    }
    *expelled=0;return -1;
}

int main(int argc,char **argv) {
    long size,vsize,resident;unsigned char *data,*voices;aw_dial_t d;aw_glut_t g;file_t file;char line[4096];
    FILE *x;int checks=0,opened=-1;static unsigned char buffer[131072];aw_dial_conv_t conv;
    if(argc==3 && !strcmp(argv[1],"--refusal")){
        /* a table of another format: the reason, and the reader opens nothing (it never reads past the end) */
        int version;const char *why;aw_dial_t bad;long r;
        data=slurp(argv[2],&size);
        why=AW_DialRefusal(data,size,&version);r=AW_DialResidentSize(data,size);
        printf("refusal version %d wanted %d: %s\n",version,AW_DIAL_VERSION,*why?why:"none");
        if(r>0 && r<=size && AW_DialOpen(&bad,data,r,size)){printf("opened\n");free(data);return 1;}
        free(data);
        printf("refused\n");return 0;
    }
    assert(argc==4);
    data=slurp(argv[1],&size);voices=slurp(argv[2],&vsize);
    file.data=data;file.size=size;file.reads=0;
    resident=AW_DialResidentSize(data,size);
    assert(resident>AW_DIAL_HEADER && resident<size);
    assert(AW_DialOpen(&d,data,resident,size));
    /* a short resident part, or one that does not add up to the file, is refused */
    {aw_dial_t bad;assert(!AW_DialOpen(&bad,data,resident-4,size));assert(!AW_DialOpen(&bad,data,resident,size+4));}
    {long vr=AW_GlutResidentSize(voices,vsize);assert(vr>0 && AW_GlutOpen(&g,voices,vr,vsize));}
    assert(d.npcs==g.npcs);
    x=fopen(argv[3],"r");assert(x);
    while(fgets(line,sizeof(line),x)){
        char *f[16];int n=0;char *p=strtok(line,"\t\n");
        while(p && n<16){f[n++]=p;p=strtok(NULL,"\t\n");}
        if(!n)continue;
        if(!strcmp(f[0],"row")){
            int npc=AW_GlutFind(&g,f[1]),k;char got[2048];aw_glut_cond_t speaker;
            assert(n==4);
            if(npc!=atoi(f[2])){fprintf(stderr,"row %s: %d, want %s\n",f[1],npc,f[2]);return 1;}
            AW_GlutCondOf(&g,npc,&speaker);
            if(!AW_DialConverse(&conv,&d,npc,&speaker,read_mem,&file,buffer,sizeof(buffer))){fprintf(stderr,"converse %s failed\n",f[1]);return 1;}
            opened=npc;
            got[0]=0;
            for(k=0;k<conv.topics;k++)sprintf(got+strlen(got),"%s%d",k?",":"",conv.topic[k].topic);
            if(!conv.topics)strcpy(got,"-");
            if(strcmp(got,f[3])){fprintf(stderr,"row %s topics %s, want %s\n",f[1],got,f[3]);return 1;}
            /* a buffer too small for the conversation is refused, never overrun */
            {static unsigned char small[64];aw_dial_conv_t c2;
             if(conv.answers>0)assert(!AW_DialConverse(&c2,&d,npc,&speaker,read_mem,&file,small,sizeof(small)));}
        }else if(!strcmp(f[0],"answer")){
            aw_glut_state_t s;int got,npc=AW_GlutFind(&g,f[1]),entry;char text[2048],script[2048],links[512];
            unsigned short l[64];int nl,k;aw_dial_span_t sp[64];char spans[1024];
            assert(n==11 && npc==opened);
            memset(&s,0,sizeof(s));
            s.random100=atoi(f[5]);s.speaker_health_percent=s.player_health_percent=s.player_health=100;
            conv.cond.disposition=atoi(f[3]);conv.cond.choice=atoi(f[4]);
            got=AW_DialAnswer(&conv,atoi(f[2]),&s);
            entry=got<0?-1:(int)conv.answer[got].entry;
            if(entry!=atoi(f[6])){fprintf(stderr,"answer %s topic %s disp %s choice %s r %s: %d, want %s\n",f[1],f[2],f[3],f[4],f[5],entry,f[6]);return 1;}
            string_at(&file,AW_DialTextAt(&conv,got),text,sizeof(text));
            string_at(&file,AW_DialScriptAt(&conv,got),script,sizeof(script));
            if(strcmp(text,f[7]) || strcmp(script,f[8])){fprintf(stderr,"answer %s topic %s: text '%s' script '%s'\n",f[1],f[2],text,script);return 1;}
            nl=AW_DialLinks(&conv,got,read_mem,&file,l,64);links[0]=0;
            for(k=0;k<nl;k++)sprintf(links+strlen(links),"%s%u",k?",":"",l[k]);
            if(!nl)strcpy(links,"-");
            if(strcmp(links,f[9])){fprintf(stderr,"answer %s topic %s links %s, want %s\n",f[1],f[2],links,f[9]);return 1;}
            nl=AW_DialSpans(&conv,got,read_mem,&file,sp,64);spans[0]=0;
            for(k=0;k<nl;k++)sprintf(spans+strlen(spans),"%s%u:%u:%u",k?",":"",sp[k].offset,sp[k].length,sp[k].topic);
            if(!nl)strcpy(spans,"-");
            if(strcmp(spans,f[10])){fprintf(stderr,"answer %s topic %s spans %s, want %s\n",f[1],f[2],spans,f[10]);return 1;}
            if(entry>=0){   /* the journal's links: the entry row gives the same spans as the answer (journal-links) */
                unsigned char row[AW_DIAL_ENTRY_ROW];aw_dial_span_t je[64];int nj;
                assert(read_mem(&file,d.at_entries+(long)AW_DIAL_ENTRY_ROW*entry,row,AW_DIAL_ENTRY_ROW));
                nj=AW_DialEntrySpans(&d,row,read_mem,&file,je,64);
                assert(nj==nl);
                for(k=0;k<nl;k++)assert(je[k].offset==sp[k].offset && je[k].length==sp[k].length && je[k].topic==sp[k].topic);
            }
        }else if(!strcmp(f[0],"greet")){         /* greet ID DISP ENTRY|-1: the greeting when the conversation opens */
            aw_glut_state_t s;int npc=AW_GlutFind(&g,f[1]),got,topic,entry;
            assert(n==4 && npc==opened);
            memset(&s,0,sizeof(s));s.random100=50;s.speaker_health_percent=s.player_health_percent=s.player_health=100;
            conv.cond.disposition=atoi(f[2]);conv.cond.choice=-1;
            got=AW_DialGreeting(&conv,&s,&topic);
            entry=got<0?-1:(int)conv.answer[got].entry;
            if(entry!=atoi(f[3]) || (got>=0)!=(AW_DialTopicKind(&d,topic)==AW_DIAL_KIND_GREETING)){
                fprintf(stderr,"greet %s disp %s: %d (topic %d), want %s\n",f[1],f[2],entry,topic,f[3]);return 1;}
        }else if(!strcmp(f[0],"topicmap")){      /* topicmap ROW|NAMES KNOWN-ROWS PRESET WANT: the saved topics by name */
            static unsigned long hashes[64];static unsigned short map[4096];static unsigned char known[8192];
            char *names[64],*q;int rows=0,k;char got[1024];
            assert(n==5 && d.topics<=4096);
            for(q=strtok(f[1],"|");q && rows<64;q=strtok(NULL,"|"))names[rows++]=q;
            for(k=0;k<rows;k++)hashes[k]=AW_DialNameHash(names[k],(int)strlen(names[k]));
            assert(AW_DialNameHash("My Ring",7)==AW_DialNameHash("my ring",7));
            memset(known_rows,0,sizeof(known_rows));
            for(q=strtok(f[2],",");q;q=strtok(NULL,","))if(strcmp(q,"-"))known_rows[atoi(q)]=1;
            memset(known,0,sizeof(known));
            for(q=strtok(f[3],",");q;q=strtok(NULL,","))if(strcmp(q,"-"))AW_DialKnow(&d,known,atoi(q));
            if(AW_DialTopicMap(&d,read_mem,&file,hashes,rows,map)<0){fprintf(stderr,"topicmap: a read failed\n");return 1;}
            AW_DialKnownSync(&d,known,map,row_known);
            got[0]=0;
            for(k=0;k<d.topics;k++)if(AW_DialKnows(&d,known,k))sprintf(got+strlen(got),"%s%d",got[0]?",":"",k);
            if(!got[0])strcpy(got,"-");
            if(strcmp(got,f[4])){fprintf(stderr,"topicmap: %s, want %s\n",got,f[4]);return 1;}
        }else if(!strcmp(f[0],"list")){          /* list ID DISP KNOWN(all|start) TOPIC,..|- */
            aw_glut_state_t s;int npc=AW_GlutFind(&g,f[1]),out[AW_DIAL_MAX_TOPICS],m,k;char got[4096];
            static unsigned char known[8192];
            assert(n==5 && npc==opened && AW_DialKnownBytes(&d)<=(long)sizeof(known));
            if(!strcmp(f[3],"all"))memset(known,0xFF,sizeof(known));else AW_DialKnownStart(&d,known);
            memset(&s,0,sizeof(s));s.random100=50;s.speaker_health_percent=s.player_health_percent=s.player_health=100;
            conv.cond.disposition=atoi(f[2]);conv.cond.choice=-1;
            m=AW_DialTopicList(&conv,known,&s,out,AW_DIAL_MAX_TOPICS);got[0]=0;
            for(k=0;k<m;k++)sprintf(got+strlen(got),"%s%d",k?",":"",out[k]);
            if(!m)strcpy(got,"-");
            if(strcmp(got,f[4])){fprintf(stderr,"list %s disp %s %s: %s, want %s\n",f[1],f[2],f[3],got,f[4]);return 1;}
        }else if(!strcmp(f[0],"disp")){          /* disp BASE RACE PERSONALITY BOUNTY FACTION RANKS DISEASED WEAPON CLAMP WANT */
            aw_dial_facts_t facts;int got;
            assert(n==11);
            memset(&facts,0,sizeof(facts));   /* no Charm here (tests/aga_dial_rules_test.c checks it) */
            facts.base=atoi(f[1]);facts.same_race=atoi(f[2]);facts.personality=(float)atof(f[3]);facts.bounty=atoi(f[4]);
            facts.faction=strcmp(f[5],"-")?f[5]:NULL;strcpy(disp_ranks,strcmp(f[6],"-")?f[6]:"");
            facts.diseased=atoi(f[7]);facts.weapon_drawn=atoi(f[8]);facts.rank=disp_rank;
            got=AW_DialDisposition(&d,&facts,atoi(f[9]));
            if(got!=atoi(f[10])){fprintf(stderr,"disp %s %s %s %s %s %s: %d, want %s\n",f[1],f[2],f[3],f[4],f[5],f[6],got,f[10]);return 1;}
        }else if(!strcmp(f[0],"dispbench")){     /* dispbench CALLS FACTION RANKS: the per-tick cost of the world's NPC aggro
                                                  * disposition (the rule on cached facts), printed in ns per call */
            aw_dial_facts_t facts;long calls=atol(f[1]),k;volatile int sink=0;clock_t t0;double ns;
            assert(n==4);
            memset(&facts,0,sizeof(facts));facts.base=40;facts.same_race=1;facts.personality=40;
            facts.faction=strcmp(f[2],"-")?f[2]:NULL;strcpy(disp_ranks,strcmp(f[3],"-")?f[3]:"");facts.rank=disp_rank;
            t0=clock();
            for(k=0;k<calls;k++){facts.bounty=(int)(k&63);sink+=AW_DialDisposition(&d,&facts,1);}
            ns=(double)(clock()-t0)*1e9/CLOCKS_PER_SEC/(double)(calls>0?calls:1);
            printf("dispbench %ld calls %.1f ns per call (%d)\n",calls,ns,sink&1);
        }else if(!strcmp(f[0],"services")){      /* services ROW WANT: the NPC row's service flags */
            unsigned long got;
            assert(n==3);
            got=AW_DialServices(&d,atoi(f[1]),read_mem,&file);
            if(got!=strtoul(f[2],NULL,10)){fprintf(stderr,"services %s: %lu, want %s\n",f[1],got,f[2]);return 1;}
        }else if(!strcmp(f[0],"reactmod")){      /* reactmod A B VALUE SET: a script's faction reaction change */
            assert(n==5 && AW_DialReactionChange(f[1],f[2],atoi(f[3]),atoi(f[4])));
        }else if(!strcmp(f[0],"heard")){         /* heard: the journal's topic pages (add, once, ClearInfoActor, a save) */
            static unsigned char blob[1<<16];int e,tp,k,m,a,b,c;const char *sp;char got[256];
            AW_DialHeardReset();
            a=AW_DialHeardAdd(5,1,"Fargoth");b=AW_DialHeardAdd(5,1,"Fargoth");c=AW_DialHeardAdd(9,1,"Hrisskar");
            AW_DialHeardAdd(7,2,"Fargoth");AW_DialHeardAdd(8,1,"Fargoth");
            assert(AW_DialHeardHas(8) && AW_DialHeardHas(9) && !AW_DialHeardHas(6));   /* an exhausted topic's test */
            k=AW_DialHeardRemoveLast(1,"fargoth");          /* the last of Fargoth on topic 1: entry 8 */
            assert(!AW_DialHeardHas(8));
            m=AW_DialHeardExport(blob,sizeof(blob));AW_DialHeardReset();
            sprintf(got,"%d %d %d %d %d",a,b,c,k,AW_DialHeardImport(blob,m)==m);
            for(k=0;k<AW_DialHeardCount();k++){AW_DialHeardAt(k,&e,&tp,&sp);sprintf(got+strlen(got)," %d:%d:%s",e,tp,sp);}
            /* the bound: the oldest of the fullest topic gives way, never a refusal */
            AW_DialHeardReset();for(k=0;k<12000;k++)AW_DialHeardAdd(k,k<11000?3:4,"X");
            m=AW_DialHeardAdd(20000,4,"X");AW_DialHeardAt(0,&e,&tp,&sp);
            sprintf(got+strlen(got)," full %d %d first %d",m,AW_DialHeardCount(),e);
            AW_DialHeardReset();
            if(strcmp(got,f[1])){fprintf(stderr,"heard: %s, want %s\n",got,f[1]);return 1;}
        }else if(!strcmp(f[0],"reactreset")){
            unsigned char blob[256];int k=AW_DialReactionsExport(blob,sizeof(blob)),m;
            m=AW_DialReactionsImport(blob,k);   /* through a save and back: the same changes */
            assert(k>0 && m==k);
            AW_DialReactionsReset();
        }else if(!strcmp(f[0],"rank")){          /* rank FACTION RANK NAME|- (any case) */
            char got[64];long at=AW_DialRankAt(&d,f[1],atoi(f[2]));
            assert(n==4);
            string_at(&file,at,got,sizeof(got));
            if(at>=0 && !got[0])strcpy(got,"-");
            if(strcmp(got,f[3])){fprintf(stderr,"rank %s %s: %s, want %s\n",f[1],f[2],got,f[3]);return 1;}
        }else if(!strcmp(f[0],"rankreq")){       /* rankreq FACTION RANK ATTRIBUTES(8) SKILLS(27) REPUTATION WANT */
            short attributes[8],skills[27];const char *s;int k,got;
            assert(n==7);
            for(s=f[3],k=0;k<8;k++){attributes[k]=(short)strtol(s,(char **)&s,10);if(*s==',')s++;}
            for(s=f[4],k=0;k<27;k++){skills[k]=(short)strtol(s,(char **)&s,10);if(*s==',')s++;}
            got=AW_DialRankRequirement(&d,f[1],atoi(f[2]),attributes,skills,atoi(f[5]),read_mem,&file);
            if(got!=atoi(f[6])){fprintf(stderr,"rankreq %s %s rep %s: %d, want %s\n",f[1],f[2],f[5],got,f[6]);return 1;}
        }else if(!strcmp(f[0],"persuade")){      /* persuade KIND PLAYER(7) NPC(7) DISP ROLL FIGHT FLEE "success temp perm fight flee" */
            aw_dial_person_t who[2];aw_dial_persuasion_t r;char got[64];int w;
            assert(n==9);
            for(w=0;w<2;w++){float v[7];
                assert(sscanf(f[2+w],"%f,%f,%f,%f,%f,%f,%f",&v[0],&v[1],&v[2],&v[3],&v[4],&v[5],&v[6])==7);
                who[w].personality=v[0];who[w].luck=v[1];who[w].reputation=v[2];who[w].speechcraft=v[3];
                who[w].mercantile=v[4];who[w].level=v[5];who[w].fatigue=v[6];}
            AW_DialPersuade(&d,atoi(f[1]),&who[0],&who[1],atoi(f[4]),atoi(f[5]),atoi(f[6]),atoi(f[7]),&r);
            sprintf(got,"%d %d %d %d %d",r.success,r.temp,r.perm,r.fight,r.flee);
            if(strcmp(got,f[8])){fprintf(stderr,"persuade %s %s %s disp %s roll %s: %s, want %s\n",f[1],f[2],f[3],f[4],f[5],got,f[8]);return 1;}
        }else if(!strcmp(f[0],"barter") || !strcmp(f[0],"trainprice") || !strcmp(f[0],"spellprice")){
            /* barter BASE BUYING PLAYER(7) NPC(7) DISP WANT; trainprice SKILL PLAYER(7) NPC(7) DISP WANT */
            aw_dial_person_t who[2];int w,got,o=!strcmp(f[0],"barter")?1:0;
            assert(n==(o?7:6));
            for(w=0;w<2;w++){float v[7];
                assert(sscanf(f[2+o+w],"%f,%f,%f,%f,%f,%f,%f",&v[0],&v[1],&v[2],&v[3],&v[4],&v[5],&v[6])==7);
                who[w].personality=v[0];who[w].luck=v[1];who[w].reputation=v[2];who[w].speechcraft=v[3];
                who[w].mercantile=v[4];who[w].level=v[5];who[w].fatigue=v[6];}
            got=o?AW_DialBarterOffer(&d,atoi(f[1]),atoi(f[2]),&who[0],&who[1],atoi(f[5])):
                  f[0][0]=='s'?AW_DialSpellPrice(&d,atoi(f[1]),&who[0],&who[1],atoi(f[4])):
                  AW_DialTrainingPrice(&d,atoi(f[1]),&who[0],&who[1],atoi(f[4]));
            if(got!=atoi(f[n-1])){fprintf(stderr,"%s %s %s %s: %d, want %s\n",f[0],f[1],f[2+o],f[3+o],got,f[n-1]);return 1;}
        }else if(!strcmp(f[0],"repairprice")){   /* repairprice VALUE MAX DURABILITY PLAYER(7) NPC(7) DISP WANT */
            aw_dial_person_t who[2];int w,got;
            assert(n==8);
            for(w=0;w<2;w++){float v[7];
                assert(sscanf(f[4+w],"%f,%f,%f,%f,%f,%f,%f",&v[0],&v[1],&v[2],&v[3],&v[4],&v[5],&v[6])==7);
                who[w].personality=v[0];who[w].luck=v[1];who[w].reputation=v[2];who[w].speechcraft=v[3];
                who[w].mercantile=v[4];who[w].level=v[5];who[w].fatigue=v[6];}
            got=AW_DialRepairPrice(&d,atoi(f[1]),atoi(f[2]),atoi(f[3]),&who[0],&who[1],atoi(f[6]));
            if(got!=atoi(f[7])){fprintf(stderr,"repairprice %s %s %s: %d, want %s\n",f[1],f[2],f[3],got,f[7]);return 1;}
        }else if(!strcmp(f[0],"caststyle")){     /* caststyle ITEM STYLE SOUL WANT */
            assert(n==5);
            if(AW_DialNextCastStyle(atoi(f[1]),atoi(f[2]),atoi(f[3]),&d)!=atoi(f[4])){fprintf(stderr,"caststyle %s %s %s\n",f[1],f[2],f[3]);return 1;}
        }else if(!strcmp(f[0],"enchant")){       /* enchant EFFECTS CONSTANT PLAYER NPC DISP "cast price chance points*100" */
            aw_dial_effect_t e[8];aw_dial_person_t who[2];int m=0,w,c=atoi(f[2]);char got[64];const char *s=f[1];
            assert(n==7);
            while(strcmp(s,"-") && *s && m<8){
                int used=0;
                assert(sscanf(s,"%f,%d,%d,%d,%d,%d,%d%n",&e[m].base_cost,&e[m].flags,&e[m].magnitude_min,&e[m].magnitude_max,
                              &e[m].duration,&e[m].area,&e[m].range,&used)==7);
                m++;s+=used;if(*s==0x3B)s++;
            }
            for(w=0;w<2;w++){float v[7];
                assert(sscanf(f[3+w],"%f,%f,%f,%f,%f,%f,%f",&v[0],&v[1],&v[2],&v[3],&v[4],&v[5],&v[6])==7);
                who[w].personality=v[0];who[w].luck=v[1];who[w].reputation=v[2];who[w].speechcraft=v[3];
                who[w].mercantile=v[4];who[w].level=v[5];who[w].fatigue=v[6];}
            sprintf(got,"%d %d %d %d",AW_DialEnchantCastCost(&d,e,m,c,45),AW_DialEnchantPrice(&d,e,m,c,&who[0],&who[1],atoi(f[5])),
                    AW_DialEnchantChance(&d,e,m,c,80,60,50,0.8f),(int)(AW_DialEnchantPoints(&d,e,m,c,1)*100));
            if(strcmp(got,f[6])){fprintf(stderr,"enchant %s const %s disp %s: %s, want %s\n",f[1],f[2],f[5],got,f[6]);return 1;}
        }else if(!strcmp(f[0],"spellmaking")){   /* spellmaking EFFECTS(b,f,lo,hi,dur,area,range;..|-) PLAYER NPC DISP "cost price" */
            aw_dial_effect_t e[8];aw_dial_person_t who[2];int m=0,w;char got[32];const char *s=f[1];
            assert(n==6);
            while(strcmp(s,"-") && *s && m<8){
                int used=0;
                assert(sscanf(s,"%f,%d,%d,%d,%d,%d,%d%n",&e[m].base_cost,&e[m].flags,&e[m].magnitude_min,&e[m].magnitude_max,
                              &e[m].duration,&e[m].area,&e[m].range,&used)==7);
                m++;s+=used;if(*s==0x3B)s++;
            }
            for(w=0;w<2;w++){float v[7];
                assert(sscanf(f[2+w],"%f,%f,%f,%f,%f,%f,%f",&v[0],&v[1],&v[2],&v[3],&v[4],&v[5],&v[6])==7);
                who[w].personality=v[0];who[w].luck=v[1];who[w].reputation=v[2];who[w].speechcraft=v[3];
                who[w].mercantile=v[4];who[w].level=v[5];who[w].fatigue=v[6];}
            sprintf(got,"%d %d",AW_DialSpellmakingCost(&d,e,m),AW_DialSpellmakingPrice(&d,e,m,&who[0],&who[1],atoi(f[4])));
            if(strcmp(got,f[5])){fprintf(stderr,"spellmaking %s disp %s: %s, want %s\n",f[1],f[4],got,f[5]);return 1;}
        }else if(!strcmp(f[0],"trainpicks")){    /* trainpicks SKILLS(27) WANT(a,b,c) */
            float v[27];int out[3],k,m;char got[32];const char *s=f[1];
            assert(n==3);
            for(k=0;k<27;k++){v[k]=(float)strtod(s,(char **)&s);if(*s==',')s++;}
            m=AW_DialTrainingPicks(v,27,out);got[0]=0;
            for(k=0;k<m;k++)sprintf(got+strlen(got),"%s%d",k?",":"",out[k]);
            if(strcmp(got,f[2])){fprintf(stderr,"trainpicks %s: %s, want %s\n",f[1],got,f[2]);return 1;}
        }else if(!strcmp(f[0],"uitext")){        /* uitext INDEX WANT: the window's word from the table */
            static char texts[AW_DIAL_TEXTS*AW_DIAL_UI_TEXT];
            assert(n==3 && atoi(f[1])>=0 && atoi(f[1])<AW_DIAL_TEXTS);
            assert(AW_DialUiTexts(&d,read_mem,&file,texts));
            if(strcmp(texts+AW_DIAL_UI_TEXT*atoi(f[1]),f[2])){fprintf(stderr,"uitext %s: %s, want %s\n",f[1],texts+AW_DIAL_UI_TEXT*atoi(f[1]),f[2]);return 1;}
        }else if(!strcmp(f[0],"skillattr")){     /* skillattr SKILL WANT (-1 unknown) */
            assert(n==3);
            if(AW_DialSkillAttribute(&d,atoi(f[1]),read_mem,&file)!=atoi(f[2])){fprintf(stderr,"skillattr %s\n",f[1]);return 1;}
        }else if(!strcmp(f[0],"spanfill")){      /* spanfill TEXT SPANS(o:l:t,..) PCRANK NEXT CELL WANT_TEXT WANT_SPANS */
            aw_dial_span_t in[16],out[16];int m=0,got,k;char marked[512],filled[512],shown[512],spans[256];const char *s=f[2];
            assert(n==8);
            while(strcmp(s,"-") && *s && m<16){
                in[m].offset=(unsigned short)strtol(s,(char **)&s,10);s++;in[m].length=(unsigned short)strtol(s,(char **)&s,10);s++;
                in[m].topic=(unsigned short)strtol(s,(char **)&s,10);m++;if(*s==',')s++;
            }
            AW_DialMarkSpans(f[1],in,m,marked,sizeof(marked));
            AW_DialFillDefines(marked,filled,sizeof(filled),f[3],f[4],f[5]);
            AW_DialTakeSpans(filled,in,m,shown,sizeof(shown),out,&got);
            spans[0]=0;for(k=0;k<got;k++)sprintf(spans+strlen(spans),"%s%u:%u:%u",k?",":"",out[k].offset,out[k].length,out[k].topic);
            if(!got)strcpy(spans,"-");
            if(strcmp(shown,f[6]) || strcmp(spans,f[7])){fprintf(stderr,"spanfill '%s': '%s' %s, want '%s' %s\n",f[1],shown,spans,f[6],f[7]);return 1;}
        }else if(!strcmp(f[0],"defines")){       /* defines TEXT PCRANK NEXT CELL WANT */
            char got[512];
            assert(n==6);
            AW_DialFillDefines(f[1],got,sizeof(got),f[2],f[3],f[4]);
            if(strcmp(got,f[5])){fprintf(stderr,"defines '%s': '%s', want '%s'\n",f[1],got,f[5]);return 1;}
        }else if(!strcmp(f[0],"live")){          /* from here on the conditions read the stub live state */
            aw_glut_live=&stub_live;live_count=0;
        }else if(!strcmp(f[0],"set")){           /* set KIND NAME VALUE */
            assert(n==4 && live_count<LIVE_ROWS);
            strcpy(live_rows[live_count].kind,f[1]);strcpy(live_rows[live_count].name,f[2]);
            live_rows[live_count++].value=atol(f[3]);
        }else if(!strcmp(f[0],"faction")){       /* the open conversation's speaker faction (- none) */
            static char faction[64];
            assert(n==2);
            if(strcmp(f[1],"-")){strcpy(faction,f[1]);conv.cond.faction=faction;}else conv.cond.faction=NULL;
        }else if(!strcmp(f[0],"start")){         /* start TOPIC,..|- */
            char got[1024];int k;got[0]=0;
            for(k=0;AW_DialStartTopic(&d,k)>=0;k++)sprintf(got+strlen(got),"%s%d",k?",":"",AW_DialStartTopic(&d,k));
            if(!k)strcpy(got,"-");
            if(strcmp(got,f[1])){fprintf(stderr,"start %s, want %s\n",got,f[1]);return 1;}
        }else if(!strcmp(f[0],"wrap")){          /* wrap COLS TEXT LINE|LINE.. ('~' for a space-free empty line) */
            const char *p;char out[128],got[2048],*w=f[2],*r=f[2];int k=0;got[0]=0;
            while(*r){if(r[0]=='\\' && r[1]=='n'){*w++='\n';r+=2;}else *w++=*r++;}   /* "\n" in the line: a line end */
            *w=0;p=f[2];
            while(AW_DialWrapNext(&p,atoi(f[1]),out,sizeof(out))){
                assert((int)strlen(out)<=atoi(f[1]));
                sprintf(got+strlen(got),"%s%s",k++?"|":"",*out?out:"~");
            }
            if(strcmp(got,f[3])){fprintf(stderr,"wrap %s '%s': %s, want %s\n",f[1],f[2],got,f[3]);return 1;}
        }else{fprintf(stderr,"unknown line %s\n",f[0]);return 1;}
        checks++;
    }
    fclose(x);
    assert(AW_DialTopicKind(&d,-1)==-1 && AW_DialTopicName(&d,(int)d.topics,NULL)==-1);
    printf("%d checks, %ld reads\n",checks,file.reads);
    free(data);free(voices);
    return 0;
}
