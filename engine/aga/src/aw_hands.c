/* SPDX-License-Identifier: GPL-2.0-or-later
 * The first-person hands (FIRST-PERSON-HANDS-IN-C-54; was world.qc aw_hands_update): the clips table the image carries
 * (gfx/hand-anims.txt, tools/hand_metadata.py hand_table) and the hands' state machine. The clips are no longer
 * stamped into every map's worldspawn nor written into the QuakeC, so a change to the hands rebuilds the image only,
 * never the world. Declarations: aw_hand_models.h. The pure part (the table, the frame) is host-tested
 * (tests/aga_hand_table_test.c, -DAW_HANDS_HOST_TEST); the state machine with the compiled QuakeC and the torch
 * (tests/aga_torch_qc_test.c).
 */
#include <string.h>
#include "aw_hand_models.h"

/* ---- the hand clips table, pure ---- */
static const char *hand_word(const char *p,char *out,int size) {
    int n=0;
    while(*p==' ' || *p=='\t')p++;
    while(*p && *p!=' ' && *p!='\t' && *p!='\n' && *p!='\r'){if(n<size-1)out[n++]=*p;p++;}
    out[n]=0;
    return p;
}
/* digits and one point only (no strtod: it reaches 68040-unimplemented FPU code) */
static int hand_number(const char *s,float *out) {
    long whole=0;float frac=0,scale=.1f;int digits=0;
    while(*s>='0' && *s<='9'){if(whole<100000)whole=whole*10+(*s-'0');s++;digits++;}
    if(*s=='.'){s++;while(*s>='0' && *s<='9'){frac+=(float)(*s-'0')*scale;scale*=.1f;s++;digits++;}}
    if(!digits || *s)return 0;
    *out=(float)whole+frac;return 1;
}
int AW_HandTableParse(const char *text,aw_hand_table_t *out) {
    static const char *const names[AW_HAND_CLIPS]={"idle","draw","lower","punch"};
    char word[16],name[16],a[16],b[16],c[16];int seen=0,i;const char *p=text;float first,count,duration;
    memset(out,0,sizeof(*out));
    if(!p)return 0;
    p=hand_word(p,word,sizeof(word));
    if(strcmp(word,"AWHA1"))return 0;
    while(*p){
        while(*p=='\n' || *p=='\r' || *p==' ' || *p=='\t')p++;
        if(!*p)break;
        p=hand_word(p,word,sizeof(word));
        if(strcmp(word,"clip")){while(*p && *p!='\n')p++;continue;}       /* later lines (stances) are skipped */
        p=hand_word(p,name,sizeof(name));p=hand_word(p,a,sizeof(a));p=hand_word(p,b,sizeof(b));p=hand_word(p,c,sizeof(c));
        for(i=0;i<AW_HAND_CLIPS && strcmp(name,names[i]);i++);
        if(i==AW_HAND_CLIPS || (seen>>i&1) || !hand_number(a,&first) || !hand_number(b,&count) || !hand_number(c,&duration))return 0;
        if(first>255 || count<1 || count>64 || !(duration>0 && duration<=60))return 0;
        {int f=(int)first,n=(int)count;out->first[i]=f;out->count[i]=n;out->duration[i]=duration;}
        seen|=1<<i;
    }
    return seen==(1<<AW_HAND_CLIPS)-1;
}
int AW_HandClipFrame(const aw_hand_table_t *t,int clip,float elapsed) {
    int f;
    if(clip<0 || clip>=AW_HAND_CLIPS)return 0;
    if(!(elapsed>0))elapsed=0;
    f=(int)(elapsed*(float)t->count[clip]/t->duration[clip]);
    if(f>=t->count[clip])f=t->count[clip]-1;
    return t->first[clip]+f;
}

#ifndef AW_HANDS_HOST_TEST
#include "quakedef.h"

/* ---- the hands' state machine ----
 * States: 0 down, 1 drawing, 2 ready (idle), 3 punching, 4 lowering. impulse 202 raises or lowers the hands; the
 * attack button punches from the ready state, once per press; a carried torch takes the place of the punch. The
 * player's QuakeC fields as before (aw_hand_state, aw_hand_goal, aw_hand_started, aw_torch, aw_attack_latched), so
 * the torch, combat, the view, the gallery and the saves read them unchanged. */
