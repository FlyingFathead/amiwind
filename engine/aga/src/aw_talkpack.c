/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_talkpack.c: the skeletal actors' mouths (NPC-TALK-MOUTH-STILL-69).
 *
 * The original moves a speaking NPC's mouth by its head's Talk morph whenever it says anything, in the world or in a
 * conversation (OpenMW 0.53 apps/openmw/mwrender/npcanimation.cpp 162-195 HeadAnimationTime::update: while the actor
 * says a line, the morph's time follows SoundManager::getSaySoundLoudness of that line; the head part's "talk: start"
 * and "talk: stop" keys, 834-846). The 21-frame opening actors carry the morph as talk frames (aw_speech.c
 * AW_SpeechPose); a skeletal actor carries none, so this module moves its head's vertices:
 *
 *   id1/talk.awt (tools/talk_pack.py, read from the game data only): per head of the game, the original vertices the
 *   Talk morph moves (and the still ones around them), in the bone space of the tables' head bone, with their offsets
 *   at the three open levels of the speech envelope; per NPC record (by the FNV-1a hash of its id) its head; none for
 *   an NPC whose helmet takes the head's place (the original draws no head under it).
 *
 *   When an NPC with a skeletal model starts a voice line, aw_speech.c asks AW_TalkTalker for its head (and computes
 *   the line's mouth levels from its samples); while it speaks, the renderer (r_alias.c R_AliasSkelFrame) keys the
 *   pose by the level (AW_TalkLevel) and, after posing it, calls AW_TalkApply: each of the model's head-bone vertices
 *   within AW_TALK_AROUND units of the head's kept vertices takes their offsets (inverse square distance weights; a
 *   vertex on an original one takes its own), computed once per model and head and kept (AW_TALK_MODELS), and is
 *   posed again with them through the same bone matrix and the same rounding as AW_SkelPoseVerts.
 *
 * Memory at 32 MB Fast, bounded by the caps whatever the town (Balmora, Vivec): the pack's record and head tables
 * once the file is first used (8 bytes a record and a head; about 24 KB for the three masters, AW_TryMalloc), and
 * the static AW_TALK_HEADS heads' rows (16 KB) and AW_TALK_MODELS models' vertex lists (20 KB); dbg speech prints it.
 * aw_talk_skeletal 0 switches it off (the previous method: a skeletal actor's mouth stays shut), for an A/B. */
#include "quakedef.h"
#include "aw_skel.h"
#include "aw_tryalloc.h"

#define AW_TALK_HEADER	20
#define AW_TALK_VERT	16
#define AW_TALK_HEADS	4		/* heads kept (at most four voice tracks speak at once, aw_speech.c) */
#define AW_TALK_MODELS	4		/* models' vertex lists kept */
#define AW_TALK_MAX	256		/* a model's talking vertices (on the v0.0.69-dev5 models: at most 188) */
#define AW_TALK_REGION	256		/* a head's kept original vertices (tools/talk_pack.py MAX_ROWS; the pack: at most 200) */
#define AW_TALK_AROUND	1.0f	/* an original vertex this near a model vertex lends it its offsets (bone units) */
#define AW_TALK_OFF_UNITS 1024.0f	/* a model vertex's kept offsets: bone units x this, in shorts */

cvar_t aw_talk_skeletal={"aw_talk_skeletal","1",false,false,1};	/* registered in aw_debug.c, not saved */
/* aw_debug.c sets them: the record id (aw_source_id) of a client entity whose model is skeletal, else NULL; the clock
 * (Sys_FloatTime) for the time a model's list takes. NULL in fixtures. */
const char *(*aw_talk_record)(int entity);
double (*aw_talk_clock)(void);
int AW_SpeechLevel(int entity,int *head);	/* aw_speech.c */

unsigned long AW_TalkHash(const char *id);
int AW_TalkHeadOfId(const char *id);
int AW_TalkTalker(int entity,int *head);
int AW_TalkLevel(int entity);
int AW_TalkApply(int entity,const void *model,const void *hdr,const aw_skel_block_t *block,const float world[][3][4],
                 unsigned char *out);
int AW_TalkLevelOf(const entity_t *e);
int AW_TalkApplyOf(const entity_t *e,const void *hdr,const aw_skel_block_t *block,const float world[][3][4],
                   unsigned char *out);
void AW_TalkStatus(void);

static int pack_state;			/* 0 not read yet, 1 read, -1 none or refused (said once) */
static unsigned char *table;		/* records x 8 (u32 hash, u16 head, u16 0), then heads x 8 (u32 offset, u16 rows, u16 0) */
static long record_count,head_count,head_bytes,data_at;
static int head_bone;
typedef struct {int head,n;unsigned used;unsigned char rows[AW_TALK_REGION][AW_TALK_VERT];} talk_head_t;
static talk_head_t heads[AW_TALK_HEADS];
typedef struct {const void *model,*hdr;int head,n;unsigned used;unsigned short index[AW_TALK_MAX];
    short off[AW_TALK_MAX][3][3];} talk_model_t;
static talk_model_t models[AW_TALK_MODELS];
static float region[AW_TALK_REGION][3];
static unsigned clock_;
static unsigned long transfers,poses,head_reads;
static double transfer_ms_last,transfer_ms_max;

static unsigned u16(const unsigned char *p){return (unsigned)p[0]<<8|p[1];}
static unsigned long u32(const unsigned char *p){return (unsigned long)u16(p)<<16|u16(p+2);}
static int s16(const unsigned char *p){int v=(int)u16(p);return v>=32768?v-65536:v;}
/* v rounded to the nearest integer, clamped to 0..255, as aw_skel.c byte_of (no float-to-integer conversion: the
 * 68040 has no FINTRZ) */
static int byte_of(float v){
    union {float f;unsigned int u;} m;
    if(!(v>0))return 0;
    if(v>=255)return 255;
    m.f=v+12582912.0f;
    return (int)(m.u&0x3FFFFF);
}

/* the record id's hash as tools/talk_pack.py fnv1a: FNV-1a 32 over its bytes, ASCII letters lowered */
unsigned long AW_TalkHash(const char *id) {
    unsigned long h=0x811C9DC5UL;
    for(;*id;id++){unsigned c=(unsigned char)*id;if(c>='A' && c<='Z')c+=32;h=((h^c)*0x01000193UL)&0xFFFFFFFFUL;}
    return h;
}
static int load(void) {
    FILE *f=NULL;long size,bytes;unsigned char head[AW_TALK_HEADER];
    if(pack_state)return pack_state>0;
    pack_state=-1;
    size=COM_FOpenFile("talk.awt",&f);
    if(size<AW_TALK_HEADER || !f){if(f)fclose(f);Con_DPrintf("Talk pack: not in this build\n");return 0;}
    if(fread(head,1,AW_TALK_HEADER,f)!=AW_TALK_HEADER || memcmp(head,"AWTP",4) || u16(head+4)!=1){
        fclose(f);Con_Printf("Talk pack: not AWTP 1\n");return 0;}
    head_count=(long)u16(head+6);record_count=(long)u32(head+8);head_bytes=(long)u32(head+12);head_bone=(int)u16(head+16);
    bytes=8*record_count+8*head_count;
    if(head_count<1 || record_count<1 || head_bone>=AW_SKEL_MAX_BONES || size!=AW_TALK_HEADER+bytes+head_bytes){
        fclose(f);Con_Printf("Talk pack: damaged\n");return 0;}
    if(!(table=(unsigned char *)AW_TryMalloc((size_t)bytes))){
        fclose(f);Con_Printf("Talk pack: no memory for %ld bytes\n",bytes);return 0;}
    if(fread(table,1,(size_t)bytes,f)!=(size_t)bytes){fclose(f);free(table);table=NULL;Con_Printf("Talk pack: damaged\n");return 0;}
    fclose(f);
    data_at=AW_TALK_HEADER+bytes;
    pack_state=1;
    return 1;
}
/* the head of a record id in the pack, or -1 */
int AW_TalkHeadOfId(const char *id) {
    unsigned long h;long lo=0,hi;
    if(!aw_talk_skeletal.value || !id || !*id || !load())return -1;
    h=AW_TalkHash(id);hi=record_count-1;
    while(lo<=hi){
        long mid=(lo+hi)/2;unsigned long v=u32(table+8*mid);
        if(v<h)lo=mid+1;else if(v>h)hi=mid-1;else return (int)u16(table+8*mid+4);
    }
    return -1;
}
/* aw_speech.c's question at a voice line's start: 1 and HEAD when ENTITY is an NPC with a skeletal model and a head
 * in the pack */
int AW_TalkTalker(int entity,int *head) {
    const char *id;
    if(!aw_talk_skeletal.value || !aw_talk_record || !(id=aw_talk_record(entity)))return 0;
    return (*head=AW_TalkHeadOfId(id))>=0;
}
static talk_head_t *head_of(int head) {
    int i,slot=0,n;FILE *f=NULL;long off;talk_head_t *t;
    for(i=0;i<AW_TALK_HEADS;i++){
        if(heads[i].used && heads[i].head==head){heads[i].used=++clock_;return &heads[i];}
        if(heads[i].used<heads[slot].used)slot=i;
    }
    if(pack_state<=0 || head<0 || head>=head_count)return NULL;
    off=(long)u32(table+8*record_count+8*head);n=(int)u16(table+8*record_count+8*head+4);
    if(n<1 || n>AW_TALK_REGION || off+(long)n*AW_TALK_VERT>head_bytes)return NULL;
    if(COM_FOpenFile("talk.awt",&f)<0 || !f)return NULL;
    t=&heads[slot];t->used=0;
    if(fseek(f,data_at+off,SEEK_CUR) || fread(t->rows,AW_TALK_VERT,(size_t)n,f)!=(size_t)n){fclose(f);return NULL;}
    fclose(f);
    t->head=head;t->n=n;t->used=++clock_;head_reads++;
    return t;
}
/* A model's talking vertices for HEAD (see the top): kept per model, header and head; NULL when nothing talks. */
static const talk_model_t *transfer(const void *model,const void *hdr,int head,const unsigned char *verts,int nv,
                                    float rest_scale) {
    int i,slot=0,v,j,k,l;talk_model_t *m;const talk_head_t *t;float lo[3],hi[3];double t0;
    for(i=0;i<AW_TALK_MODELS;i++){
        if(models[i].used && models[i].model==model && models[i].hdr==hdr && models[i].head==head){
            models[i].used=++clock_;return models[i].n?&models[i]:NULL;}
        if(models[i].used<models[slot].used)slot=i;
    }
    if(!(t=head_of(head)))return NULL;
    t0=aw_talk_clock?aw_talk_clock():0;
    for(k=0;k<3;k++){lo[k]=1e9f;hi[k]=-1e9f;}
    for(j=0;j<t->n;j++)for(k=0;k<3;k++){
        region[j][k]=(float)s16(t->rows[j]+2*k)/256.0f;
        if(region[j][k]-AW_TALK_AROUND<lo[k])lo[k]=region[j][k]-AW_TALK_AROUND;
        if(region[j][k]+AW_TALK_AROUND>hi[k])hi[k]=region[j][k]+AW_TALK_AROUND;
    }
    m=&models[slot];m->model=model;m->hdr=hdr;m->head=head;m->n=0;m->used=++clock_;
    for(v=0;v<nv && m->n<AW_TALK_MAX;v++){
        const unsigned char *p=verts+(long)v*AW_SKEL_VERT_BYTES;float in[3],sum=0,acc[3][3],big=0;
        if(p[0]!=head_bone || (p[1]!=AW_SKEL_NONE && p[2]))continue;
        for(k=0;k<3;k++)in[k]=(float)s16(p+4+2*k)*rest_scale;
        if(in[0]<lo[0] || in[0]>hi[0] || in[1]<lo[1] || in[1]>hi[1] || in[2]<lo[2] || in[2]>hi[2])continue;
        memset(acc,0,sizeof(acc));
        for(j=0;j<t->n;j++){
            float d[3],d2,w;
            for(k=0;k<3;k++)d[k]=region[j][k]-in[k];
            d2=d[0]*d[0]+d[1]*d[1]+d[2]*d[2];
            if(d2>AW_TALK_AROUND*AW_TALK_AROUND)continue;
            w=1.0f/(d2+1e-4f);sum+=w;
            for(l=0;l<3;l++)for(k=0;k<3;k++)acc[l][k]+=w*(float)(signed char)t->rows[j][6+3*l+k];
        }
        if(sum<=0)continue;
        for(l=0;l<3;l++)for(k=0;k<3;k++){
            acc[l][k]/=sum*32.0f;		/* the pack's offsets are 1/32 units (tools/talk_pack.py OFFSET_UNITS) */
            if(acc[l][k]>big)big=acc[l][k];
            if(-acc[l][k]>big)big=-acc[l][k];
        }
        if(big<0.01f)continue;
        m->index[m->n]=(unsigned short)v;
        for(l=0;l<3;l++)for(k=0;k<3;k++)m->off[m->n][l][k]=(short)(acc[l][k]*AW_TALK_OFF_UNITS);
        m->n++;
    }
    transfers++;
    if(aw_talk_clock){transfer_ms_last=(aw_talk_clock()-t0)*1000.0;if(transfer_ms_last>transfer_ms_max)transfer_ms_max=transfer_ms_last;}
    return m->n?m:NULL;
}
/* r_alias.c R_AliasSkelFrame, before the pose cache: ENTITY's talk level now (1..3), 0 when its mouth is shut */
int AW_TalkLevel(int entity) {
    int head=-1,level;
    if(!aw_talk_skeletal.value || (level=AW_SpeechLevel(entity,&head))<=0 || head<0)return 0;
    return level>3?3:level;
}
/* r_alias.c R_AliasSkelFrame, after AW_SkelPoseVerts posed the model into OUT with WORLD: its talking vertices posed
 * again with the level's offsets (the same bone matrix, origin, step and rounding). Returns the vertices moved. */
int AW_TalkApply(int entity,const void *model,const void *hdr,const aw_skel_block_t *block,const float world[][3][4],
                 unsigned char *out) {
    int head=-1,level,i,k;const talk_model_t *m;float inv[3],unit=1.0f/AW_TALK_OFF_UNITS;
    if(!aw_talk_skeletal.value || (level=AW_SpeechLevel(entity,&head))<=0 || head<0)return 0;
    if(level>3)level=3;
    if(!(m=transfer(model,hdr,head,block->data,block->verts,block->rest_scale)))return 0;
    for(k=0;k<3;k++)inv[k]=1.0f/block->pose_step[k];
    for(i=0;i<m->n;i++){
        const unsigned char *p=block->data+(long)m->index[i]*AW_SKEL_VERT_BYTES;
        const float (*b)[4]=world[p[0]];
        const short *o=m->off[i][level-1];
        unsigned char *q=out+4*(long)m->index[i];
        float in[3];
        for(k=0;k<3;k++)in[k]=(float)s16(p+4+2*k)*block->rest_scale+o[k]*unit;
        for(k=0;k<3;k++)
            q[k]=(unsigned char)byte_of((b[k][0]*in[0]+b[k][1]*in[1]+b[k][2]*in[2]+b[k][3]-block->pose_origin[k])*inv[k]);
    }
    poses++;
    return m->n;
}
/* r_alias.c's hooks (R_AliasTalkLevel, R_AliasTalkApply; set in aw_debug.c): the client entity drawn, by its number
 * (the speech tracks' entity numbers are the client's: snd_dma.c S_StartSound) */
static int number_of(const entity_t *e) {
    return e && e>=cl_entities && e<cl_entities+MAX_EDICTS?(int)(e-cl_entities):0;
}
int AW_TalkLevelOf(const entity_t *e) {
    int n=number_of(e);
    return n>0?AW_TalkLevel(n):0;
}
int AW_TalkApplyOf(const entity_t *e,const void *hdr,const aw_skel_block_t *block,const float world[][3][4],
                   unsigned char *out) {
    int n=number_of(e);
    return n>0?AW_TalkApply(n,e->model,hdr,block,world,out):0;
}
/* dbg speech: the pack's state, its counts and the memory it holds */
void AW_TalkStatus(void) {
    Con_Printf("Talk pack: %s; %ld records, %ld heads, head bone %d; %lu heads read, %lu model lists made (the last took "
               "%.1f ms, the longest %.1f ms), %lu talking poses; aw_talk_skeletal %d; %ld bytes held\n",
               pack_state>0?"read":pack_state<0?"none":"not read yet",record_count,head_count,head_bone,head_reads,
               transfers,transfer_ms_last,transfer_ms_max,poses,(int)aw_talk_skeletal.value,
               (long)(pack_state>0?8*(record_count+head_count):0)+(long)sizeof(heads)+(long)sizeof(models)+
               (long)sizeof(region));
}
