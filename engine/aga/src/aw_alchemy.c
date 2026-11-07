/* SPDX-License-Identifier: GPL-2.0-or-later
 * Alchemy, the engine glue (aw_alchemy.h; docs/ALCHEMY.md): drinking a potion, eating an ingredient, and the alchemy
 * window that a carried apparatus opens.
 *
 * Use (the inventory window's E/Enter or its Drink/Eat/Use entry, or "aw_inventory use ID"):
 * - a potion: one leaves the inventory and its effects land on the player (Self) through the active effects
 *   (AW_MwscriptLand, aw_effects.h), as OpenMW Actor::consume and CastSpell::cast(Potion); the "Drink" sound;
 * - an ingredient: one leaves the inventory; its first effect lands when the roll allows (AW_AlchemyEat), with an
 *   Alchemy skill use (OpenMW actioneat.cpp), else the game's "%s has no effect on you."; the "Swallow" sound;
 * - an apparatus: the alchemy window opens (OpenMW ActionAlchemy), the inventory window closing first.
 * The window: the best carried apparatus of each type (the highest quality), four ingredient slots, the carried
 * ingredients with the effects the Alchemy skill reveals (one slot per fWortChanceValue points), the potion those
 * slots would make (the effects shown as the skill reveals them), its name (its first effect, OpenMW
 * suggestPotionName), Create and Cancel. Create follows OpenMW Alchemy::create with one potion: the checks, the roll,
 * one of each ingredient used up either way, the potion added (a made item, aw_actorstate.h AW_MADE_POTION; an
 * identical one made before is reused, as OpenMW getRecord), an Alchemy skill use, the game's line and sound.
 *
 * Cost: nothing resident but this file's few statics; the window's state (the carried ingredients, about 60 bytes
 * each, and the game's lines, about 1.6 KB) is allocated when it opens and freed when it closes; a drink or a meal
 * reads alchemy/settings.txt (about 1 KB) once and frees it. The item's alchemy numbers come in its own catalogue row.
 * "aw_inventory alchemy ..." (the test words, aw_inventory's own command): add "ID", remove N, create, status, close. */
#include <stdlib.h>
#include <string.h>
#include "quakedef.h"
#include "aw_alchemy.h"
#include "aw_inventory.h"
#include "aw_actorstate.h"
#include "aw_cast.h"
#include "aw_effects.h"
#include "aw_combat.h"
#include "aw_levelup.h"
#include "aw_statswin.h"
#include "aw_tryalloc.h"

#define SETTINGS_FILE "alchemy/settings.txt"
#define SKILL_ALCHEMY 16
#define USE_CREATE_POTION 0       /* OpenMW ESM::Skill::Alchemy_CreatePotion */
#define USE_INGREDIENT 1          /* Alchemy_UseIngredient */
#define TIERS 6
enum {T_SUCCESS,T_FAILED,T_TOO_FEW,T_NO_MORTAR,T_NO_EFFECT,T_ONE_EACH,T_CREATE,T_INGREDIENTS,T_APPARATUS,T_EFFECTS,
      T_NAME,T_CANCEL,T_ABSORB,T_DAMAGE,T_DRAIN,T_FORTIFY,T_RESTORE,T_COUNT};
static const char *const text_keys[T_COUNT]={"sPotionSuccess","sNotifyMessage8","sNotifyMessage6a","sNotifyMessage45",
    "sNotifyMessage50","sNotifyMessage6","sCreate","sIngredients","sApparatus","sEffects","sName","sCancel","sAbsorb",
    "sDamage","sDrain","sFortify","sRestore"};
/* the words when an image has no line of its own (an older image): the masters' */
static const char *const text_fallback[T_COUNT]={"You created a potion","Your potion failed.",
    "At least two ingredients are needed to make a potion.","You need a Mortar and Pestle to use","%s has no effect on you.",
    "Only one of each ingredient can be used to make a potion.","Create","Ingredients","Apparatus","Effects","Name",
    "Cancel","Absorb","Damage","Drain","Fortify","Restore"};
enum {S_DRINK,S_SWALLOW,S_SUCCESS,S_FAIL,S_COUNT};
static const char *const sound_keys[S_COUNT]={"drink","swallow","success","fail"};
typedef struct {
    aw_alchemy_settings_t set;
    char text[T_COUNT][72],sound[S_COUNT][40],tier[TIERS][40];int tiers;
} data_t;

static unsigned long drinks,meals,meals_empty,brews,brews_failed;
static double last_use_ms,last_create_ms;   /* the last drink or meal, the last Create: for the budget sheet */

