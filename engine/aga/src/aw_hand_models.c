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
int AW_HandStance(int weapon) {
    /* weapon = 1 + the WEAP type: short blade 0, long blade 1, blunt 3 and axe 7 are one-handed; long blade 2,
     * blunt 4 and axe 8 two-handed close; blunt 5 and spear 6 two-handed wide (the original's idle1h/idle2c/idle2w). */
    switch(weapon){
    case 1:case 2:case 4:case 8:return 0;
    case 3:case 5:case 9:return 1;
    case 6:case 7:return 2;
    /* FIRST-PERSON-WEAPONS-56: bow 9, crossbow 10, thrown 11 (bowandarrow, crossbow, throwweapon over idle1h and
     * idlecrossbow, as the original's first-person file has them) */
    case 10:return 3;
    case 11:return 4;
    case 12:return 5;
    }
    return -1;
}
int AW_HandWeaponsDecode(aw_hand_weapons_t *out,const unsigned char *raw,int size) {
    aw_hand_weapons_t t;int s,f,j;const unsigned char *p;
    if(!out)return 0;
    memset(out,0,sizeof(*out));memset(&t,0,sizeof(t));
    if(!raw || size<8 || memcmp(raw,"AWW1",4) || raw[4] || raw[6] || raw[7]!=AW_HAND_WEAPON_FRAMES)return 0;
    t.stances=raw[5];
    if(t.stances<1 || t.stances>AW_HAND_STANCES || size!=8+t.stances*AW_HAND_WEAPON_FRAMES*24)return 0;
    for(s=0;s<t.stances;s++)for(f=0;f<AW_HAND_WEAPON_FRAMES;f++){
        p=raw+8+(s*AW_HAND_WEAPON_FRAMES+f)*24;
        for(j=0;j<6;j++){
            t.tag[s][f][j]=(float)(int)block_u32(p+j*4)/65536.0f;
            if(fabs(t.tag[s][f][j])>(j<3?128.0f:720.0f))return 0;
        }
    }
    *out=t;return 1;
}
int AW_HandItemPath(const char *s) {
    int i,n=0,prefix;
    if(!s)return 0;
    while(n<64 && s[n])n++;
    prefix=!strncmp(s,"progs/inv/",10)?10:!strncmp(s,"progs/items/",12)?12:0;
    if(!prefix || n<prefix+5 || n>=64 || strstr(s,"..") || strcmp(s+n-4,".mdl"))return 0;
    for(i=0;i<n;i++)if(!((s[i]>='a' && s[i]<='z') || (s[i]>='0' && s[i]<='9') || s[i]=='_' || s[i]=='/' || s[i]=='.'))return 0;
    return 1;
}

#ifndef AW_BLOCK_HOST_TEST
#include "quakedef.h"
#include "aw_character.h"
#include "aw_hand_models.h"
#include "aw_torch.h"
#include "aw_combat.h"
static void block_reset(void);
static void weapon_reset(void);
static int probe_frames(const char *,int);

#define MAX_HAND_APPEARANCES 32
#define HAND_RECORD_BYTES 196
typedef struct {char race[64],hand[64],torch[64];int female;} hand_appearance_t;
static hand_appearance_t appearances[MAX_HAND_APPEARANCES];
static int appearance_count,selected=-2,pair_valid;
static model_t *hand_model,*torch_model;

/* HELD-LIGHT-OWN-MODEL-61: a held candle, candlestick or lantern in first person: the arms from parts at the light
 * stance (the bare hands with the left arm on the torch group) and the light's own item model on their shield bone */
