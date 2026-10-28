/* SPDX-License-Identifier: GPL-2.0-or-later
 * The voice table (engine/aga/src/aw_glut.c, NPC-GREETINGS-LIBRARY-MUTE-48), compiled natively.
 * With AW_GLUT_HOST_TEST: the pure part on a real AWGL2 file the builder made (tests/test_greeting_lut.py):
 *   aga_glut_test pure TABLE EXPECTATIONS   (tab-separated lines: find / pick / sound / expand / damaged)
 * Without it: the engine glue with the real aw_anim.c and small Quake stubs: the greet trigger's spawn step
 * (hello distance for an NPC without its own greeting, a town resident's own fields kept), the hello said with
 * its voice or quiet when the build lacks the file, the conversation greeting with the speaker's defines filled,
 * the barks through the table and the previous method with aw_npc_voice_lut 0:
 *   aga_glut_test glue TABLE PRESENT_HEX16[,..] */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef AW_GLUT_HOST_TEST
#include "aw_glut.h"

static unsigned char *slurp(const char *path,long *size) {
    FILE *f=fopen(path,"rb");unsigned char *d;
    assert(f);fseek(f,0,SEEK_END);*size=ftell(f);fseek(f,0,SEEK_SET);
    d=(unsigned char *)malloc((size_t)*size);assert(d);
    assert((long)fread(d,1,(size_t)*size,f)==*size);fclose(f);
    return d;
}
static int topic_of(const char *name) {
    static const char *const names[]={"hello","idle","intruder","thief","hit","attack","flee","greeting"};
    int i;for(i=0;i<AW_GLUT_TOPICS;i++)if(!strcmp(names[i],name))return i;
    assert(0);return -1;
}
int main(int argc,char **argv) {
    long size,resident;unsigned char *data;aw_glut_t g;char line[2048];FILE *x;int checks=0;
    assert(argc==4 && !strcmp(argv[1],"pure"));
    data=slurp(argv[2],&size);
    resident=AW_GlutResidentSize(data,size);
    assert(resident>AW_GLUT_HEADER && resident<size);
    assert(AW_GlutOpen(&g,data,resident,size));
    /* a truncated resident part, or one past the file, is refused */
    {aw_glut_t bad;assert(!AW_GlutOpen(&bad,data,resident-4,size));assert(!AW_GlutOpen(&bad,data,resident,size+4));}
    x=fopen(argv[3],"r");assert(x);
    while(fgets(line,sizeof(line),x)){
        char *f[8];int n=0;char *p=strtok(line,"\t\n");
        while(p && n<8){f[n++]=p;p=strtok(NULL,"\t\n");}
        if(!n)continue;
        if(!strcmp(f[0],"find")){
            assert(n==3);
            if(AW_GlutFind(&g,f[1])!=atoi(f[2])){fprintf(stderr,"find %s: %d, want %s\n",f[1],AW_GlutFind(&g,f[1]),f[2]);return 1;}
        }else if(!strcmp(f[0],"hello")){
            assert(n==3 && AW_GlutHelloDistance(&g,AW_GlutFind(&g,f[1]))==atoi(f[2]));
        }else if(!strcmp(f[0],"pick")){
            aw_glut_state_t s;int got;
            assert(n==8);
            s.talked=atoi(f[3]);s.random100=atoi(f[4]);s.speaker_health_percent=atoi(f[5]);
            s.player_health_percent=atoi(f[6]);s.player_health=s.player_health_percent;
            got=AW_GlutPick(&g,AW_GlutFind(&g,f[1]),topic_of(f[2]),&s,0,0);
            if(got!=atoi(f[7])){fprintf(stderr,"pick %s %s talked %s r %s hp %s: %d, want %s\n",f[1],f[2],f[3],f[4],f[5],got,f[7]);return 1;}
            /* the random-pick option returns one of the entries that hold, never one that does not */
            if(got>=0){int k;for(k=0;k<8;k++){int r=AW_GlutPick(&g,AW_GlutFind(&g,f[1]),topic_of(f[2]),&s,1,k);assert(r>=0);}}
        }else if(!strcmp(f[0],"sound")){
            unsigned char h[8];char hex[17];int k;
            assert(n==3);
            if(!strcmp(f[2],"-"))assert(!AW_GlutSound(&g,atoi(f[1]),h));
            else{assert(AW_GlutSound(&g,atoi(f[1]),h));for(k=0;k<8;k++)sprintf(hex+2*k,"%02x",h[k]);assert(!strcmp(hex,f[2]));}
        }else if(!strcmp(f[0],"creature")){     /* creature ID ROW [S0,..,S7] (Sounds index, -1 none) */
            int row=AW_GlutCreatureFind(&g,f[1]),k;
            assert(n==3 || n==4);
            if(row!=atoi(f[2])){fprintf(stderr,"creature %s: %d, want %s\n",f[1],row,f[2]);return 1;}
            if(n==4){char *s=f[3];for(k=0;k<AW_SNDG_MOMENTS;k++){int want=(int)strtol(s,&s,10);
                if(AW_GlutCreatureSound(&g,row,k)!=want){fprintf(stderr,"creature %s moment %d: %d, want %d\n",f[1],k,AW_GlutCreatureSound(&g,row,k),want);return 1;}
                if(*s==',')s++;}}
            assert(AW_GlutCreatureSound(&g,row,AW_SNDG_MOMENTS)==-1 && AW_GlutCreatureSound(&g,-1,0)==-1);
        }else if(!strcmp(f[0],"slot")){         /* slot N INDEX PATH|- */
            char path[AW_GLUT_POOL_PATH];int got=AW_GlutSlotSound(&g,atoi(f[1]));
            assert(n==4);
            if(got!=atoi(f[2])){fprintf(stderr,"slot %s: %d, want %s\n",f[1],got,f[2]);return 1;}
            if(got>=0){assert(AW_GlutPoolPath(&g,got,path,sizeof(path)));assert(!strcmp(path,f[3]));}
            assert(!AW_GlutPoolPath(&g,got>=0?got:0,path,AW_GLUT_POOL_PATH-1));
        }else if(!strcmp(f[0],"slen")){         /* slen SOUND CENTIS MAPPED */
            assert(n==4);
            if(AW_GlutSoundLength(&g,atoi(f[1]))!=atoi(f[2]) || AW_GlutSoundMapped(&g,atoi(f[1]))!=atoi(f[3])){
                fprintf(stderr,"slen %s: %d %d\n",f[1],AW_GlutSoundLength(&g,atoi(f[1])),AW_GlutSoundMapped(&g,atoi(f[1])));return 1;}
        }else if(!strcmp(f[0],"soun")){         /* soun INDEX HEX CENTIS VOLUME MAPPED NEAR FAR */
            aw_glut_soun_t s;char hex[17];int k;
            assert(n==8 && AW_GlutSoun(&g,atoi(f[1]),&s));
            for(k=0;k<8;k++)sprintf(hex+2*k,"%02x",s.hash[k]);
            {char got[96];
             sprintf(got,"%s %u %u %u",hex,(unsigned)s.centis,(unsigned)s.volume,(unsigned)s.mapped);
             if(strcmp(hex,f[2]) || s.centis!=atoi(f[3]) || s.volume!=atoi(f[4]) || s.mapped!=atoi(f[5]) ||
                s.near_units!=atoi(f[6]) || s.far_units!=atoi(f[7])){fprintf(stderr,"soun %s: %s %u %u\n",f[1],got,s.near_units,s.far_units);return 1;}}
            assert(!AW_GlutSoun(&g,(int)g.souns,&s) && !AW_GlutSoun(&g,-1,&s));
        }else if(!strcmp(f[0],"expand")){
            char out[512];
            assert(n==5);
            AW_GlutExpand(&g,AW_GlutFind(&g,f[1]),f[2],f[3],out,sizeof(out));
            if(strcmp(out,f[4])){fprintf(stderr,"expand: '%s', want '%s'\n",out,f[4]);return 1;}
            AW_GlutExpand(&g,AW_GlutFind(&g,f[1]),f[2],f[3],out,8);assert(strlen(out)==7);   /* capacity kept */
        }else assert(0);
        checks++;
    }
    fclose(x);
    assert(AW_GlutFind(&g,"nobody")==-1 && AW_GlutFind(&g,"")==-1 && AW_GlutFind(&g,NULL)==-1);
    printf("%d checks\n",checks);
    free(data);
    return 0;
}
#else
#include "quakedef.h"
#include "aw_anim.h"
#include "aw_combat.h"
#include "aw_glut.h"

