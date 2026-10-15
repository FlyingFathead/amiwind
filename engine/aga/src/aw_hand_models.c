/* SPDX-License-Identifier: GPL-2.0-or-later
 * Optional owned race/sex viewmodels. Keep the server's animation/frame
 * contract and legacy Nord payload; only the local appearance is selected. */
#include <math.h>
#include <string.h>
#include "aw_hand_models.h"

/* Existing AmiQuake mathlib routines: no hot-path 68881 library trig. */
void Q_SinCosDeg(float degrees,float *s,float *c);
double Q_atan2(double y,double x);

static unsigned long block_u32(const unsigned char *p) {
    return ((unsigned long)p[0]<<24)|((unsigned long)p[1]<<16)|((unsigned long)p[2]<<8)|p[3];
}
static int block_string(char *out,const unsigned char *p,int model) {
    int i,end=-1;
    for(i=0;i<64;i++){
        unsigned char c=p[i];
        if(!c){if(end<0)end=i;continue;}
        if(end>=0 || !((c>='a' && c<='z') || (c>='0' && c<='9') || c=='_' ||
           (!model && c==' ') || (model && (c=='/' || c=='.'))))return 0;
    }
    if(end<1)return 0;
    memcpy(out,p,64);
    if(model && (strncmp(out,"progs/hands/",12) || strstr(out,"..") || end<17 || strcmp(out+end-4,".mdl")))return 0;
    return 1;
}
int AW_BlockViewDecode(aw_block_view_t *out,const unsigned char *raw,int size) {
    aw_block_view_t t;int i,j;unsigned long duration,hit,ms;const unsigned char *p;
    if(!out)return 0;
    memset(out,0,sizeof(*out));memset(&t,0,sizeof(t));t.hold=-1;
    if(!raw || size<240 || memcmp(raw,"AWB1",4) || raw[4] || raw[6] || raw[7]!=132)return 0;
    t.count=raw[5];duration=block_u32(raw+8);hit=block_u32(raw+12);
    if(t.count<1 || t.count>AW_BLOCK_APPEARANCES || size!=240+t.count*132 ||
       duration<1 || duration>10000 || hit<1 || hit>=duration)return 0;
    t.duration=duration*.001f;t.hit=hit*.001f;
    for(i=0;i<AW_BLOCK_FRAMES;i++){
        p=raw+16+i*28;ms=block_u32(p);t.time[i]=ms*.001f;
        if(ms>duration || (i && t.time[i]<=t.time[i-1]) || (!i && ms) ||
           (i==AW_BLOCK_FRAMES-1 && ms!=duration))return 0;
        if(ms==hit)t.hold=i;
        for(j=0;j<6;j++){
            t.tag[i][j]=(float)(int)block_u32(p+4+j*4)/65536.0f;
            if(fabs(t.tag[i][j])>(j<3?128.0f:720.0f))return 0;
        }
    }
    if(t.hold<0)return 0;
    for(i=0;i<t.count;i++){
        aw_block_appearance_t *a=&t.appearance[i];p=raw+240+i*132;
        if(!block_string(a->race,p,0) || block_u32(p+64)>1 || !block_string(a->model,p+68,1))return 0;
        a->female=(int)block_u32(p+64);
        for(j=0;j<i;j++)if(a->female==t.appearance[j].female && !strcmp(a->race,t.appearance[j].race))return 0;
    }
    *out=t;return 1;
}
static int block_frame(const aw_block_view_t *a,float phase) {
    int i=0;
    while(i<AW_BLOCK_FRAMES-1 && phase>=(a->time[i]+a->time[i+1])*.5f)i++;
    return i;
}
int AW_BlockPlayback(const aw_block_view_t *a,aw_block_clock_t *c,int guarding,float left,float dt) {
    if(!a || !c || a->count<1 || a->hold<0 || a->hold>=AW_BLOCK_FRAMES)return -1;
    if(!(dt>=0))dt=0;
    if(dt>.25f)dt=.25f;
    if(guarding){
        if(c->mode!=1){c->mode=1;c->phase=0;}
        c->phase+=dt;if(c->phase>a->hit)c->phase=a->hit;
    }else if(left>0){
        c->mode=2;c->phase=a->duration-left;if(c->phase<a->hit)c->phase=a->hit;
    }else if(c->mode){c->mode=2;c->phase+=dt;}
    else return -1;
    if(c->phase>a->duration){memset(c,0,sizeof(*c));return -1;}
    return block_frame(a,c->phase);
}
static void block_basis(const float a[3],float b[3][3]) {
    float sp,cp,sy,cy,sr,cr;
    Q_SinCosDeg(a[0],&sp,&cp);Q_SinCosDeg(a[1],&sy,&cy);Q_SinCosDeg(a[2],&sr,&cr);
    b[0][0]=cp*cy;b[0][1]=cp*sy;b[0][2]=-sp;
    b[1][0]=sr*sp*cy-cr*sy;b[1][1]=sr*sp*sy+cr*cy;b[1][2]=sr*cp;
    b[2][0]=cr*sp*cy+sr*sy;b[2][1]=cr*sp*sy-sr*cy;b[2][2]=cr*cp;
}
void AW_BlockCompose(const float base_origin[3],const float base_angles[3],const float tag[6],float origin[3],float angles[3]) {
    float ba[3],b[3][3],l[3][3],m[3][3];double z,h,cy,sy;int i,j,k;
    ba[0]=-base_angles[0];ba[1]=base_angles[1];ba[2]=base_angles[2];
    block_basis(ba,b);block_basis(tag+3,l);
    for(j=0;j<3;j++){
        origin[j]=base_origin[j];for(k=0;k<3;k++)origin[j]+=tag[k]*b[k][j];
        for(i=0;i<3;i++){m[i][j]=0;for(k=0;k<3;k++)m[i][j]+=l[i][k]*b[k][j];}
    }
    /* The horizontal forward length retains near-pole information that a
     * float sin(pitch) rounds to +/-1. sqrt receives only a sum of squares. */
    z=m[0][2];h=sqrt((double)m[0][0]*m[0][0]+(double)m[0][1]*m[0][1]);
    angles[0]=(float)(Q_atan2(z,h)*57.29577951308232); /* Alias negates pitch. */
    if(h>0.000001){
        angles[1]=(float)(Q_atan2(m[0][1],m[0][0])*57.29577951308232);
        if(fabs(z)>.5){
            /* Near a pole derive the coupled roll from the stable right row.
             * Dividing its tiny Z terms would amplify float matrix error. */
            cy=m[0][0]/h;sy=m[0][1]/h;
            angles[2]=(float)(Q_atan2(-(m[1][0]*cy+m[1][1]*sy)/z,
                -m[1][0]*sy+m[1][1]*cy)*57.29577951308232);
        }else angles[2]=(float)(Q_atan2(m[1][2],m[2][2])*57.29577951308232);
    }else {angles[1]=(float)(Q_atan2(-m[1][0],m[1][1])*57.29577951308232);angles[2]=0;}
}

