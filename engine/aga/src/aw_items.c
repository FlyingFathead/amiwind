/* Carried items on a hand bone's per-frame tag (aw_items.h; tools/npc_items.py). */
#ifdef AW_ITEMS_HOST_TEST
#include <string.h>
float Q_SinRad(float radians);
float Q_CosRad(float radians);
#else
#include "quakedef.h"
#include "aw_anim.h"
#include "aw_skel.h"
#include "aw_torch.h"
#include "aw_weather.h"
#endif
#include "aw_items.h"
#include "aw_tryalloc.h"

/* A decimal number "-12.345" (the tag writer's %.3f); no library float parsing. */
static int number(const char **p,float *out) {
    const char *s=*p;float v=0,scale=1;int neg=0,digits=0;
    while(*s==' ')s++;
    if(*s=='-'){neg=1;s++;}
    while(*s>='0' && *s<='9'){v=v*10+(float)(*s-'0');s++;digits++;}
    if(*s=='.'){s++;while(*s>='0' && *s<='9'){scale*=.1f;v+=(float)(*s-'0')*scale;s++;digits++;}}
    if(!digits || v>100000.f)return 0;
    *out=neg?-v:v;*p=s;return 1;
}
static const char *line_end(const char *p) {while(*p && *p!='\n')p++;return p;}

/* The "weapon <path|->" and "shield <path|->" lines of both tag forms. */
static int item_paths(const char **pp,char paths[AW_ITEMS_KINDS][AW_ITEMS_PATH]) {
    static const char *const kind[AW_ITEMS_KINDS]={"weapon ","shield "};
    const char *p=*pp,*e;int i,k,n;
    for(k=0;k<AW_ITEMS_KINDS;k++){
        if(strncmp(p,kind[k],7))return 0;
        p+=7;e=line_end(p);n=(int)(e-p);if(n>0 && p[n-1]=='\r')n--;
        if(n<1 || n>=AW_ITEMS_PATH)return 0;
        if(n==1 && *p=='-')paths[k][0]=0;
        else{
            for(i=0;i<n;i++)if(p[i]<=' ' || p[i]>'~' || (p[i]=='.' && p[i+1]=='.'))return 0;
            memcpy(paths[k],p,(size_t)n);paths[k][n]=0;
        }
        p=*e?e+1:e;
    }
    *pp=p;return 1;
}

int AW_ItemsParse(const char *text,int numframes,float *rows,int maxframes,char paths[AW_ITEMS_KINDS][AW_ITEMS_PATH]) {
    const char *p=text;float f;int frames,i,k;
    if(strncmp(p,"AWTG1 ",6))return 0;
    p+=6;if(!number(&p,&f) || f<1 || f>AW_ITEMS_MAX_FRAMES || f>maxframes)return 0;
    frames=(int)f;if(frames!=numframes)return 0;
    p=line_end(p);if(*p)p++;
    if(!item_paths(&p,paths))return 0;
    for(i=0;i<frames;i++){
        for(k=0;k<AW_ITEMS_ROW;k++)if(!number(&p,&rows[i*AW_ITEMS_ROW+k]))return 0;
        while(*p==' ' || *p=='\r')p++;
        if(*p!='\n' && *p)return 0;
        if(*p)p++;
    }
    return frames;
}

