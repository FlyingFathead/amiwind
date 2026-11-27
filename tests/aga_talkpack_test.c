/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_talkpack.c (NPC-TALK-MOUTH-STILL-69): a skeletal NPC's mouth from the talk pack. A pack written here (one head:
 * two original vertices the Talk morph moves down x, one still anchor), a skeletal block with a vertex on a moving
 * one, one between the two, one on the still anchor, one far away and one on another bone: the record's head is
 * found by its id (any case), the talker hook answers, and the posed bytes of the talking vertices move by the
 * level's offsets through the bone's matrix while the others keep AW_SkelPoseVerts' bytes. Before: no skeletal
 * actor's vertex ever moved with a voice line. */
#include "quakedef.h"
#include "aw_skel.h"
#include <assert.h>
client_state_t cl;entity_t cl_entities[MAX_EDICTS];
static unsigned char pack[20+8*2+8*1+16*3];
static int pack_size,opens;
int COM_FOpenFile(char *s,FILE **f){
    if(strcmp(s,"talk.awt")){*f=NULL;return -1;}
    opens++;*f=tmpfile();assert(*f);fwrite(pack,1,pack_size,*f);rewind(*f);return pack_size;
}
void Con_Printf(char *fmt,...){(void)fmt;}
void Con_DPrintf(char *fmt,...){(void)fmt;}
static int level_now=2,head_now=0;
int AW_SpeechLevel(int entity,int *head){(void)entity;*head=head_now;return level_now;}
extern cvar_t aw_talk_skeletal;
extern const char *(*aw_talk_record)(int entity);
unsigned long AW_TalkHash(const char *id);
int AW_TalkHeadOfId(const char *id);
int AW_TalkTalker(int entity,int *head);
int AW_TalkLevel(int entity);
int AW_TalkApply(int entity,const void *model,const void *hdr,const aw_skel_block_t *block,const float world[][3][4],
                 unsigned char *out);