server_t sv;server_static_t svs;client_static_t cls;client_state_t cl;
char *pr_strings;double realtime;
void (*aw_combat_voice)(edict_t *,int);
static char strings[4096];static int string_at=1;
static edict_t edicts[6];
static struct {eval_t source,voice,hello,reset,duration,manual,netname;} fields[6];
static const char *table_path,*present;
static int played,precached_ok;static char last_sound[64];
static sfx_t sample;static sfxcache_t cache={11025,0,11025,1,0,{0}};
static cvar_t *lut_cvar;

static int add_string(const char *s){int at=string_at;strcpy(strings+at,s);string_at+=(int)strlen(s)+1;return at;}
void Cvar_RegisterVariable(cvar_t *c){c->value=(float)atof(c->string);if(!strcmp(c->name,"aw_npc_voice_lut"))lut_cvar=c;}
int Hunk_LowMark(void){return 0;}
void Hunk_FreeToLowMark(int m){(void)m;}
byte *COM_LoadHunkFile(char *p){(void)p;return NULL;}
model_t *Mod_FindName(char *n){(void)n;return NULL;}
model_t *Mod_ForName(char *n,qboolean crash){(void)n;(void)crash;return NULL;}
void *Cache_Check(cache_user_t *c){(void)c;return NULL;}
void Cache_Free(cache_user_t *c){(void)c;}
void Con_Printf(char *f,...){(void)f;}
void Con_DPrintf(char *f,...){(void)f;}
void Sys_Error(char *f,...){(void)f;abort();}
int AW_CombatHealthPercent(edict_t *e){(void)e;return -1;}
void AW_ExpandDialogue(char *out,int capacity,const char *source){
    /* the player's defines: only %PCName here */
    const char *p=strstr(source,"%PCName");
    if(!p){strncpy(out,source,(size_t)capacity-1);out[capacity-1]=0;return;}
    snprintf(out,(size_t)capacity,"%.*sNerevar%s",(int)(p-source),source,p+7);
}
int COM_FOpenFile(char *p,FILE **f){
    char hex[17];
    *f=NULL;
    if(!strcmp(p,"npc-voices.lut")){long n;*f=fopen(table_path,"rb");if(!*f)return -1;fseek(*f,0,SEEK_END);n=ftell(*f);fseek(*f,0,SEEK_SET);return (int)n;}
    if(!strncmp(p,"sound/pool/a",12) && strlen(p)==32){
        memcpy(hex,p+12,16);hex[16]=0;
        if(strstr(present,hex)){*f=tmpfile();return 2048;}
    }
    return -1;
}
int SV_PointContents(vec3_t p){(void)p;return CONTENTS_EMPTY;}
trace_t SV_Move(vec3_t a,vec3_t mi,vec3_t ma,vec3_t b,int t,edict_t *e){trace_t x;(void)a;(void)mi;(void)ma;(void)b;(void)t;(void)e;memset(&x,0,sizeof(x));x.fraction=1;return x;}
void SV_StartSound(edict_t *e,int c,char *s,int v,float a){(void)e;(void)c;(void)s;(void)v;(void)a;}
void S_StartSound(int e,int c,sfx_t *s,vec3_t o,float v,float a){(void)o;(void)v;(void)a;assert(c==2 && s==&sample && e>=2);played++;}
sfx_t *S_PrecacheSound(char *s){strcpy(last_sound,s);precached_ok++;return &sample;}
sfxcache_t *S_LoadSound(sfx_t *s){(void)s;return &cache;}
edict_t *EDICT_NUM(int n){assert(n>=0 && n<6);return &edicts[n];}
int NUM_FOR_EDICT(edict_t *e){return (int)(e-edicts);}
eval_t *GetEdictFieldValue(edict_t *e,char *name){
    int n=NUM_FOR_EDICT(e);
    if(!strcmp(name,"aw_source_id"))return &fields[n].source;
    if(!strcmp(name,"aw_voice"))return &fields[n].voice;
    if(!strcmp(name,"aw_hello_distance"))return &fields[n].hello;
    if(!strcmp(name,"aw_hello_reset"))return &fields[n].reset;
    if(!strcmp(name,"aw_greet_duration"))return &fields[n].duration;
    if(!strcmp(name,"aw_manual_count"))return &fields[n].manual;
    return NULL;
}
static void actor(int n,const char *id,const char *name,const char *voice,float hello){
    memset(&edicts[n],0,sizeof(edicts[n]));memset(&fields[n],0,sizeof(fields[n]));
    fields[n].source.string=id?add_string(id):0;
    fields[n].voice.string=voice?add_string(voice):0;
    fields[n].hello._float=hello;
    edicts[n].v.netname=add_string(name);
    edicts[n].v.health=100;
}
int main(int argc,char **argv){
    char text[512];int before;
    assert(argc==4 && !strcmp(argv[1],"glue"));
    table_path=argv[2];present=argv[3];
    pr_strings=strings;cls.state=ca_connected;svs.maxclients=1;
    edicts[1].v.health=100;edicts[1].v.max_health=100;
    AW_AnimInit();AW_GlutInit();assert(lut_cvar && lut_cvar->value==1);
    actor(2,"Dunmer_M","Dral",NULL,0);                 /* a library actor: no greeting fields of its own */
    actor(3,"dunmer_f","Dralasa",NULL,0);              /* its hello voice is not in this build's voice pool */
    actor(4,"mage","Edwinna","npc/a_town.wav",30);     /* a town resident with its own hello */
    actor(5,"nobody","Ghost",NULL,0);
    /* spawn (QC aw_npc -> aw_glut_prep): the hello distance from the table; a resident keeps its own */
    assert(AW_GlutPrep(&edicts[2]) && fields[2].hello._float==45 && fields[2].reset._float==128 && fields[2].duration._float==4);
    assert(AW_GlutPrep(&edicts[4]) && fields[4].hello._float==30 && fields[4].reset._float==0);
    assert(!AW_GlutPrep(&edicts[5]) && fields[5].hello._float==0);
    assert(AW_GlutNpcOf(&edicts[2])>=0 && AW_GlutNpcOf(&edicts[2])==AW_GlutNpcOf(&edicts[2]));   /* cached */
    /* the greet trigger's hello (QC aw_greet -> aw_glut_say): the line, its voice */
    before=played;
    assert(AW_GlutSay(&edicts[2],AW_GLUT_HELLO,0) && !strcmp(AW_GlutText(),"Outlander.") && played==before+1);
    /* the voice file is missing from the pool: the line is shown, nothing plays (base disposition 50 < 60) */
    before=played;
    assert(AW_GlutSay(&edicts[3],AW_GLUT_HELLO,0) && !strcmp(AW_GlutText(),"Hmph.") && played==before);
    assert(!AW_GlutSay(&edicts[5],AW_GLUT_HELLO,0) && !strcmp(AW_GlutText(),""));
    /* the conversation greeting: the journal line is closed at the start; the speaker's and player's defines */
    assert(AW_GlutConverse(&edicts[4],0,text,sizeof(text)) && !strcmp(text,"I am Edwinna, a Mage of the Mages Guild."));
    assert(AW_GlutConverse(&edicts[2],0,text,sizeof(text)) && !strcmp(text,"What do you want, %PCRace?"));
    /* barks through the table (a town resident too): Attack always said, its file present */
    realtime=10;before=played;
    assert(AW_VoiceSay(&edicts[4],AW_VOICE_ATTACK_LINE,10000) && played==before+1);
    assert(!strncmp(last_sound,"pool/a",6));
    realtime=20;
    /* aw_npc_voice_lut 0: the previous method (the model's own lines; these models have none) */
    lut_cvar->value=0;before=played;
    assert(AW_GlutNpcOf(&edicts[2])<0 && !AW_VoiceSay(&edicts[2],AW_VOICE_ATTACK_LINE,10000) && played==before);
    assert(!AW_GlutSay(&edicts[2],AW_GLUT_HELLO,0));
    lut_cvar->value=1;
    /* a new level reuses the edict number for another record: the cache follows the record id */
    actor(2,"breton_m","Jean",NULL,0);
    assert(AW_GlutPrep(&edicts[2]) && AW_GlutSay(&edicts[2],AW_GLUT_HELLO,0) && !strcmp(AW_GlutText(),"Hello."));
    printf("glue ok\n");
    return 0;
}
#endif