int AW_ItemsParseSkel(const char *text,int numframes,char paths[AW_ITEMS_KINDS][AW_ITEMS_PATH],int bones[AW_ITEMS_KINDS],
                      float scale[3],char light[AW_ITEMS_PATH],float emitter[3],int *has_emitter) {
    const char *p=text;float f;int frames,k;
    if(has_emitter)*has_emitter=0;
    if(light)light[0]=0;
    if(strncmp(p,"AWTS1 ",6))return 0;
    p+=6;if(!number(&p,&f) || f<1 || f>AW_ITEMS_MAX_SKEL_FRAMES)return 0;
    frames=(int)f;if(frames!=numframes)return 0;
    p=line_end(p);if(*p)p++;
    if(!item_paths(&p,paths) || strncmp(p,"bones ",6))return 0;
    p+=6;
    for(k=0;k<AW_ITEMS_KINDS;k++){
        if(!number(&p,&f) || f<-1 || f>=AW_ITEMS_MAX_BONES || f!=(float)(int)f)return 0;
        bones[k]=(int)f;
    }
    p=line_end(p);if(*p)p++;
    if(strncmp(p,"scale ",6))return 0;
    p+=6;
    for(k=0;k<3;k++)if(!number(&p,&scale[k]) || !(scale[k]>0))return 0;
    /* optional: a carried light (a guard's torch; SKEL-ITEM-TAGS-52), its model on the shield bone and its flame
     * point in that bone's space; it takes the shield hand while torches are carried (night, or forced) */
    p=line_end(p);if(*p)p++;
    if(!strncmp(p,"light ",6)){
        const char *e;float pt[3];int n,i;
        p+=6;e=line_end(p);n=(int)(e-p);if(n>0 && p[n-1]=='\r')n--;
        if(n<1 || n>=AW_ITEMS_PATH || bones[1]<0)return 0;
        for(i=0;i<n;i++)if(p[i]<=' ' || p[i]>'~' || (p[i]=='.' && p[i+1]=='.'))return 0;
        if(light){memcpy(light,p,(size_t)n);light[n]=0;}
        p=*e?e+1:e;
        if(strncmp(p,"emitter ",8))return 0;
        p+=8;
        for(k=0;k<3;k++)if(!number(&p,&pt[k]))return 0;
        if(emitter)for(k=0;k<3;k++)emitter[k]=pt[k];
        if(has_emitter)*has_emitter=1;
    }
    return frames;
}

void AW_ItemsPose(const float *tag6,const float origin[3],float yaw,float out_origin[3],float out_angles[3]) {
    float r=yaw*(float)(3.14159265358979323846/180.0),c=Q_CosRad(r),s=Q_SinRad(r);
    out_origin[0]=origin[0]+c*tag6[0]-s*tag6[1];
    out_origin[1]=origin[1]+s*tag6[0]+c*tag6[1];
    out_origin[2]=origin[2]+tag6[2];
    /* r_alias.c R_AliasSetUpTransform negates an alias entity's pitch before AngleVectors,
     * so the entity carries minus the tag's (true AngleVectors) pitch. */
    out_angles[0]=-tag6[3];out_angles[1]=tag6[4]+yaw;out_angles[2]=tag6[5];
}

#ifndef AW_ITEMS_HOST_TEST
/* One tag table per actor model in use, reset per level (like aw_anim.c's layouts);
 * rows live on the hunk, which the level owns. */
#define TABLE 64
/* rows: a baked model's tag rows; or skel: a skeletal model's item bones and actor scale (rows NULL). */
static struct {model_t *model;int frames;float *rows;int item[AW_ITEMS_KINDS];
               int skel,bone[AW_ITEMS_KINDS];float scale[3];
               float emitter[3];int has_emitter,light_item;} table[TABLE];   /* a carried light (guard torch) */
static int used;
static model_t *level_world;
static char names[TABLE*AW_ITEMS_KINDS][AW_ITEMS_PATH];   /* precache names live through the level */
static int named;

static void level_check(void) {
    R_AliasTorchLayer=AW_ItemsTorchLayer;   /* the renderer poses a torch-holding guard's arm (r_alias.c) */
    R_AliasStormLayer=AW_ItemsStormLayer;   /* and an actor's eye-shielding arm in an ash or blight storm */
    if(level_world!=sv.worldmodel){level_world=sv.worldmodel;used=0;named=0;memset(table,0,sizeof(table));}
}
static model_t *model_of(edict_t *e) {
    int i=(int)e->v.modelindex;
    return i>0 && i<MAX_MODELS?sv.models[i]:NULL;
}
static int entry_of(model_t *m) {
    int i;
    for(i=0;i<used;i++)if(table[i].model==m)return i;
    return -1;
}
/* Carried lights (a guard's torch on a skeletal actor; SKEL-ITEM-TAGS-52): an actor whose tag names a flame point
 * carries its shield-slot item all the time, not only while it fights (the combat slots then draw its weapon only).
 * One entity per carrier, made when first needed and moved with the actor every server frame
 * (AW_ItemsCarriedUpdate); reset per level. */