static void be16(unsigned char *p,unsigned v){p[0]=(unsigned char)(v>>8);p[1]=(unsigned char)v;}
static void be32(unsigned char *p,unsigned long v){be16(p,(unsigned)(v>>16));be16(p+2,(unsigned)(v&65535));}
/* a pack row: position x 256, the x offset DX x (level) in 1/32 units */
static void row(unsigned char *p,float x,float y,float z,int dx){
    int l;be16(p,(unsigned)(unsigned short)(short)(x*256));be16(p+2,(unsigned)(unsigned short)(short)(y*256));
    be16(p+4,(unsigned)(unsigned short)(short)(z*256));
    for(l=0;l<3;l++){p[6+3*l]=(unsigned char)(signed char)(dx*(l+1));p[7+3*l]=0;p[8+3*l]=0;}p[15]=0;
}
static void vert(unsigned char *p,int bone,float x,float y,float z,float rest_scale){
    memset(p,0,AW_SKEL_VERT_BYTES);p[0]=(unsigned char)bone;p[1]=AW_SKEL_NONE;
    be16(p+4,(unsigned)(unsigned short)(short)(x/rest_scale));be16(p+6,(unsigned)(unsigned short)(short)(y/rest_scale));
    be16(p+8,(unsigned)(unsigned short)(short)(z/rest_scale));
}
static const char *record_of(int entity){return entity==7?"Fargoth":NULL;}
static unsigned char expect(float v){return (unsigned char)((v+8.0f)*16.0f+0.5f);}
int main(void){
    unsigned char *p=pack,verts[5*AW_SKEL_VERT_BYTES],out[5*4];static float world[AW_SKEL_MAX_BONES][3][4];
    aw_skel_block_t block;int i,k,head=-1;unsigned long h1=AW_TalkHash("Fargoth"),h2=AW_TalkHash("chargen class");
    /* tools/talk_pack.py fnv1a: FNV-1a 32, ASCII letters lowered */
    assert(AW_TalkHash("")==0x811C9DC5UL && AW_TalkHash("a")==0xE40C292CUL && h1==AW_TalkHash("fargoth"));
    /* the header, two records sorted by hash (both on head 0, the tables' head bone 4), one head of three rows */
    memcpy(p,"AWTP",4);be16(p+4,1);be16(p+6,1);be32(p+8,2);be32(p+12,16*3);be16(p+16,4);be16(p+18,0);p+=20;
    be32(p,h1<h2?h1:h2);be16(p+4,0);be16(p+6,0);be32(p+8,h1<h2?h2:h1);be16(p+12,0);be16(p+14,0);p+=16;
    be32(p,0);be16(p+4,3);be16(p+6,0);p+=8;
    row(p,0.0f,1.0f,2.0f,-16);row(p+16,0.0f,1.25f,2.0f,-16);row(p+32,0.0f,1.0f,2.75f,0);p+=48;
    pack_size=(int)(p-pack);
    assert(AW_TalkHeadOfId("Fargoth")==0 && AW_TalkHeadOfId("CHARGEN CLASS")==0 && AW_TalkHeadOfId("nobody")==-1);
    /* the talker hook: only an entity whose record the renderer side names (a skeletal model's) */
    assert(!AW_TalkTalker(7,&head));
    aw_talk_record=record_of;assert(AW_TalkTalker(7,&head) && head==0);assert(!AW_TalkTalker(8,&head));
    /* the model: on a moving vertex, between the two moving ones, on the still anchor, far away, another bone */
    vert(verts,4,0.0f,1.0f,2.0f,0.001f);vert(verts+16,4,0.0f,1.125f,2.0f,0.001f);vert(verts+32,4,0.0f,1.0f,2.75f,0.001f);
    vert(verts+48,4,0.0f,9.0f,9.0f,0.001f);vert(verts+64,3,0.0f,1.0f,2.0f,0.001f);
    memset(&block,0,sizeof(block));block.verts=5;block.rest_scale=0.001f;block.data=verts;
    for(k=0;k<3;k++){block.pose_origin[k]=-8.0f;block.pose_step[k]=1.0f/16;}
    for(i=0;i<AW_SKEL_MAX_BONES;i++)for(k=0;k<3;k++)world[i][k][k]=1.0f;   /* the rest pose: identity matrices */
    assert(AW_TalkLevel(7)==2);
    memset(out,0x55,sizeof(out));
    assert(AW_TalkApply(7,(void *)1,(void *)2,&block,(const float (*)[3][4])world,out)==2);
    /* level 2 of the moving vertex: x = 0 - 2 x 16/32 = -1 */
    assert(out[0]==expect(-1.0f) && out[1]==expect(1.0f) && out[2]==expect(2.0f));
    /* between the two moving ones: the same offset (the still anchor 0.76 away weighs about 1 %) */
    assert(out[4]==expect(-1.0f));
    /* the still anchor, the far vertex and the other bone: not posed again (AW_SkelPoseVerts' bytes stay) */
    assert(out[8]==0x55 && out[12]==0x55 && out[16]==0x55);
    /* level 0 (shut) or aw_talk_skeletal 0: nothing moves */
    level_now=0;assert(!AW_TalkLevel(7));memset(out,0x55,sizeof(out));
    assert(!AW_TalkApply(7,(void *)1,(void *)2,&block,(const float (*)[3][4])world,out) && out[0]==0x55);
    level_now=3;aw_talk_skeletal.value=0;assert(!AW_TalkLevel(7));
    assert(!AW_TalkApply(7,(void *)1,(void *)2,&block,(const float (*)[3][4])world,out) && out[0]==0x55);
    aw_talk_skeletal.value=1;
    /* the model's list is kept: a second pose reads the pack no more; level 3 opens further (x - 1.5) */
    k=opens;assert(AW_TalkApply(7,(void *)1,(void *)2,&block,(const float (*)[3][4])world,out)==2 && opens==k);
    assert(out[0]==expect(-1.5f));
    /* the bone's matrix carries the offset: the head bone turned a quarter round z moves the mouth along y */
    memset(world[4],0,sizeof(world[4]));world[4][0][1]=-1.0f;world[4][1][0]=1.0f;world[4][2][2]=1.0f;
    assert(AW_TalkApply(7,(void *)1,(void *)2,&block,(const float (*)[3][4])world,out)==2);
    assert(out[0]==expect(-1.0f) && out[1]==expect(-1.5f) && out[2]==expect(2.0f));
    /* another head for the same model is its own list; an unknown head none */
    head_now=5;assert(!AW_TalkApply(7,(void *)1,(void *)2,&block,(const float (*)[3][4])world,out));
    return 0;
}