static model_t *light_model,*light_base;
static char light_path[64];
static int light_bad,light_visible,light_said,light_pose_frame=-1;
static float light_pose[6];
static void light_reset(void){light_model=light_base=NULL;light_path[0]=0;light_bad=light_visible=0;light_pose_frame=-1;}
void AW_HandModelsReset(void)
{
    selected=-2;pair_valid=0;hand_model=torch_model=NULL;AW_TorchUseHandAssets(0);
    block_reset();weapon_reset();light_reset();
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
/* The equipped shield's model: the inventory's own (progs/inv/) or, since the item model table
 * (ITEM-WORLD-MODELS-58), the one shared model of its mesh (progs/items/). */
static int block_equipment_path(const char *s) {return AW_HandItemPath(s);}
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
/* First-person weapons (aw_hand_models.h): the stance arms of the selected appearance and the equipped weapon's own
 * model, both loaded only while that weapon is equipped; a missing or invalid file falls back to the bare hands once,
 * with one console line. */
int (*aw_hand_weapon_item)(int *weapon,char model[64]);
/* The first-person arms from parts (aw_view.c hand_parts_apply, PLAYER-GEAR-VISUAL-59): NULL in fixtures without it. */
int (*aw_hand_parts_apply)(const char *race,int female,int stance,int frame);
static aw_hand_weapons_t weapon_data;
static model_t *stance_model,*weapon_model;
/* the view model the weapon rides this frame (the stance arms, or the first part of the arms from parts) and the
 * first frame of its stance (0 for the stance arms; the stance's row of the first-person table for the parts) */
static model_t *weapon_base;
static int weapon_frame_base;
static int weapon_loaded,weapon_bad,weapon_visible,weapon_stance=-1;
static int weapon_arms=-1;    /* the stance arms' file: -1 not probed yet, 0 missing, 1 there */
static char stance_path[64],weapon_path[64];
static void weapon_reset(void) {
    weapon_loaded=weapon_bad=weapon_visible=0;weapon_stance=weapon_arms=-1;stance_model=weapon_model=weapon_base=NULL;
    stance_path[0]=weapon_path[0]=0;weapon_frame_base=0;
}
/* WITH_ARMS 1: the stance arms of the appearance and the weapon (the baked arms); 0: the weapon alone (the arms from
 * parts pose the stance themselves). 1 = the weapon is shown. */
static int hand_weapon(int index,int with_arms) {
    /* the ranged stances have no baked arms (the arms from parts pose them): their files are absent, the bare hands */
    static const char *suffix[AW_HAND_STANCES]={"_1h.mdl","_2c.mdl","_2w.mdl","_bw.mdl","_xb.mdl","_1t.mdl"};
    char path[64]={0},arms[64];int weapon=0,stance,n,mark;byte *raw;
    weapon_visible=0;
    if(!aw_hand_weapon_item || !aw_hand_weapon_item(&weapon,path) || !memchr(path,0,sizeof(path)) ||
       (stance=AW_HandStance(weapon))<0 || !AW_HandItemPath(path))return 0;
    if(!weapon_loaded){
        weapon_loaded=1;mark=Hunk_LowMark();raw=COM_LoadHunkFile("gfx/hand-weapons.aww");
        if(!AW_HandWeaponsDecode(&weapon_data,raw,com_filesize)){
            weapon_data.stances=0;Con_Printf("First-person weapon assets unavailable; showing the bare hands.\n");
        }
        Hunk_FreeToLowMark(mark);
    }
    if(stance>=weapon_data.stances)return 0;
    n=(int)strlen(appearances[index].hand);
    if(n<5 || n-4+7>=(int)sizeof(arms))return 0;
    memcpy(arms,appearances[index].hand,n-4);strcpy(arms+n-4,suffix[stance]);
    if(stance!=weapon_stance || strcmp(arms,stance_path) || strcmp(path,weapon_path)){
        if(stance_model && stance_path[0])release_owned(stance_model,stance_path);
        weapon_stance=stance;strcpy(stance_path,arms);strcpy(weapon_path,path);stance_model=weapon_model=NULL;
        weapon_arms=-1;                       /* the stance arms' file: probed when first wanted */
        weapon_bad=!probe_frames(path,1);
        if(weapon_bad)Con_Printf("First-person arms or the equipped weapon's model unavailable; showing the bare hands.\n");
    }
    if(weapon_bad)return 0;
    if(with_arms && weapon_arms<0){
        weapon_arms=probe_frames(arms,AW_HAND_WEAPON_FRAMES);
        if(!weapon_arms)Con_Printf("First-person arms or the equipped weapon's model unavailable; showing the bare hands.\n");
    }
    if(with_arms && !weapon_arms)return 0;
    if(with_arms && !stance_model){
        if(!Mod_CanFindName(arms)){weapon_bad=1;Con_Printf("First-person weapon model slots unavailable; showing the bare hands.\n");return 0;}
        stance_model=Mod_ForName(arms,false);
    }
    if(!weapon_model){
        if(!Mod_CanFindName(path)){weapon_bad=1;Con_Printf("First-person weapon model slots unavailable; showing the bare hands.\n");return 0;}
        weapon_model=Mod_ForName(path,false);
    }
    if((with_arms && (!stance_model || stance_model->type!=mod_alias || stance_model->numframes!=AW_HAND_WEAPON_FRAMES ||
                      strcmp(stance_model->name,arms))) ||
       !weapon_model || weapon_model->type!=mod_alias || weapon_model->numframes!=1 || strcmp(weapon_model->name,path)){
        weapon_bad=1;Con_Printf("Invalid first-person weapon model; showing the bare hands.\n");return 0;
    }
    weapon_visible=1;return 1;
}
int AW_HandWeaponItemApply(void) {
    float origin[3],angles[3];int frame=cl.viewent.frame-weapon_frame_base;
    if(!weapon_visible || !weapon_model || weapon_stance<0 || weapon_stance>=weapon_data.stances || !weapon_base ||
       cl.viewent.model!=weapon_base)return 0;
    if(frame<0)frame=0;
    if(frame>=AW_HAND_WEAPON_FRAMES)frame=AW_HAND_WEAPON_FRAMES-1;
    AW_BlockCompose(cl.viewent.origin,cl.viewent.angles,weapon_data.tag[weapon_stance][frame],origin,angles);
    cl.viewent.model=weapon_model;cl.viewent.frame=0;
    VectorCopy(origin,cl.viewent.origin);VectorCopy(angles,cl.viewent.angles);return 1;
}
/* aw_view.c: the arms from parts' shield bone this frame as a tag in the view model's space; 0 none */
int (*aw_hand_parts_shield_tag)(float tag[6]);
static model_t *held_light_model(const char *path)
{
    if(strcmp(path,light_path)){
        Q_strncpy(light_path,(char *)path,63);light_path[63]=0;light_model=NULL;
        light_bad=!AW_HandItemPath(path) || !probe_frames(path,1);
        if(light_bad)Con_Printf("First-person held light: model %s unavailable; not drawn.\n",path);
    }
    if(light_bad)return NULL;
    if(!light_model){
        if(!Mod_CanFindName(light_path)){light_bad=1;Con_Printf("First-person held light: no model slot; not drawn.\n");return NULL;}
        light_model=Mod_ForName(light_path,false);
    }
    if(!light_model || light_model->type!=mod_alias || light_model->numframes!=1 || strcmp(light_model->name,light_path)){
        light_bad=1;light_model=NULL;Con_Printf("First-person held light: invalid model %s; not drawn.\n",light_path);return NULL;
    }
    return light_model;
}
int AW_HandLightItemApply(void) {
    extern int r_framecount;
    const aw_held_light_t *l;float tag[6],origin[3],angles[3];model_t *m;
    if(!light_visible || !light_base || cl.viewent.model!=light_base || !(l=AW_HeldLight()) ||
       !aw_hand_parts_shield_tag || !aw_hand_parts_shield_tag(tag) || !(m=held_light_model(l->model)))return 0;
    /* the view model's place, then the shield bone, then the light's own carried-light place on it */
    AW_BlockCompose(cl.viewent.origin,cl.viewent.angles,tag,origin,angles);
    AW_BlockCompose(origin,angles,l->offset,light_pose,light_pose+3);
    /* forward by the torch arms' own view offset (tools/prepare_torch.py VIEW_OFFSET, 4 units: the whole held torch is
     * moved forward so it does not crowd the camera), so a candle or lantern sits where the torch's hand does */
    {
        vec3_t a,forward,right,up;int i;
        VectorCopy(cl.viewent.angles,a);a[PITCH]=-a[PITCH];AngleVectors(a,forward,right,up);
        for(i=0;i<3;i++)light_pose[i]+=AW_HAND_LIGHT_FORWARD*forward[i];
    }
    light_pose_frame=r_framecount;
    cl.viewent.model=m;cl.viewent.frame=0;
    memcpy(cl.viewent.origin,light_pose,3*sizeof(float));memcpy(cl.viewent.angles,light_pose+3,3*sizeof(float));return 1;
}
/* aw_torch.h aw_hand_held_light: the place the light was drawn at this frame (its flames follow it) */
static int hand_held_light(float origin[3],float angles[3]) {
    extern int r_framecount;
    if(!light_visible || light_pose_frame!=r_framecount)return 0;
    memcpy(origin,light_pose,3*sizeof(float));memcpy(angles,light_pose+3,3*sizeof(float));return 1;
}
int AW_HandModelsApply(void)
{
#if !AMIWIND_SPRITE_HANDS
    const char *race="nord",*path;int female=0,index=-1,i,equipped,frames;
    model_t **wanted,*base=cl.viewent.model;
    aw_hand_held_light=hand_held_light;light_visible=0;
    weapon_visible=0;weapon_base=NULL;weapon_frame_base=0;
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
        if(stance_model && stance_path[0])release_owned(stance_model,stance_path);
        weapon_stance=-1;stance_model=weapon_model=NULL;stance_path[0]=weapon_path[0]=0;weapon_bad=0;
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
    light_visible=0;
    if(!equipped && AW_HeldLight()){
        /* a held light of its own (HELD-LIGHT-OWN-MODEL-61): the arms from parts at the light stance, the bare hands'
         * frame (the right hand keeps its fist and punch); the light rides their shield bone (AW_HandLightItemApply) */
        if(aw_hand_parts_apply && aw_hand_parts_apply(race,female,AW_HAND_LIGHT_STANCE,cl.viewent.frame)){
            light_visible=1;light_base=cl.viewent.model;
            AW_TorchUseHandAssets(1);release_owned(base,"progs/v_nord.mdl");AW_TorchReleaseLegacyCache();
            return 1;
        }
        if(!light_said){
            light_said=1;
            Con_Printf("First-person held light: no light stance in the arms from parts (aw_hand_parts 0 or an older "
                       "image); the bare hands are shown.\n");
        }
    }
    /* The arms from parts (PLAYER-GEAR-VISUAL-59, aw_view.c): what the hands wear, at the stance of the drawn weapon
     * (the weapon alone loads here: the parts pose the stance). Unavailable or aw_hand_parts 0: the baked arms below,
     * the previous method. The carried torch keeps its baked arms. */
    if(!equipped && aw_hand_parts_apply){
        int armed=hand_weapon(index,0),stance=armed?weapon_stance+1:0,frame=cl.viewent.frame;
        if(aw_hand_parts_apply(race,female,stance,frame)){
            if(armed){weapon_base=cl.viewent.model;weapon_frame_base=stance*AW_HAND_WEAPON_FRAMES;}
            AW_TorchUseHandAssets(1);release_owned(base,"progs/v_nord.mdl");AW_TorchReleaseLegacyCache();
            return 1;
        }
        weapon_visible=0;
    }
    if(!equipped && hand_weapon(index,1)){
        cl.viewent.model=stance_model;weapon_base=stance_model;AW_TorchUseHandAssets(1);
        release_owned(base,"progs/v_nord.mdl");AW_TorchReleaseLegacyCache();
        return 1;
    }
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