/* ---- the data file ---- */
static data_t *data_load(void){
    FILE *f=NULL;char line[200];data_t *d;int i;
    d=(data_t *)AW_TryCalloc(1,sizeof(*d));
    if(!d)return NULL;
    for(i=0;i<T_COUNT;i++)Q_strcpy_bounded(d->text[i],text_fallback[i],sizeof(d->text[i]));
    if(COM_FOpenFile(SETTINGS_FILE,&f)<0 || !f)return d;
    if(!fgets(line,sizeof(line),f) || strncmp(line,"AWAL1",5)){fclose(f);return d;}
    while(fgets(line,sizeof(line),f)){
        char name[64],rest[160];float v;
        line[strcspn(line,"\r\n")]=0;
        if(Q_sscanf(line,"set %63s %f",name,&v)==2){AW_AlchemySetting(&d->set,name,v);continue;}
        if(!strncmp(line,"text ",5)){
            const char *p=line+5,*sp=strchr(p,' ');
            if(!sp)continue;
            for(i=0;i<T_COUNT;i++)if((int)strlen(text_keys[i])==sp-p && !strncmp(text_keys[i],p,sp-p))
                Q_strcpy_bounded(d->text[i],sp+1,sizeof(d->text[i]));
            continue;
        }
        if(Q_sscanf(line,"sound %63s %159s",name,rest)==2){
            for(i=0;i<S_COUNT;i++)if(!strcmp(name,sound_keys[i]))Q_strcpy_bounded(d->sound[i],rest,sizeof(d->sound[i]));
            continue;
        }
        if(Q_sscanf(line,"tier %63s %159s",name,rest)==2 && d->tiers<TIERS)
            Q_strcpy_bounded(d->tier[d->tiers++],rest,sizeof(d->tier[0]));
    }
    fclose(f);
    return d;
}
static void sound(const data_t *d,int which){if(d && d->sound[which][0])S_LocalSound((char *)d->sound[which]);}
static void notice(const char *line){AW_UISubtitle("",line,4);}

/* ---- the player ---- */
static void player_stats(float *alchemy,float *intelligence,float *luck){
    aw_actor_t *p=AW_MwscriptPlayerRecord();
    if(p){*alchemy=AW_ActorStat(p,AWA_SKILL+SKILL_ALCHEMY);*intelligence=AW_ActorStat(p,AWA_ATTRIBUTE+1);
          *luck=AW_ActorStat(p,AWA_ATTRIBUTE+7);return;}
    {aw_stats_sheet_t s;AW_StatsSheet(&s);*alchemy=s.skills[SKILL_ALCHEMY];*intelligence=s.attributes[1];*luck=s.attributes[7];}
}
static int mgef_of(void *ctx,int effect,uint32_t *flags,float *base_cost){
    aw_mgef_t m;(void)ctx;
    if(!AW_ActorMagicEffect(effect,&m))return 0;
    *flags=m.flags|(AW_EffectHarmful(effect)?AW_ALCHEMY_MGEF_HARMFUL:0);*base_cost=m.base_cost;
    return 1;
}
/* an effect as the spell machinery takes it: Self, magnitude min = max, its attribute or skill */
static void spell_effect(const aw_alchemy_effect_t *x,aw_spell_effect_t *e){
    int kind=AW_AlchemyArgKind(x->effect);
    memset(e,0,sizeof(*e));
    e->effect=x->effect;e->skill=-1;e->attribute=-1;
    if(kind==1 && x->arg<8)e->attribute=(signed char)x->arg;
    if(kind==2 && x->arg<27)e->skill=(signed char)x->arg;
    e->range=AW_RANGE_SELF;e->duration=x->duration;e->magnitude_min=e->magnitude_max=x->magnitude;
}
/* the effect's words (OpenMW getMagicEffectString): "Fortify Strength", "Restore Fatigue", "Night Eye" */
static void effect_name(const data_t *d,const aw_alchemy_effect_t *x,char *out,int size){
    aw_mgef_t m;int kind=AW_AlchemyArgKind(x->effect);const char *word=NULL;
    if(kind && x->arg!=0xFF && d){
        switch(x->effect){
        case 85:case 89:word=d->text[T_ABSORB];break;
        case 22:case 26:word=d->text[T_DAMAGE];break;
        case 17:case 21:word=d->text[T_DRAIN];break;
        case 79:case 83:word=d->text[T_FORTIFY];break;
        case 74:case 78:word=d->text[T_RESTORE];break;
        }
        Q_snprintf(out,size,"%s %s",word,kind==1?AW_StatsAttributeName(x->arg):AW_StatsSkillName(x->arg));
        return;
    }
    if(AW_ActorMagicEffect(x->effect,&m) && m.name[0])Q_snprintf(out,size,"%s",m.name);
    else Q_snprintf(out,size,"Effect %d",x->effect);
}
static float fatigue_term(void){
    float maximum=0,current=AW_CombatPlayerFatigue(&maximum);
    return AW_CastFatigueTerm(1.25f,.5f,current,maximum);   /* fFatigueBase, fFatigueMult of the masters (aw_cast.c) */
}