#define CARRIERS AW_ITEMS_CARRIERS
static struct {edict_t *actor;edict_t *light;int table;} carriers[CARRIERS];
static int carrier_count;
static model_t *carrier_world;
static void carriers_check(void) {
    if(carrier_world!=sv.worldmodel){carrier_world=sv.worldmodel;carrier_count=0;memset(carriers,0,sizeof(carriers));}
}
static int carries_light(int t) {return t>=0 && table[t].skel && table[t].has_emitter && table[t].light_item;}
/* Precache an item model while the level loads (spawn functions only). */
static int precache(const char *path) {
    int i;model_t *m;
    for(i=1;i<MAX_MODELS && sv.model_precache[i];i++)if(!strcmp(sv.model_precache[i],path))return i;
    if(i>=MAX_MODELS || sv.state!=ss_loading || named>=TABLE*AW_ITEMS_KINDS)return 0;
    if(!(m=Mod_ForName((char *)path,false)))return 0;
    strcpy(names[named],path);sv.model_precache[i]=names[named++];sv.models[i]=m;
    return i;
}

/* One model's tag table. numframes 0: a mover model that is not loaded yet (aw_anim.c registers it by
 * name only): the tag's own frame count is kept and checked against the model when it is worn
 * (frames_match); the builder writes one row per frame of each model (ANIMKIT-ITEM-TAG-FRAMES-35). */
static void prep(model_t *m,const char *name,int numframes) {
    char path[MAX_QPATH+4],items[AW_ITEMS_KINDS][AW_ITEMS_PATH];byte *text;const char *p;
    int mark,n,k,frames,any=0;float *rows,declared;
    if(!m || entry_of(m)>=0 || used>=TABLE)return;
    n=(int)strlen(name);
    if(n<5 || n>=(int)sizeof(path) || strcmp(name+n-4,".mdl") || numframes<0 || numframes>AW_ITEMS_MAX_SKEL_FRAMES)
        return;
    memcpy(path,name,(size_t)(n-4));strcpy(path+n-4,".tag");
    /* The rows stay on the level's hunk; the text is read into temporary memory. */
    mark=Hunk_LowMark();
    text=COM_LoadTempFile(path);
    if(!text){Hunk_FreeToLowMark(mark);return;}
    if(!strncmp((const char *)text,"AWTS1 ",6)){
        /* a skeletal model: its items follow the table's bones, posed when drawn (SKEL-ITEM-TAGS-52) */
        int bones[AW_ITEMS_KINDS];float scale[3];char light[AW_ITEMS_PATH];
        frames=AW_ItemsParseSkel((const char *)text,numframes,items,bones,scale,light,table[used].emitter,
                                 &table[used].has_emitter);
        Hunk_FreeToLowMark(mark);
        if(!frames){Con_Printf("Item tags %s: invalid, items not drawn\n",path);return;}
        table[used].model=m;table[used].frames=frames;table[used].rows=NULL;table[used].skel=1;
        for(k=0;k<3;k++)table[used].scale[k]=scale[k];
        for(k=0;k<AW_ITEMS_KINDS;k++){
            table[used].bone[k]=bones[k];
            table[used].item[k]=items[k][0] && bones[k]>=0?precache(items[k]):0;
            if(table[used].item[k])any=1;
        }
        table[used].light_item=table[used].has_emitter && light[0]?precache(light):0;
        if(table[used].light_item)any=1;
        if(any)used++;
        return;
    }
    if(numframes>AW_ITEMS_MAX_FRAMES){Hunk_FreeToLowMark(mark);return;}
    if(!numframes){
        p=(const char *)text;
        if(strncmp(p,"AWTG1 ",6)){Con_Printf("Item tags %s: invalid, items not drawn\n",path);Hunk_FreeToLowMark(mark);return;}
        p+=6;
        if(!number(&p,&declared) || declared<1 || declared>AW_ITEMS_MAX_FRAMES){
            Con_Printf("Item tags %s: invalid, items not drawn\n",path);Hunk_FreeToLowMark(mark);return;
        }
        numframes=(int)declared;
    }
    rows=(float *)Hunk_AllocName(numframes*AW_ITEMS_ROW*(int)sizeof(float),"awtag");
    frames=AW_ItemsParse((const char *)text,numframes,rows,numframes,items);
    if(!frames){
        Con_Printf("Item tags %s: invalid, items not drawn\n",path);
        Hunk_FreeToLowMark(mark);return;
    }
    table[used].model=m;table[used].frames=frames;table[used].rows=rows;table[used].skel=0;
    for(k=0;k<AW_ITEMS_KINDS;k++){table[used].item[k]=items[k][0]?precache(items[k]):0;if(table[used].item[k])any=1;}
    if(any)used++;else Hunk_FreeToLowMark(mark);
}