static aw_hand_table_t hand_table;
static int hand_table_state;          /* 0 not read yet, 1 ready, -1 none in this image */
void AW_HandTableReset(void) {hand_table_state=0;}
static void hand_table_load(void) {
    FILE *f=NULL;int size;char text[1024];
    if(hand_table_state)return;
    hand_table_state=-1;
    size=COM_FOpenFile(AW_HAND_TABLE_PATH,&f);
    if(!f)return;
    if(size>0 && size<(int)sizeof(text) && fread(text,1,(size_t)size,f)==(size_t)size){
        text[size]=0;
        if(AW_HandTableParse(text,&hand_table))hand_table_state=1;
    }
    fclose(f);
}
int AW_HandTableReady(void) {hand_table_load();return hand_table_state>0;}
float AW_HandDuration(int clip,float fallback) {
    return AW_HandTableReady() && clip>=0 && clip<AW_HAND_CLIPS?hand_table.duration[clip]:fallback;
}
static float hand_get(edict_t *p,const char *name) {eval_t *v=GetEdictFieldValue(p,(char *)name);return v?v->_float:0;}
static void hand_set(edict_t *p,const char *name,float value) {eval_t *v=GetEdictFieldValue(p,(char *)name);if(v)v->_float=value;}
static void hand_begin(edict_t *p,int state) {hand_set(p,"aw_hand_state",(float)state);hand_set(p,"aw_hand_started",(float)sv.time);}
static void hand_show(edict_t *p,int on) {
    int i;
    p->v.weaponmodel=0;
    if(!on)return;
    for(i=1;i<MAX_MODELS && sv.model_precache[i];i++)
        if(!strcmp(sv.model_precache[i],"progs/v_nord.mdl")){p->v.weaponmodel=sv.model_precache[i]-pr_strings;return;}
}
void AW_HandsTick(void) {
    edict_t *p;int state,goal,clip;float elapsed;
    /* runs when the server's physics run (host.c: not paused, not frozen by a modal screen, the game has the keys) */
    if(!sv.active || sv.paused || AW_ModalWorldFrozen() || (svs.maxclients==1 && key_dest!=key_game))return;
    if(svs.maxclients<1 || !svs.clients || !(p=svs.clients[0].edict) || p->free)return;
    if(!GetEdictFieldValue(p,"aw_hand_state"))return;      /* progs without hands */
    if(p->v.impulse==202){p->v.impulse=0;hand_set(p,"aw_hand_goal",1-hand_get(p,"aw_hand_goal"));}
    goal=hand_get(p,"aw_hand_goal")!=0;state=(int)hand_get(p,"aw_hand_state");
    /* no valid table in the image: never an invisible raising state that takes V forever */
    if((goal || state) && !AW_HandTableReady()){
        hand_set(p,"aw_hand_goal",0);hand_set(p,"aw_torch",0);hand_begin(p,0);hand_show(p,0);
        Con_Printf("Hands unavailable: this image has no valid hand clip table (gfx/hand-anims.txt); rebuild it.\n");
        return;
    }
    if(!goal || p->v.health<=0)hand_set(p,"aw_torch",0);
    if(state==0 && goal){hand_begin(p,1);state=1;}
    if(state==2 && !goal){hand_begin(p,4);state=4;}
    if(!p->v.button0)hand_set(p,"aw_attack_latched",0);
    if(p->v.button0 && !hand_get(p,"aw_attack_latched")){
        /* a press held while raising is still pending when the hands are ready; a held attack never repeats */
        if(state!=1)hand_set(p,"aw_attack_latched",1);
        if(state==2 && !hand_get(p,"aw_torch")){hand_begin(p,3);state=3;}
    }
    if(state==0){hand_show(p,0);return;}
    hand_show(p,1);
    clip=state==1?AW_HAND_DRAW:state==3?AW_HAND_PUNCH:state==4?AW_HAND_LOWER:AW_HAND_IDLE;
    elapsed=(float)sv.time-hand_get(p,"aw_hand_started");
    if(elapsed>=hand_table.duration[clip]){
        if(state==4){hand_begin(p,0);hand_show(p,0);return;}
        hand_begin(p,2);clip=AW_HAND_IDLE;elapsed=0;
    }
    p->v.weaponframe=(float)AW_HandClipFrame(&hand_table,clip,elapsed);
}
#endif