/* ---- drinking and eating ---- */
static int drink(const aw_inventory_item_t *it){
    aw_spell_effect_t e[AW_INV_ALCHEMY_EFFECTS];aw_mgef_t m[AW_INV_ALCHEMY_EFFECTS];int i,n=it->alchemy_count,landed;data_t *d;
    if(AW_StateGet(&aw_state,AW_ITEM,it->id)<1 || n<1 || n>AW_INV_ALCHEMY_EFFECTS || !AW_MwscriptPlayerRecord())return 0;
    for(i=0;i<n;i++){spell_effect(&it->alchemy[i],&e[i]);if(!AW_ActorMagicEffect(e[i].effect,&m[i]))memset(&m[i],0,sizeof(m[i]));}
    if(!AW_ItemAdd(&aw_state,it->id,-1))return 0;   /* used up first, as OpenMW Actor::consume */
    landed=AW_MwscriptLand(NULL,e,m,n,AW_RANGE_SELF,AW_EFFECT_SOURCE_ITEM);
    drinks++;
    d=data_load();sound(d,S_DRINK);free(d);
    Con_Printf("Alchemy: drank %s (%s): %d of %d effects landed.\n",it->name,it->id,landed,n);
    return 1;
}
static int eat(const aw_inventory_item_t *it){
    aw_spell_effect_t e;aw_mgef_t m;float alchemy,intelligence,luck;unsigned short magnitude=0,duration=0;int roll,ok;data_t *d;
    if(AW_StateGet(&aw_state,AW_ITEM,it->id)<1 || it->alchemy_kind!=AW_ALCHEMY_INGREDIENT ||
       it->alchemy[0].effect==AW_ALCHEMY_NO_EFFECT || !AW_MwscriptPlayerRecord())return 0;   /* OpenMW: no first effect, no meal */
    if(!AW_ActorMagicEffect(it->alchemy[0].effect,&m))memset(&m,0,sizeof(m));
    m.flags|=AW_EffectHarmful(it->alchemy[0].effect)?AW_ALCHEMY_MGEF_HARMFUL:0;
    if(!AW_ItemAdd(&aw_state,it->id,-1))return 0;
    player_stats(&alchemy,&intelligence,&luck);
    roll=rand()%100;
    ok=AW_AlchemyEat(alchemy,intelligence,luck,fatigue_term(),roll,m.flags,m.base_cost,&magnitude,&duration);
    d=data_load();meals++;
    if(ok){
        aw_alchemy_effect_t x=it->alchemy[0];
        x.magnitude=magnitude;x.duration=duration;spell_effect(&x,&e);
        ok=AW_MwscriptLand(NULL,&e,&m,1,AW_RANGE_SELF,AW_EFFECT_SOURCE_ITEM)>0;
        if(ok)AW_LevelupUse(SKILL_ALCHEMY,USE_INGREDIENT,1);
    }
    if(!ok){
        char line[160];const char *form=d?d->text[T_NO_EFFECT]:text_fallback[T_NO_EFFECT],*at=strstr(form,"%s");
        meals_empty++;
        if(at)Q_snprintf(line,sizeof(line),"%.*s%s%s",(int)(at-form),form,it->name,at+2);
        else Q_snprintf(line,sizeof(line),"%s",form);
        notice(line);
    }
    sound(d,S_SWALLOW);free(d);
    Con_Printf("Alchemy: ate %s (%s): roll %d, %s (effect %d, magnitude %u, %u s).\n",it->name,it->id,roll,
               ok?"effect landed":"no effect",it->alchemy[0].effect,(unsigned)magnitude,(unsigned)duration);
    return 1;
}

/* ---- the window ---- */
typedef struct {int row;char name[32];aw_alchemy_effect_t e[4];float weight;} ingredient_t;
typedef struct {
    data_t *d;
    ingredient_t *list;int n,capacity,top,sel,full;
    int slot[AW_ALCHEMY_SLOTS];                         /* rows of the item table, -1 empty */
    float quality[AW_APPARATUS_TYPES];char tool[AW_APPARATUS_TYPES][40];
    int tool_type[16];float tool_quality[16];char tool_name[16][40];int tools;
    aw_alchemy_effect_t keys[AW_ALCHEMY_OUT],fx[AW_ALCHEMY_OUT];int nkeys,nfx,value;
    float skill,intelligence,luck;
    char name[32],message[96];
    unsigned long reads;double open_ms;
} window_t;
static window_t *win;
#define W_LIST_X 164
#define W_LIST_Y 30
#define W_ROW 8
#define W_VISIBLE 11
#define W_SCROLL_X 306
#define W_SLOT_Y 70
#define W_BUTTON_Y 183
#define W_CREATE_X 210
#define W_CANCEL_X 264
#define W_BUTTON_W 48