void AW_ItemsPrep(edict_t *actor) {
    model_t *m;const aw_anim_t *a;int i;
    level_check();
    if(!actor || !(m=model_of(actor)) || sv.state!=ss_loading)return;
    if(m->numframes<1 || m->numframes>AW_ITEMS_MAX_SKEL_FRAMES)return;
    prep(m,m->name,m->numframes);
    if(carries_light(entry_of(m))){          /* a guard's torch: carried all the time (AW_ItemsCarriedUpdate) */
        carriers_check();
        for(i=0;i<carrier_count && carriers[i].actor!=actor;i++);
        if(i==carrier_count && carrier_count<CARRIERS){
            carriers[carrier_count].actor=actor;carriers[carrier_count].light=NULL;
            carriers[carrier_count++].table=entry_of(m);
        }
    }
    /* The full-kit model the actor wears while it moves or fights (aw_anim.c AW_AnimMover) has its own
     * tag table beside it; AW_AnimPrep has registered it by name. */
    a=AW_AnimOf(actor);
    if(!a->mover[0])return;
    for(i=1;i<MAX_MODELS && sv.model_precache[i];i++)
        if(!strcmp(sv.model_precache[i],a->mover)){
            if(sv.models[i] && sv.models[i]!=m)prep(sv.models[i],a->mover,sv.models[i]->numframes);
            break;
        }
}

/* A table is used only when its rows match the model's frames (a mover's are checked once it is loaded). */
static int frames_match(model_t *m,int t) {return t>=0 && m && m->numframes==table[t].frames;}

int AW_ItemsShow(edict_t *actor,edict_t *out[AW_ITEMS_KINDS]) {
    int t,k,n=0;edict_t *e;
    level_check();
    for(k=0;k<AW_ITEMS_KINDS;k++)out[k]=NULL;
    if(!actor || actor->free || !frames_match(model_of(actor),t=entry_of(model_of(actor))))return 0;
    for(k=0;k<AW_ITEMS_KINDS;k++){
        int i=table[t].item[k];
        /* while torches are carried the torch has the shield hand (AW_ItemsCarriedUpdate) */
        if(!i || !sv.model_precache[i] || (k==1 && carries_light(t) && AW_GuardTorchWanted()))continue;
        e=ED_Alloc();
        e->v.classname=ED_NewString("aw_item")-pr_strings;
        e->v.model=sv.model_precache[i]-pr_strings;e->v.modelindex=i;
        e->v.movetype=MOVETYPE_NONE;e->v.solid=SOLID_NOT;e->v.frame=0;
        out[k]=e;n++;
    }
    AW_ItemsUpdate(actor,out);
    return n;
}

