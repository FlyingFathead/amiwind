/* Carried items on a hand bone's per-frame tag (aw_items.h; tools/npc_items.py). */
#ifdef AW_ITEMS_HOST_TEST
#include <string.h>
float Q_SinRad(float radians);
float Q_CosRad(float radians);
#else
#include "quakedef.h"
#include "aw_anim.h"
#endif
#include "aw_items.h"

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

int AW_ItemsParse(const char *text,int numframes,float *rows,int maxframes,char paths[AW_ITEMS_KINDS][AW_ITEMS_PATH]) {
    static const char *const kind[AW_ITEMS_KINDS]={"weapon ","shield "};
    const char *p=text,*e;float f;int frames,i,k,n;
    if(strncmp(p,"AWTG1 ",6))return 0;
    p+=6;if(!number(&p,&f) || f<1 || f>AW_ITEMS_MAX_FRAMES || f>maxframes)return 0;
    frames=(int)f;if(frames!=numframes)return 0;
    p=line_end(p);if(*p)p++;
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
    for(i=0;i<frames;i++){
        for(k=0;k<AW_ITEMS_ROW;k++)if(!number(&p,&rows[i*AW_ITEMS_ROW+k]))return 0;
        while(*p==' ' || *p=='\r')p++;
        if(*p!='\n' && *p)return 0;
        if(*p)p++;
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
static struct {model_t *model;int frames;float *rows;int item[AW_ITEMS_KINDS];} table[TABLE];
static int used;
static model_t *level_world;
static char names[TABLE*AW_ITEMS_KINDS][AW_ITEMS_PATH];   /* precache names live through the level */
static int named;

static void level_check(void) {
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
    if(n<5 || n>=(int)sizeof(path) || strcmp(name+n-4,".mdl") || numframes<0 || numframes>AW_ITEMS_MAX_FRAMES)return;
    memcpy(path,name,(size_t)(n-4));strcpy(path+n-4,".tag");
    /* The rows stay on the level's hunk; the text is read into temporary memory. */
    mark=Hunk_LowMark();
    text=COM_LoadTempFile(path);
    if(!text){Hunk_FreeToLowMark(mark);return;}
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
    table[used].model=m;table[used].frames=frames;table[used].rows=rows;
    for(k=0;k<AW_ITEMS_KINDS;k++){table[used].item[k]=items[k][0]?precache(items[k]):0;if(table[used].item[k])any=1;}
    if(any)used++;else Hunk_FreeToLowMark(mark);
}

void AW_ItemsPrep(edict_t *actor) {
    model_t *m;const aw_anim_t *a;int i;
    level_check();
    if(!actor || !(m=model_of(actor)) || sv.state!=ss_loading)return;
    if(m->numframes<1 || m->numframes>AW_ITEMS_MAX_FRAMES)return;
    prep(m,m->name,m->numframes);
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
        if(!i || !sv.model_precache[i])continue;
        e=ED_Alloc();
        e->v.classname=ED_NewString("aw_item")-pr_strings;
        e->v.model=sv.model_precache[i]-pr_strings;e->v.modelindex=i;
        e->v.movetype=MOVETYPE_NONE;e->v.solid=SOLID_NOT;e->v.frame=0;
        out[k]=e;n++;
    }
    AW_ItemsUpdate(actor,out);
    return n;
}

void AW_ItemsUpdate(edict_t *actor,edict_t *items[AW_ITEMS_KINDS]) {
    int t,k,f;
    if(!actor || actor->free || !frames_match(model_of(actor),t=entry_of(model_of(actor)))){AW_ItemsHide(items);return;}
    f=(int)actor->v.frame;if(f<0 || f>=table[t].frames)f=0;
    for(k=0;k<AW_ITEMS_KINDS;k++){
        edict_t *e=items[k];
        if(!e || e->free)continue;
        AW_ItemsPose(&table[t].rows[f*AW_ITEMS_ROW+k*6],actor->v.origin,actor->v.angles[1],e->v.origin,e->v.angles);
        SV_LinkEdict(e,false);
    }
}

void AW_ItemsHide(edict_t *items[AW_ITEMS_KINDS]) {
    int k;
    for(k=0;k<AW_ITEMS_KINDS;k++){if(items[k] && !items[k]->free)ED_Free(items[k]);items[k]=NULL;}
}
#endif