int AW_AlchemyActive(void){return win!=NULL;}
static void collect(void *ctx,int row,const aw_inventory_item_t *it,int file_row){
    (void)ctx;(void)file_row;
    if(!win || !it || !(it->flags&AW_INV_ALCHEMY))return;
    if(it->alchemy_kind==AW_ALCHEMY_APPARATUS){
        if(win->tools<16 && it->subtype>=0 && it->subtype<AW_APPARATUS_TYPES){
            win->tool_type[win->tools]=it->subtype;win->tool_quality[win->tools]=it->apparatus_quality;
            Q_strcpy_bounded(win->tool_name[win->tools],it->name,sizeof(win->tool_name[0]));win->tools++;
        }
        return;
    }
    if(it->alchemy_kind!=AW_ALCHEMY_INGREDIENT || win->full)return;
    if(win->n>=win->capacity){
        int grow=win->capacity?win->capacity*2:32;ingredient_t *more=(ingredient_t *)AW_TryMalloc((unsigned long)grow*sizeof(*more));
        if(!more){win->full=1;return;}
        if(win->list){memcpy(more,win->list,(size_t)win->n*sizeof(*more));free(win->list);}
        win->list=more;win->capacity=grow;
    }
    {ingredient_t *g=&win->list[win->n++];
     g->row=row;Q_strcpy_bounded(g->name,it->name,sizeof(g->name));memcpy(g->e,it->alchemy,sizeof(g->e));g->weight=it->weight;}
}
static int by_name(const void *a,const void *b){return AW_InventoryCompare(((const ingredient_t *)a)->name,((const ingredient_t *)b)->name);}
static const ingredient_t *of_row(int row){
    int i;
    if(row<0 || !win)return NULL;
    for(i=0;i<win->n;i++)if(win->list[i].row==row)return &win->list[i];
    return NULL;
}
static void slots_of(aw_alchemy_slot_t s[AW_ALCHEMY_SLOTS]){
    int i;
    memset(s,0,sizeof(aw_alchemy_slot_t)*AW_ALCHEMY_SLOTS);
    for(i=0;i<AW_ALCHEMY_SLOTS;i++){
        const ingredient_t *g=of_row(win->slot[i]);
        if(!g){win->slot[i]=-1;continue;}
        s[i].used=1;memcpy(s[i].e,g->e,sizeof(s[i].e));s[i].weight=g->weight;
    }
}
/* the potion the slots make now (OpenMW updateEffects) and its suggested name */
static void update(void){
    aw_alchemy_slot_t s[AW_ALCHEMY_SLOTS];
    player_stats(&win->skill,&win->intelligence,&win->luck);
    slots_of(s);
    win->nkeys=AW_AlchemyListEffects(s,win->keys);
    win->nfx=AW_AlchemyBrew(&win->d->set,s,win->quality,AW_AlchemyFactor(win->skill,win->intelligence,win->luck),
                            mgef_of,NULL,win->fx,&win->value);
    if(win->nfx<0)win->nfx=0;
    if(win->nkeys)effect_name(win->d,&win->keys[0],win->name,sizeof(win->name));
    else win->name[0]=0;
}
/* the carried ingredients and apparatus, read again (opening, and after Create) */
static void refresh(void){
    int i,best[AW_APPARATUS_TYPES];
    win->n=0;win->tools=0;win->full=0;
    AW_InventoryCarried(collect,NULL);win->reads++;
    if(win->n>1)qsort(win->list,(size_t)win->n,sizeof(*win->list),by_name);
    AW_AlchemyBestTools(win->tool_type,win->tool_quality,win->tools,win->quality,best);
    for(i=0;i<AW_APPARATUS_TYPES;i++)
        if(best[i]>=0)Q_strcpy_bounded(win->tool[i],win->tool_name[best[i]],sizeof(win->tool[i]));
        else win->tool[i][0]=0;
    for(i=0;i<AW_ALCHEMY_SLOTS;i++)if(win->slot[i]>=0 && (AW_ItemCount(&aw_state)<=win->slot[i] ||
                                     AW_ITEM_ROW(&aw_state,win->slot[i])->value<1))win->slot[i]=-1;
    if(win->sel>=win->n)win->sel=win->n?win->n-1:0;
    update();
}
static void message(const char *line){Q_strcpy_bounded(win->message,line,sizeof(win->message));}
static int add(int index){
    int i,free_slot=-1;
    if(!win || index<0 || index>=win->n)return 0;
    for(i=0;i<AW_ALCHEMY_SLOTS;i++){
        if(win->slot[i]==win->list[index].row){message(win->d->text[T_ONE_EACH]);return 0;}
        if(win->slot[i]<0 && free_slot<0)free_slot=i;
    }
    if(free_slot<0)return 0;
    win->slot[free_slot]=win->list[index].row;win->message[0]=0;
    update();return 1;
}
static int take_out(int slot){
    if(!win || slot<0 || slot>=AW_ALCHEMY_SLOTS || win->slot[slot]<0)return 0;
    win->slot[slot]=-1;win->message[0]=0;update();return 1;
}
/* the made potion's row in the made items: one made before with the same name, weight, value and effects (OpenMW
 * Alchemy::getRecord), else a new one in a random bottle (OpenMW addPotion: one of six looks); -1 no room */
