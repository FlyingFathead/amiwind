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
            unsigned short l[64];int nl,k;
            assert(n==10 && npc==opened);
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
            facts.base=atoi(f[1]);facts.same_race=atoi(f[2]);facts.personality=(float)atof(f[3]);facts.bounty=atoi(f[4]);
            facts.faction=strcmp(f[5],"-")?f[5]:NULL;strcpy(disp_ranks,strcmp(f[6],"-")?f[6]:"");
            facts.diseased=atoi(f[7]);facts.weapon_drawn=atoi(f[8]);facts.rank=disp_rank;
            got=AW_DialDisposition(&d,&facts,atoi(f[9]));
            if(got!=atoi(f[10])){fprintf(stderr,"disp %s %s %s %s %s %s: %d, want %s\n",f[1],f[2],f[3],f[4],f[5],f[6],got,f[10]);return 1;}
        }else if(!strcmp(f[0],"rank")){          /* rank FACTION RANK NAME|- (any case) */
            char got[64];long at=AW_DialRankAt(&d,f[1],atoi(f[2]));
            assert(n==4);
            string_at(&file,at,got,sizeof(got));
            if(at>=0 && !got[0])strcpy(got,"-");
            if(strcmp(got,f[3])){fprintf(stderr,"rank %s %s: %s, want %s\n",f[1],f[2],got,f[3]);return 1;}
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