/* A skeletal model's item rows at one table frame (SKEL-ITEM-TAGS-52): the table posed at the frame and each item
 * bone made into a tag row. The last pose is kept (an armed actor's items follow it every server frame while its
 * table frame changes about 8 times a second). 0 when the model has no table. */
int AW_ItemsTorchLayer(const model_t *m,const void *skel_table,int frame,float *layer_frame,int *root) {
    const aw_skel_table_t *tab=(const aw_skel_table_t *)skel_table;
    aw_skel_group_t g;int t,i,span;
    if(!m || !tab || !AW_GuardTorchWanted())return 0;
    for(t=0;t<used && table[t].model!=m;t++);
    if(t==used || !carries_light(t))return 0;
    if((*root=AW_SkelLeftArmRoot(tab,table[t].bone[1],table[t].bone[0]))<0 || (i=AW_SkelGroup(tab,"torch"))<0)return 0;
    AW_SkelGroupAt(tab,i,&g);
    span=(int)(g.last-g.first)+1;
    if(span<1)return 0;
    /* the group's frames in turn with the actor's own (the baked guards: its eight phases), so a frame poses alike */
    *layer_frame=(float)(g.first+(unsigned)(frame<0?0:frame)%(unsigned)span);
    return 1;
}

/* ACTOR-STORM-POSE-51: the frames an actor may shield its eyes in. Rule from OpenMW file
 * apps/openmw/mwmechanics/character.cpp (updateIdleStormState, read, not copied): only with no upper-body action
 * (no attack, cast, weapon or hit) and out of the water; here: a frame of the idle groups (idle, idle2..idle9) or of
 * walking, running, turning or sneaking; a view's own prefix ("f:", "d:f:") is skipped. One answer kept. */
static int storm_frame(const aw_skel_table_t *tab,int frame) {
    static const aw_skel_table_t *last_tab;static int last_frame=-1,last_ok;
    aw_skel_group_t g;int i;const char *name,*c;
    if(tab==last_tab && frame==last_frame)return last_ok;
    last_tab=tab;last_frame=frame;last_ok=0;
    for(i=0;i<tab->groups;i++){
        AW_SkelGroupAt(tab,i,&g);
        if(frame<(int)g.first || frame>(int)g.last)continue;
        for(name=c=g.name;*c && c<g.name+AW_SKEL_NAME;c++)if(*c==':')name=c+1;
        if(!Q_strncasecmp((char *)name,"idle",4))
            last_ok=!name[4] || (name[4]>='2' && name[4]<='9' && !name[5]);
        else last_ok=!Q_strncasecmp((char *)name,"walk",4) || !Q_strncasecmp((char *)name,"run",3) ||
                     !Q_strncasecmp((char *)name,"turn",4) || !Q_strncasecmp((char *)name,"sneak",5);
        break;
    }
    return last_ok;
}
int AW_ItemsStormLayer(const model_t *m,const void *skel_table,int frame,float yaw,float *layer_frame,int *root) {
    const aw_skel_table_t *tab=(const aw_skel_table_t *)skel_table;
    aw_skel_group_t g;int t,i,span;float dir[2];
    if(!m || !tab || !AW_WeatherStorm(dir) || !AW_WeatherFacesStorm(yaw,dir))return 0;
    for(t=0;t<used && table[t].model!=m;t++);
    if(t==used || !table[t].skel)return 0;
    if((*root=AW_SkelRightArmRoot(tab,table[t].bone[1],table[t].bone[0]))<0 || (i=AW_SkelGroup(tab,"idlestorm"))<0)return 0;
    if(!storm_frame(tab,frame))return 0;
    AW_SkelGroupAt(tab,i,&g);
    span=(int)(g.last-g.first)+1;
    if(span<1)return 0;
    /* the group in turn with the actor's own frames, as the torch layer */
    *layer_frame=(float)(g.first+(unsigned)(frame<0?0:frame)%(unsigned)span);
    return 1;
}