static int potion_record(float weight){
    aw_made_item_t m;int i,k,n=AW_MadeItemCount(),tier;
    for(i=0;i<n;i++){
        const aw_made_item_t *o=AW_MadeItemAt(i);
        if(!o || o->cast_type!=AW_MADE_POTION || strcmp(o->name,win->name) || o->charge!=weight ||
           o->charge_max!=(float)win->value || o->effects!=win->nfx)continue;
        for(k=0;k<win->nfx;k++){
            aw_spell_effect_t e;spell_effect(&win->fx[k],&e);
            if(memcmp(&e,&o->effect[k],sizeof(e)))break;
        }
        if(k==win->nfx)return i;
    }
    if(!win->d->tiers)return -1;
    memset(&m,0,sizeof(m));
    tier=rand()%win->d->tiers;
    Q_strcpy_bounded(m.base,win->d->tier[tier],sizeof(m.base));Q_strcpy_bounded(m.name,win->name,sizeof(m.name));
    m.charge=weight;m.charge_max=(float)win->value;m.cast_type=AW_MADE_POTION;m.effects=win->nfx;
    for(k=0;k<win->nfx;k++)spell_effect(&win->fx[k],&m.effect[k]);
    return AW_MadeItemAdd(&m);
}
/* one of each ingredient in the slots used up (OpenMW removeIngredients) */
static void use_up(void){
    int i;
    for(i=0;i<AW_ALCHEMY_SLOTS;i++){
        char id[64];
        if(win->slot[i]<0 || win->slot[i]>=AW_ItemCount(&aw_state))continue;
        Q_strcpy_bounded(id,AW_ITEM_ID(&aw_state,win->slot[i]),sizeof(id));
        AW_ItemAdd(&aw_state,id,-1);
        if(AW_ITEM_ROW(&aw_state,win->slot[i])->value<1)win->slot[i]=-1;
    }
}
/* Create (OpenMW Alchemy::create with a count of one and createSingle) */
static int create_once(void);
static int create(void){
    double t0=Sys_FloatTime();int r=create_once();
    last_create_ms=(Sys_FloatTime()-t0)*1000;
    return r;
}
static int create_once(void){
    aw_alchemy_slot_t s[AW_ALCHEMY_SLOTS];float factor,weight;int ready,roll,record;char id[32];
    if(!win)return 0;
    update();slots_of(s);
    ready=AW_AlchemyReady(s,win->quality);
    if(ready==AW_ALCHEMY_NO_MORTAR){message(win->d->text[T_NO_MORTAR]);notice(win->message);return 0;}
    if(ready==AW_ALCHEMY_TOO_FEW){message(win->d->text[T_TOO_FEW]);notice(win->message);return 0;}
    if(win->d->set.loaded!=AW_ALCHEMY_SETTINGS_ALL){message("Alchemy settings missing from this image.");return 0;}
    factor=AW_AlchemyFactor(win->skill,win->intelligence,win->luck);
    roll=rand()%100;weight=AW_AlchemyWeight(s);
    if(ready==AW_ALCHEMY_NO_EFFECTS || !AW_AlchemySucceeds(factor,roll,win->nfx)){
        use_up();brews_failed++;
        message(win->d->text[T_FAILED]);notice(win->message);sound(win->d,S_FAIL);
        Con_Printf("Alchemy: potion failed (roll %d, factor %.1f, %d effects).\n",roll,factor,win->nfx);
        refresh();return 0;
    }
    record=potion_record(weight);
    if(record<0){message("No room for another kind of made potion.");Con_Printf("Alchemy: made items full.\n");return 0;}
    Q_snprintf(id,sizeof(id),AW_MADE_ITEM_PREFIX "%d",record);
    if(!AW_ItemAdd(&aw_state,id,1)){message("The potion cannot be carried.");return 0;}
    use_up();brews++;
    AW_LevelupUse(SKILL_ALCHEMY,USE_CREATE_POTION,1);
    message(win->d->text[T_SUCCESS]);notice(win->message);sound(win->d,S_SUCCESS);
    {int k;Con_Printf("Alchemy: created %s (%s): value %d, weight %.2f, roll %d, factor %.1f;",win->name,id,win->value,weight,roll,factor);
     for(k=0;k<win->nfx;k++)Con_Printf(" effect %d arg %d magnitude %d duration %d;",win->fx[k].effect,
                                       win->fx[k].arg==0xFF?-1:win->fx[k].arg,win->fx[k].magnitude,win->fx[k].duration);
     Con_Printf("\n");}
    refresh();return 1;
}