#ifndef AW_BLOCK_HOST_TEST
#include "quakedef.h"
#include "aw_character.h"
#include "aw_hand_models.h"
#include "aw_torch.h"
#include "aw_combat.h"
static void block_reset(void);
static int probe_frames(const char *,int);

#define MAX_HAND_APPEARANCES 32
#define HAND_RECORD_BYTES 196
typedef struct {char race[64],hand[64],torch[64];int female;} hand_appearance_t;
static hand_appearance_t appearances[MAX_HAND_APPEARANCES];
static int appearance_count,selected=-2,pair_valid;
static model_t *hand_model,*torch_model;

void AW_HandModelsReset(void)
{
    selected=-2;pair_valid=0;hand_model=torch_model=NULL;AW_TorchUseHandAssets(0);
    block_reset();
}

/* Optional first-person guard: the same alias renderer and depth as the hands,
 * with a source left-arm clip and the actual equipped shield as a second alias. */
int (*aw_hand_block_item)(char id[64],char model[64]);
static aw_block_view_t block_data;
static aw_block_clock_t block_clock;
static model_t *block_arms,*block_item;
static int block_loaded,block_index=-1,block_bad,block_visible,block_pose;
static char block_id[64],block_path[64];
static void block_reset(void) {
    block_loaded=block_bad=block_visible=0;block_index=-1;block_arms=block_item=NULL;
    block_id[0]=block_path[0]=0;memset(&block_clock,0,sizeof(block_clock));
}
static int block_equipment_path(const char *s) {
    int i,n=0;while(n<64 && s[n])n++;
    if(n<18 || n>=64 || strncmp(s,"progs/inv/",10) || strstr(s,"..") || strcmp(s+n-4,".mdl"))return 0;
    for(i=0;i<n;i++)if(!((s[i]>='a' && s[i]<='z') || (s[i]>='0' && s[i]<='9') || s[i]=='_' || s[i]=='/' || s[i]=='.'))return 0;
    return 1;
}
int AW_HandBlockApply(void) {
#if !AMIWIND_SPRITE_HANDS
    char id[64]={0},path[64]={0};const char *race="nord";int female=0,i,index=-1,mark;
    int guarding=AW_CombatGuarding();float left=AW_CombatBlockShown(),dt=(float)host_frametime;byte *raw;
    block_visible=0;
    if(AW_TorchEquipped() || !aw_hand_block_item || !cl.viewent.model ||
       !aw_hand_block_item(id,path) || !id[0] || !memchr(id,0,sizeof(id)) || !block_equipment_path(path)){
        memset(&block_clock,0,sizeof(block_clock));return 0;
    }
    if(!guarding && !(left>0) && !block_clock.mode)return 0;
    if(!block_loaded){
        block_loaded=1;mark=Hunk_LowMark();raw=COM_LoadHunkFile("gfx/block-models.awb");
        if(!AW_BlockViewDecode(&block_data,raw,com_filesize)){
            block_data.count=0;Con_Printf("First-person block assets unavailable; retaining the current view.\n");
        }
        Hunk_FreeToLowMark(mark);
    }
    if(!block_data.count)return 0;
    if(aw_character.valid){
        if(aw_character.race<0 || aw_character.race>=aw_race_count || aw_character.female<0 || aw_character.female>1)return 0;
        race=aw_races[aw_character.race].id;female=aw_character.female;
    }
    for(i=0;i<block_data.count;i++)if(block_data.appearance[i].female==female && !strcmp(race,block_data.appearance[i].race)){index=i;break;}
    if(index!=block_index || strcmp(id,block_id) || strcmp(path,block_path)){
        block_index=index;strcpy(block_id,id);strcpy(block_path,path);block_arms=block_item=NULL;block_bad=0;
        memset(&block_clock,0,sizeof(block_clock));
        if(index<0 || !probe_frames(block_data.appearance[index].model,AW_BLOCK_FRAMES) || !probe_frames(path,1))block_bad=1;
        if(block_bad)Con_Printf("First-person block appearance or equipped shield unavailable; retaining the current view.\n");
    }
    if(block_bad || index<0)return 0;
    if(!block_arms){
        if(!Mod_CanFindName(block_data.appearance[index].model)){
            block_bad=1;Con_Printf("First-person block model slots unavailable; retaining the current view.\n");return 0;
        }
        block_arms=Mod_ForName(block_data.appearance[index].model,false);
    }
    if(!block_item){
        /* Recheck after the arms have consumed a slot. Two independent probes
         * before either load do not reserve two model-name slots. */
        if(!Mod_CanFindName(path)){
            block_bad=1;Con_Printf("First-person shield model slots unavailable; retaining the current view.\n");return 0;
        }
        block_item=Mod_ForName(path,false);
    }
    if(!block_arms || !block_item || block_arms->type!=mod_alias || block_arms->numframes!=AW_BLOCK_FRAMES ||
       block_item->type!=mod_alias || block_item->numframes!=1 || strcmp(block_item->name,path) ||
       strcmp(block_arms->name,block_data.appearance[index].model)){
        block_bad=1;Con_Printf("Invalid first-person block model; retaining the current view.\n");return 0;
    }
    if(cl.paused || sv.paused || AW_ModalWorldFrozen())dt=0;
    block_pose=AW_BlockPlayback(&block_data,&block_clock,guarding,left,dt);
    if(block_pose<0)return 0;
    cl.viewent.model=block_arms;cl.viewent.frame=block_pose;
    AW_TorchUseHandAssets(0);block_visible=1;return 1;
#else
    return 0;
#endif
}
int AW_HandBlockItemApply(void) {
    float origin[3],angles[3];
    if(!block_visible || !block_item)return 0;
    AW_BlockCompose(cl.viewent.origin,cl.viewent.angles,block_data.tag[block_pose],origin,angles);
    cl.viewent.model=block_item;cl.viewent.frame=0;
    VectorCopy(origin,cl.viewent.origin);VectorCopy(angles,cl.viewent.angles);return 1;
}
static int string_field(char *out,const byte *raw,int path)
{
    int i,end=-1;
    for(i=0;i<64;i++){
        unsigned char c=raw[i];
        if(!c){if(end<0)end=i;continue;}
        if(end>=0)return 0;
        if(!((c>='a' && c<='z') || (c>='0' && c<='9') || c=='_' ||
             (!path && c==' ') || (path && (c=='/' || c=='.'))))return 0;
    }
    if(end<=0)return 0;
    memcpy(out,raw,64);
    if(path && (strncmp(out,"progs/hands/",12) || strstr(out,"..") ||
                end<16 || strcmp(out+end-4,".mdl")))return 0;
    return 1;
}
int AW_HandModelsDecode(const unsigned char *data,int size)
{
    int count,i,j;const byte *p;hand_appearance_t *a;
    appearance_count=0;AW_HandModelsReset();
    if(!data || size<8 || memcmp(data,"AWH1",4) || data[4] || data[6] || data[7]!=HAND_RECORD_BYTES)return 0;
    count=data[5];if(count<1 || count>MAX_HAND_APPEARANCES || size!=8+count*HAND_RECORD_BYTES)return 0;
    for(i=0;i<count;i++){
        p=data+8+i*HAND_RECORD_BYTES;a=&appearances[i];
        if(p[64]>1 || p[65] || p[66] || p[67] ||
           !string_field(a->race,p,0) || !string_field(a->hand,p+68,1) ||
           !string_field(a->torch,p+132,1) || !strcmp(a->hand,a->torch))return 0;
        a->female=p[64];
        for(j=0;j<i;j++)if(a->female==appearances[j].female && !strcmp(a->race,appearances[j].race))return 0;
    }
    appearance_count=count;return 1;
}
void AW_HandModelsLoad(void)
{
    byte *raw;extern int com_filesize;
    raw=COM_LoadHunkFile("gfx/hand-models.awh");
    if(!AW_HandModelsDecode(raw,com_filesize)){
        if(raw)Con_Printf("Invalid hand appearance catalogue; using legacy models.\n");
        return;
    }
    if(!AW_TorchLoadHandAssets()){
        appearance_count=0;
        Con_Printf("Hand torch metadata unavailable; using legacy models.\n");
    }
}
static void release_owned(model_t *model,const char *name)
{
    /* Mod_FindName can recycle unreferenced model_t slots after a map change.
     * Name/type are part of ownership, not just the retained pointer. */
    if(model && model!=cl.viewent.model && model->type==mod_alias &&
       !strcmp(model->name,name) && model->cache.data)Cache_Free(&model->cache);
}
static unsigned int little32(const byte *p)
{
    return (unsigned int)p[0]|((unsigned int)p[1]<<8)|
           ((unsigned int)p[2]<<16)|((unsigned int)p[3]<<24);
}
static int probe_frames(const char *name,int frames)
{
    FILE *file=NULL;byte header[84];int size,ok;
    /* Verify both advertised members without retaining either alias. Respect
     * PAK member length and initial file offset; never read another member. */
    size=COM_FOpenFile((char *)name,&file);
    if(!file)return 0;
    ok=size>=(int)sizeof(header) &&
       fread(header,1,sizeof(header),file)==sizeof(header) &&
       !memcmp(header,"IDPO",4) && little32(header+4)==6 &&
       little32(header+68)==(unsigned int)frames;
    fclose(file);return ok;
}
int AW_HandModelsApply(void)
{
#if !AMIWIND_SPRITE_HANDS
    const char *race="nord",*path;int female=0,index=-1,i,equipped,frames;
    model_t **wanted,*base=cl.viewent.model;
    AW_TorchUseHandAssets(0);
    if(!appearance_count || !base)return 0;
    /* Do not replace an actual weapon or other custom viewmodel. */
    if(strcmp(base->name,"progs/v_nord.mdl") && strcmp(base->name,"progs/v_torch.mdl"))return 0;
    if(aw_character.valid){
        if(aw_character.race<0 || aw_character.race>=aw_race_count ||
           aw_character.female<0 || aw_character.female>1)return 0;
        race=aw_races[aw_character.race].id;female=aw_character.female;
    }
    for(i=0;i<appearance_count;i++)if(appearances[i].female==female && !strcmp(appearances[i].race,race)){index=i;break;}
    if(index!=selected){
        if(selected>=0 && selected<appearance_count){
            release_owned(hand_model,appearances[selected].hand);
            release_owned(torch_model,appearances[selected].torch);
        }
        selected=index;hand_model=torch_model=NULL;pair_valid=0;
        if(index>=0){
            pair_valid=probe_frames(appearances[index].hand,28) &&
                       probe_frames(appearances[index].torch,8);
            if(!pair_valid)
                Con_Printf("Incomplete hand appearance for %s; using legacy models.\n",race);
        }
    }
    if(!pair_valid || index<0)return 0;
    equipped=AW_TorchEquipped();frames=equipped?8:28;
    path=equipped?appearances[index].torch:appearances[index].hand;
    wanted=equipped?&torch_model:&hand_model;
    if(*wanted && (strcmp((*wanted)->name,path) || (*wanted)->type!=mod_alias ||
                   (*wanted)->numframes!=frames))*wanted=NULL;
    if(!*wanted){
        if(!Mod_CanFindName(path)){
            pair_valid=0;Con_Printf("Hand model slots unavailable; using legacy models.\n");return 0;
        }
        *wanted=Mod_ForName((char *)path,false);
        if(!*wanted || strcmp((*wanted)->name,path) || (*wanted)->type!=mod_alias ||
           (*wanted)->numframes!=frames){
            *wanted=NULL;pair_valid=0;
            Con_Printf("Invalid hand appearance for %s; using legacy models.\n",race);return 0;
        }
    }
    /* Only the selected mode loads. A previously used mode stays ordinary
     * LRU-evictable cache, avoiding forced reloads on repeated equip toggles.
     * Mod_Extradata reloads the active payload if cache pressure evicts it. */
    cl.viewent.model=*wanted;AW_TorchUseHandAssets(1);
    if(equipped)cl.viewent.frame=AW_TorchFrame();
    release_owned(base,"progs/v_nord.mdl");
    AW_TorchReleaseLegacyCache();
    return 1;
#else
    return 0;
#endif
}
#endif /* !AW_BLOCK_HOST_TEST */