static int skel_rows(int t,int f,float rows[AW_ITEMS_ROW]) {
    static const aw_skel_table_t *last_table;static int last_frame=-1,last_layered;
    static float world[AW_SKEL_MAX_BONES][3][4];
    const aliashdr_t *hdr=(const aliashdr_t *)Mod_Extradata(table[t].model);
    const aw_skel_table_t *tab=hdr && hdr->aw_skel?(const aw_skel_table_t *)hdr->aw_skel_table:NULL;
    int k,root=-1,layered;float layer=0;
    if(!tab)return 0;
    /* a guard holding his torch has his left arm on the torch group, as he is drawn (AW_ItemsTorchLayer) */
    layered=AW_ItemsTorchLayer(table[t].model,tab,f,&layer,&root);
    if(tab!=last_table || f!=last_frame || layered!=last_layered){
        AW_SkelPoseLayer(tab,(float)f,layer,layered?root:-1,world);last_table=tab;last_frame=f;last_layered=layered;
    }
    for(k=0;k<AW_ITEMS_KINDS;k++){
        int b=table[t].bone[k];
        if(b>=0 && b<tab->bones)AW_SkelBoneTag((const float (*)[4])world[b],table[t].scale,&rows[k*6]);
        else memset(&rows[k*6],0,6*sizeof(float));
    }
    return 1;
}

void AW_ItemsUpdate(edict_t *actor,edict_t *items[AW_ITEMS_KINDS]) {
    int t,k,f;float skel[AW_ITEMS_ROW];const float *row;
    if(!actor || actor->free || !frames_match(model_of(actor),t=entry_of(model_of(actor)))){AW_ItemsHide(items);return;}
    f=(int)actor->v.frame;if(f<0 || f>=table[t].frames)f=0;
    if(table[t].skel){
        if(!skel_rows(t,f,skel)){AW_ItemsHide(items);return;}
        row=skel;
    }else row=&table[t].rows[f*AW_ITEMS_ROW];
    for(k=0;k<AW_ITEMS_KINDS;k++){
        edict_t *e=items[k];
        if(!e || e->free)continue;
        AW_ItemsPose(&row[k*6],actor->v.origin,actor->v.angles[1],e->v.origin,e->v.angles);
        SV_LinkEdict(e,false);
    }
}

/* The shield-slot item's flame point of a carried light model (the torch item's own model space), 1 if it is one.
 * The tag states it in the shield bone's units (tools/prepare_guard_torches.py torch_item); the item model is that
 * bone space at the items' own scale, 0.25 (tools/npc_items.py: an item keeps its size, it is not scaled with the
 * actor), so the point is taken at that scale: unscaled it sat about three torch lengths out, the flame and its light
 * away from the torch (SKEL-ITEM-TAGS-52). */
#define AW_ITEMS_ITEM_SCALE 0.25f
int AW_ItemsLightEmitter(const model_t *item,float out[3]) {
    int t,k;
    if(!item)return 0;
    for(t=0;t<used;t++){
        int i=table[t].light_item;
        if(!carries_light(t) || sv.models[i]!=item)continue;
        for(k=0;k<3;k++)out[k]=table[t].emitter[k]*AW_ITEMS_ITEM_SCALE;
        return 1;
    }
    return 0;
}