static void small(int x,int y,int width,const char *value,int color){
    char clipped[96];int n=(int)strlen(value),limit=width/4;
    if(limit<1)return;
    if(limit>(int)sizeof(clipped)-1)limit=sizeof(clipped)-1;
    if(n>limit)n=limit;
    memcpy(clipped,value,n);clipped[n]=0;
    if(value[n] && n>=3)memcpy(clipped+n-3,"...",3);
    AW_SmallStringColor(x,y,width,clipped,color);
}
extern int (*aw_title_bar)(int x,int y,int w,const char *title);
static void draw(void){
    int gold=AW_UIColor(223,199,144),muted=AW_UIColor(150,135,104),bright=AW_UIColor(255,244,214),i,y;char line[96];
    if(!win)return;
    AW_UIFill(0,0,320,200,AW_UIColor(0,0,0));AW_UIBox(2,2,316,196);
    AW_UISmallBegin();
    if(!aw_title_bar || !aw_title_bar(6,6,308,AW_StatsSkillName(SKILL_ALCHEMY)))AW_UITextCentred(6,6,308,12,AW_StatsSkillName(SKILL_ALCHEMY),gold);
    AW_UISmallEnd();
    AW_UIBox(4,18,156,152);AW_UIBox(160,18,156,152);
    /* the apparatus, best of each type */
    small(8,22,148,win->d->text[T_APPARATUS],muted);
    for(i=0;i<AW_APPARATUS_TYPES;i++){
        if(win->tool[i][0])Q_snprintf(line,sizeof(line),"%s (%.1f)",win->tool[i],win->quality[i]);
        else Q_snprintf(line,sizeof(line),"-");
        small(12,30+i*8,144,line,win->tool[i][0]?gold:muted);
    }
    /* the four slots */
    small(8,W_SLOT_Y-8,148,win->d->text[T_INGREDIENTS],muted);
    for(i=0;i<AW_ALCHEMY_SLOTS;i++){
        const ingredient_t *g=of_row(win->slot[i]);
        Q_snprintf(line,sizeof(line),"%d  %s",i+1,g?g->name:"-");
        small(12,W_SLOT_Y+i*8,144,line,g?gold:muted);
    }
    /* the potion's effects, as the skill reveals them */
    small(8,108,148,win->d->text[T_EFFECTS],muted);
    for(i=0,y=116;i<win->nfx && y<=164;i++){
        char name[48];
        if(!AW_AlchemyPotionVisible(win->skill,win->d->set.wort,i))continue;
        effect_name(win->d,&win->fx[i],name,sizeof(name));
        Q_snprintf(line,sizeof(line),"%s %u for %us",name,(unsigned)win->fx[i].magnitude,(unsigned)win->fx[i].duration);
        small(12,y,144,line,gold);y+=8;
    }
    if(!win->nfx && win->nkeys)small(12,116,144,"(too weak to keep an effect)",muted);
    /* the carried ingredients */
    small(W_LIST_X,22,140,win->d->text[T_INGREDIENTS],muted);
    if(!win->n)small(W_LIST_X+4,W_LIST_Y,136,"None carried.",muted);
    for(i=0;i<W_VISIBLE && win->top+i<win->n;i++){
        int r=win->top+i,used=0,k;
        for(k=0;k<AW_ALCHEMY_SLOTS;k++)used|=win->slot[k]==win->list[r].row;
        if(r==win->sel)AW_UIFill(W_LIST_X-2,W_LIST_Y+i*W_ROW-1,W_SCROLL_X-W_LIST_X,W_ROW,AW_UIColor(44,36,20));
        Q_snprintf(line,sizeof(line),"%s%s (%ld)",used?"* ":"",win->list[r].name,(long)AW_ITEM_ROW(&aw_state,win->list[r].row)->value);
        small(W_LIST_X,W_LIST_Y+i*W_ROW,W_SCROLL_X-W_LIST_X-2,line,r==win->sel?bright:gold);
    }
    if(win->n>W_VISIBLE)AW_UIScrollbar(W_SCROLL_X,W_LIST_Y,W_VISIBLE*W_ROW,win->n,W_VISIBLE,win->top);
    /* the selected ingredient's effects: a slot the skill does not reveal is "?" */
    if(win->n && win->sel<win->n){
        const ingredient_t *g=&win->list[win->sel];
        for(i=0;i<4;i++){
            char name[48];
            if(g->e[i].effect==AW_ALCHEMY_NO_EFFECT)continue;
            if(AW_AlchemyIngredientVisible(win->skill,win->d->set.wort,i))effect_name(win->d,&g->e[i],name,sizeof(name));
            else Q_snprintf(name,sizeof(name),"?");
            small(W_LIST_X+4,W_LIST_Y+W_VISIBLE*W_ROW+4+i*8,136,name,muted);
        }
    }
    Q_snprintf(line,sizeof(line),"%s: %s",win->d->text[T_NAME],win->name[0]?win->name:"-");
    small(8,174,196,line,gold);
    small(8,W_BUTTON_Y,196,win->message[0]?win->message:"Enter add  1-4 out  C create  Esc close",muted);
    /* the buttons: a filled field with the game's word (the ornate box frame left no room for the text) */
    AW_UIFill(W_CREATE_X,W_BUTTON_Y-2,W_BUTTON_W,9,AW_UIColor(48,39,22));small(W_CREATE_X+4,W_BUTTON_Y,W_BUTTON_W-6,win->d->text[T_CREATE],gold);
    AW_UIFill(W_CANCEL_X,W_BUTTON_Y-2,W_BUTTON_W,9,AW_UIColor(48,39,22));small(W_CANCEL_X+4,W_BUTTON_Y,W_BUTTON_W-6,win->d->text[T_CANCEL],gold);
}
static int key(int k,int mouse_x,int mouse_y){
    int top;
    if(!win)return 0;
    if(k==K_UPARROW || k=='w' || k==K_MWHEELUP)win->sel--;
    if(k==K_DOWNARROW || k=='s' || k==K_MWHEELDOWN)win->sel++;
    if(k==K_PGUP)win->sel-=W_VISIBLE;
    if(k==K_PGDN)win->sel+=W_VISIBLE;
    if(k==K_ENTER || k=='e')add(win->sel);
    if(k>='1' && k<='4')take_out(k-'1');
    if(k==K_BACKSPACE || k==K_DEL){int i;for(i=AW_ALCHEMY_SLOTS-1;i>=0 && win->slot[i]<0;i--);take_out(i);}
    if(k=='c')create();
    if(k==K_MOUSE1){
        if(mouse_y>=W_BUTTON_Y-2 && mouse_y<W_BUTTON_Y+8){
            if(mouse_x>=W_CREATE_X && mouse_x<W_CREATE_X+W_BUTTON_W){create();return 1;}
            if(mouse_x>=W_CANCEL_X && mouse_x<W_CANCEL_X+W_BUTTON_W)return 0;
        }
        top=AW_UIScrollHit(mouse_x,mouse_y,W_SCROLL_X,W_LIST_Y,W_VISIBLE*W_ROW,win->n,W_VISIBLE,win->top);
        if(top>=0){win->top=top;return 1;}
        if(mouse_x>=W_LIST_X && mouse_x<W_SCROLL_X && mouse_y>=W_LIST_Y && mouse_y<W_LIST_Y+W_VISIBLE*W_ROW){
            int r=win->top+(mouse_y-W_LIST_Y)/W_ROW;
            if(r<win->n){win->sel=r;add(r);}
        }
        if(mouse_x>=8 && mouse_x<156 && mouse_y>=W_SLOT_Y && mouse_y<W_SLOT_Y+AW_ALCHEMY_SLOTS*8)take_out((mouse_y-W_SLOT_Y)/8);
    }
    if(win->sel>=win->n)win->sel=win->n-1;
    if(win->sel<0)win->sel=0;
    if(win->sel<win->top)win->top=win->sel;
    if(win->sel>=win->top+W_VISIBLE)win->top=win->sel-W_VISIBLE+1;
    return 1;
}
static void closed(void){
    if(!win)return;
    free(win->list);free(win->d);free(win);win=NULL;
}
static void open_window(void){
    double t0=Sys_FloatTime();int i;
    if(win)return;
    if(!(win=(window_t *)AW_TryCalloc(1,sizeof(*win))) || !(win->d=data_load())){
        closed();Con_Printf("Alchemy: not enough memory for the window.\n");return;
    }
    for(i=0;i<AW_ALCHEMY_SLOTS;i++)win->slot[i]=-1;
    refresh();
    if(!AW_WorldUIOpenPanel(draw,key,closed)){
        Con_Printf("Alchemy: the window cannot open now (close the console or other window first).\n");closed();return;
    }
    win->open_ms=(Sys_FloatTime()-t0)*1000;
    Con_Printf("Alchemy window: %d ingredients, %d apparatus carried; %lu bytes while open; opened in %.0f ms.\n",
               win->n,win->tools,(unsigned long)(sizeof(*win)+sizeof(*win->d)+(unsigned long)win->capacity*sizeof(*win->list)),
               win->open_ms);
}
static int use_item(const aw_inventory_item_t *it){
    double t0=Sys_FloatTime();int r=0;
    if(!it || !(it->flags&AW_INV_ALCHEMY))return 0;
    switch(it->alchemy_kind){
    case AW_ALCHEMY_POTION:r=drink(it);break;
    case AW_ALCHEMY_INGREDIENT:r=eat(it);break;
    case AW_ALCHEMY_APPARATUS:return AW_StateGet(&aw_state,AW_ITEM,it->id)>0?2:0;
    }
    last_use_ms=(Sys_FloatTime()-t0)*1000;
    return r;
}