void AW_ItemsCarriedUpdate(void) {
    int i,t,wanted;float rows[AW_ITEMS_ROW];
    carriers_check();
    wanted=AW_GuardTorchWanted();       /* as the baked guard torches: at night, or forced (aw_guard_torch.c) */
    for(i=0;i<carrier_count;i++){
        edict_t *a=carriers[i].actor,*e=carriers[i].light;
        t=carriers[i].table;
        if(!wanted || !a || a->free || model_of(a)!=table[t].model){
            if(e && !e->free)ED_Free(e);
            carriers[i].light=NULL;continue;
        }
        if(!e || e->free){
            int m=table[t].light_item;
            e=carriers[i].light=ED_Alloc();
            e->v.classname=ED_NewString("aw_item")-pr_strings;
            e->v.model=sv.model_precache[m]-pr_strings;e->v.modelindex=m;
            e->v.movetype=MOVETYPE_NONE;e->v.solid=SOLID_NOT;e->v.frame=0;
        }
        if(!skel_rows(t,(int)a->v.frame<0 || (int)a->v.frame>=table[t].frames?0:(int)a->v.frame,rows))continue;
        AW_ItemsPose(&rows[6],a->v.origin,a->v.angles[1],e->v.origin,e->v.angles);
        SV_LinkEdict(e,false);
    }
}

void AW_ItemsHide(edict_t *items[AW_ITEMS_KINDS]) {
    int k;
    for(k=0;k<AW_ITEMS_KINDS;k++){if(items[k] && !items[k]->free)ED_Free(items[k]);items[k]=NULL;}
}

int AW_ItemsKinds(edict_t *actor) {
    int t,k,kinds=0;
    level_check();
    if(!actor || actor->free || (t=entry_of(model_of(actor)))<0)return 0;
    for(k=0;k<AW_ITEMS_KINDS;k++)if(table[t].item[k])kinds|=1<<k;
    if(carries_light(t))kinds|=AW_ITEMS_LIGHT;
    return kinds;
}
/* A single active player alias: optional per-frame tags use the same parser
 * and bounds as NPC attachments. Storage is released on model/scene change. */
static model_t *player_tag_model;
static float *player_tag_rows;
static int player_tag_frames,player_tag_failed;
void AW_ItemsAliasClear(void){
    free(player_tag_rows);player_tag_rows=NULL;player_tag_model=NULL;
    player_tag_frames=player_tag_failed=0;
}
int AW_ItemsAliasTag(model_t *model,int frame,int kind,float tag[6]){
    FILE *f=NULL;int size,n;char path[96],paths[AW_ITEMS_KINDS][AW_ITEMS_PATH],*text;
    if(!model || model->type!=mod_alias || kind<0 || kind>=AW_ITEMS_KINDS)return 0;
    if(player_tag_model!=model){AW_ItemsAliasClear();player_tag_model=model;}
    if(player_tag_failed)return 0;
    if(!player_tag_rows){
        n=(int)strlen(model->name);
        if(n<5 || n>80 || model->numframes<1 || model->numframes>AW_ITEMS_MAX_FRAMES)goto unavailable;
        strcpy(path,model->name);strcpy(path+n-4,".tag");
        size=COM_FOpenFile(path,&f);
        if(!f || size<20 || size>AW_ITEMS_MAX_FRAMES*AW_ITEMS_ROW*16+256)goto unavailable;
        text=(char *)AW_TryMalloc(size+1);if(!text)goto unavailable;
        if(fread(text,1,size,f)!=(size_t)size){free(text);goto unavailable;}
        fclose(f);f=NULL;text[size]=0;
        player_tag_rows=(float *)AW_TryMalloc(model->numframes*AW_ITEMS_ROW*sizeof(float));
        if(!player_tag_rows){free(text);goto unavailable;}
        player_tag_frames=AW_ItemsParse(text,model->numframes,player_tag_rows,model->numframes,paths);
        free(text);
        if(player_tag_frames!=model->numframes){free(player_tag_rows);player_tag_rows=NULL;goto unavailable;}
    }
    if(frame<0)return 1;
    if(frame>=player_tag_frames || !tag)return 0;
    memcpy(tag,player_tag_rows+frame*AW_ITEMS_ROW+kind*6,6*sizeof(float));return 1;
 unavailable:
    if(f)fclose(f);
    player_tag_failed=1;
    Con_Printf("Player equipment tags unavailable for %s; item pose not substituted.\n",model->name);return 0;
}
#endif