/* ---- aw_inventory use "ID" / aw_inventory alchemy ... (test words) ---- */
static int command(void){
    aw_inventory_item_t it;
    if(cmd_source!=src_command || Cmd_Argc()<2)return 0;
    if(!Q_strcasecmp(Cmd_Argv(1),"use") && Cmd_Argc()==3){
        int r;
        if(!sv.active || svs.maxclients!=1){Con_Printf("Start or load a game first.\n");return 1;}
        if(!AW_InventoryRead(Cmd_Argv(2),&it) || AW_StateGet(&aw_state,AW_ITEM,it.id)<1){Con_Printf("Diagnostic use refused: not carried.\n");return 1;}
        if(!AW_InventoryUsable(&it)){Con_Printf("Diagnostic use refused: %s is not a potion, ingredient or apparatus.\n",it.id);return 1;}
        r=use_item(&it);
        if(r==2)open_window();
        Con_Printf("DIAGNOSTIC use %s: %s.\n",it.id,r==2?"alchemy window":r?"done":"refused");
        return 1;
    }
    if(Q_strcasecmp(Cmd_Argv(1),"alchemy"))return 0;
    if(Cmd_Argc()>=3 && !Q_strcasecmp(Cmd_Argv(2),"status")){
        int i;
        Con_Printf("Alchemy: %d drunk, %d eaten (%d without effect), %d potions made, %d failed; made items %d; an item "
                   "record %d bytes; last use %.1f ms, last create %.1f ms.\n",(int)drinks,(int)meals,(int)meals_empty,
                   (int)brews,(int)brews_failed,AW_MadeItemCount(),(int)sizeof(aw_inventory_item_t),last_use_ms,last_create_ms);
        if(!win){Con_Printf("Alchemy window: closed.\n");return 1;}
        Con_Printf("Alchemy window: skill %.0f, Intelligence %.0f, Luck %.0f, factor %.1f; %d ingredients carried.\n",win->skill,
                   win->intelligence,win->luck,AW_AlchemyFactor(win->skill,win->intelligence,win->luck),win->n);
        for(i=0;i<AW_APPARATUS_TYPES;i++)Con_Printf("  apparatus %d: %s %.2f\n",i,win->tool[i][0]?win->tool[i]:"-",win->quality[i]);
        for(i=0;i<AW_ALCHEMY_SLOTS;i++){const ingredient_t *g=of_row(win->slot[i]);Con_Printf("  slot %d: %s\n",i+1,g?g->name:"-");}
        for(i=0;i<win->nfx;i++){
            char name[48];effect_name(win->d,&win->fx[i],name,sizeof(name));
            Con_Printf("  effect %d: %s, %u for %u s%s\n",i,name,(unsigned)win->fx[i].magnitude,(unsigned)win->fx[i].duration,
                       AW_AlchemyPotionVisible(win->skill,win->d->set.wort,i)?"":" (not revealed)");
        }
        Con_Printf("  name %s, value %d\n",win->name[0]?win->name:"-",win->value);
        return 1;
    }
    if(!win){Con_Printf("Alchemy: the window is not open (aw_inventory use an apparatus first).\n");return 1;}
    if(Cmd_Argc()==4 && !Q_strcasecmp(Cmd_Argv(2),"add")){
        int i;
        for(i=0;i<win->n && AW_InventoryCompare(AW_ITEM_ID(&aw_state,win->list[i].row),Cmd_Argv(3));i++);
        if(i==win->n){Con_Printf("Alchemy: %s is not a carried ingredient.\n",Cmd_Argv(3));return 1;}
        win->sel=i;Con_Printf("DIAGNOSTIC alchemy add %s: %s.\n",Cmd_Argv(3),add(i)?"in a slot":win->message[0]?win->message:"refused");
        return 1;
    }
    if(Cmd_Argc()==4 && !Q_strcasecmp(Cmd_Argv(2),"remove")){take_out(Q_atoi(Cmd_Argv(3))-1);return 1;}
    if(Cmd_Argc()==3 && !Q_strcasecmp(Cmd_Argv(2),"create")){Con_Printf("DIAGNOSTIC alchemy create: %s.\n",create()?"made":win->message);return 1;}
    if(Cmd_Argc()==3 && !Q_strcasecmp(Cmd_Argv(2),"close")){AW_WorldUIClose();return 1;}
    Con_Printf("aw_inventory alchemy add \"ID\" | remove N | create | status | close\n");
    return 1;
}
static void open_hook(void){open_window();}
/* MADE-ITEM-NO-PICTURE-62: the picture of a made item (a made potion, an enchanted item) is its base item's: the
 * picture table is keyed by the masters' ids, aw_made_N has none */
static const char *icon_id(const char *id){
    const aw_made_item_t *m;size_t n=sizeof(AW_MADE_ITEM_PREFIX)-1;
    if(!id || strncmp(id,AW_MADE_ITEM_PREFIX,n) || !(m=AW_MadeItemAt(atoi(id+n))) || !m->base[0])return id;
    return m->base;
}
void AW_AlchemyInit(void){
    aw_inventory_use=use_item;aw_inventory_command=command;
    aw_worldui_use=use_item;aw_worldui_alchemy_open=open_hook;aw_worldui_icon_id=icon_id;
}
