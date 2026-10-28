/* SPDX-License-Identifier: GPL-2.0-or-later
 * The actor record (aw_actorstate.h, docs/ACTOR_STATE.md): the actor table's rows read from disk when needed, the
 * live records of the actors play has touched in a fixed pool, the dead counts. The rules of the calls are
 * OpenMW's script extensions' (apps/openmw/mwscript/statsextensions.cpp, aiextensions.cpp,
 * containerextensions.cpp; apps/openmw/mwmechanics/stat.cpp), written independently. */
#include <string.h>
#include "aw_actorstate.h"
#include "aw_tryalloc.h"

#define ACTB_BYTES 96
#define AINV_BYTES 6
#define AITM_BYTES 28
#define ASPT_BYTES 4
#define GOLD_ITEM 0          /* AITM row 0 is the gold item (tools/mwscript/actors.py) */

typedef struct {uint32_t offset,rows,bytes;} section_t;
typedef struct {
    aw_actorstate_io_t io;
    section_t actb,ainv,aitm,aspt,aspl,strs;
    aw_actor_t pool[AW_ACTOR_POOL];
    aw_actor_t player;
    uint16_t *dead;            /* per ACTB row */
    int nactors,cursor,player_row;
    aw_actorstate_stats_t stats;
} state_t;
static state_t *st;

#define U16(p) ((unsigned)(((p)[0]<<8)|(p)[1]))
static uint32_t u32(const unsigned char *p){return ((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|p[3];}
static float f32(const unsigned char *p){uint32_t u=u32(p);float f;memcpy(&f,&u,4);return f;}
static int fetch(uint32_t offset,void *out,uint32_t bytes){
    st->stats.reads++;
    return st->io.read && !st->io.read(st->io.context,offset,out,bytes);
}
static int find_section(const unsigned char *head,uint32_t head_bytes,const char *tag,section_t *out){
    unsigned n,i;
    memset(out,0,sizeof(*out));
    if(head_bytes<16)return 0;
    n=U16(head+6);
    for(i=0;i<n && 16+16*i+16<=head_bytes;i++){
        const unsigned char *d=head+16+16*i;
        if(!memcmp(d,tag,4)){out->offset=u32(d+4);out->rows=u32(d+8);out->bytes=u32(d+12);return 1;}
    }
    return 0;
}
static char fold(char c){return c>='A' && c<='Z'?(char)(c+32):c;}
/* String INDEX of STRS, folded, into OUT (CAPACITY bytes). */
static int string_of(int index,char *out,int capacity){
    unsigned char b[4];int n;
    out[0]=0;
    if(index<0 || (uint32_t)index>=st->strs.rows || !fetch(st->strs.offset+4u*(uint32_t)index,b,4))return 0;
    if(!fetch(st->strs.offset+4u*st->strs.rows+u32(b),out,(uint32_t)capacity-1)){
        /* near the end of the file: read what is there, a byte at a time */
        for(n=0;n<capacity-1;n++)if(!fetch(st->strs.offset+4u*st->strs.rows+u32(b)+(uint32_t)n,out+n,1))break;
        out[n]=0;
    }
    out[capacity-1]=0;
    for(n=0;out[n];n++)out[n]=fold(out[n]);
    return 1;
}

void AW_ActorStateClose(void){
    if(!st)return;
    if(st->dead)free(st->dead);
    free(st);st=NULL;
}
int AW_ActorStateReady(void){return st!=NULL;}
int AW_ActorCount(void){return st?st->nactors:0;}
int AW_ActorStateOpen(const unsigned char *head,uint32_t head_bytes,const aw_actorstate_io_t *io){
    section_t actb;
    AW_ActorStateClose();
    if(!head || !io || !io->read || !find_section(head,head_bytes,"ACTB",&actb) || !actb.rows ||
       actb.bytes!=actb.rows*ACTB_BYTES)return 0;
    if(!(st=(state_t *)AW_TryMalloc(sizeof(state_t))))return 0;
    memset(st,0,sizeof(*st));
    st->io=*io;st->actb=actb;
    find_section(head,head_bytes,"AINV",&st->ainv);find_section(head,head_bytes,"AITM",&st->aitm);
    find_section(head,head_bytes,"ASPT",&st->aspt);find_section(head,head_bytes,"ASPL",&st->aspl);
    find_section(head,head_bytes,"STRS",&st->strs);
    st->nactors=(int)actb.rows;
    if(!(st->dead=(uint16_t *)AW_TryMalloc(sizeof(uint16_t)*(unsigned long)st->nactors))){AW_ActorStateClose();return 0;}
    memset(st->dead,0,sizeof(uint16_t)*(unsigned long)st->nactors);
    st->player_row=AW_ActorFind("player");
    return 1;
}
const aw_actorstate_stats_t *AW_ActorStateStats(void){static aw_actorstate_stats_t none;return st?&st->stats:&none;}
unsigned long AW_ActorStateResident(void){
    return st?(unsigned long)sizeof(state_t)+sizeof(uint16_t)*(unsigned long)st->nactors:0;
}

/* --- the table on disk --- */
int AW_ActorBase(int row,aw_actor_base_t *o){
    unsigned char r[ACTB_BYTES];int i;
    if(!st || row<0 || row>=st->nactors || !fetch(st->actb.offset+(uint32_t)row*ACTB_BYTES,r,ACTB_BYTES))return 0;
    o->id=(uint16_t)U16(r);o->kind=r[2];o->flags=r[3];o->level=(short)U16(r+4);
    for(i=0;i<8;i++)o->attributes[i]=(unsigned short)U16(r+6+2*i);
    memcpy(o->skills,r+22,27);
    o->hello=r[49];o->fight=r[50];o->flee=r[51];o->alarm=r[52];o->disposition=r[53];o->reputation=r[54];
    o->rank=(short)(signed char)r[55];
    o->health=(unsigned short)U16(r+56);o->magicka=(unsigned short)U16(r+58);o->fatigue=(unsigned short)U16(r+60);
    o->race=(uint16_t)U16(r+62);o->clas=(uint16_t)U16(r+64);o->faction=(uint16_t)U16(r+66);o->gold=u32(r+68);
    o->inv_first=(uint16_t)U16(r+72);o->inv_count=(uint16_t)U16(r+74);
    o->spell_first=(uint16_t)U16(r+76);o->spell_count=(uint16_t)U16(r+78);
    o->weapon=r[80];o->type=r[81];
    for(i=0;i<6;i++)o->attack[i]=(unsigned short)U16(r+82+2*i);
    o->soul=(unsigned short)U16(r+94);
    return 1;
}
int AW_ActorItem(int item,aw_item_t *o){
    unsigned char r[AITM_BYTES];
    if(!st || item<0 || (uint32_t)item>=st->aitm.rows || !fetch(st->aitm.offset+(uint32_t)item*AITM_BYTES,r,AITM_BYTES))return 0;
    o->id=(uint16_t)U16(r);o->kind=r[2];o->type=r[3];o->health=(unsigned short)U16(r+4);o->rating=(unsigned short)U16(r+6);
    memcpy(o->damage,r+8,6);o->flags=(unsigned short)U16(r+14);o->weight=f32(r+16);o->speed=f32(r+20);o->reach=f32(r+24);
    return 1;
}
int AW_ActorFind(const char *id){
    char want[64],have[64];int low=0,high,i;
    if(!st || !id)return AW_ACTOR_NONE;
    for(i=0;i<63 && id[i];i++)want[i]=fold(id[i]);
    want[i]=0;
    st->stats.finds++;
    high=st->nactors-1;
    while(low<=high){
        int mid=(low+high)/2,cmp;unsigned char b[2];
        if(!fetch(st->actb.offset+(uint32_t)mid*ACTB_BYTES,b,2) || !string_of((int)U16(b),have,sizeof(have)))return AW_ACTOR_NONE;
        /* the builder sorts by the folded id's bytes (cp1252): an unsigned compare */
        {const unsigned char *x=(const unsigned char *)have,*y=(const unsigned char *)want;
         while(*x && *x==*y){x++;y++;}cmp=*x<*y?-1:*x>*y;}
        if(!cmp)return mid;
        if(cmp<0)low=mid+1;else high=mid-1;
    }
    return AW_ACTOR_NONE;
}
int AW_ActorOfObject(int object,const uint16_t *oact,int count){
    return oact && object>=0 && object<count?(int)oact[object]:AW_ACTOR_NONE;
}

/* --- live records --- */
static void from_base(aw_actor_t *a,uint32_t reference,int row){
    aw_actor_base_t b;int i;
    memset(a,0,sizeof(*a));
    a->reference=reference;a->base=(uint16_t)row;a->flags=AWL_USED;
    if(!AW_ActorBase(row,&b))return;
    a->level=b.level;a->kind=b.kind;a->record_flags=b.flags;
    for(i=0;i<8;i++)a->attr_base[i]=(short)(b.attributes[i]>32767?32767:b.attributes[i]);
    for(i=0;i<27;i++)a->skill_base[i]=b.skills[i];
    a->dyn_base[0]=a->dyn_cur[0]=b.health;a->dyn_base[1]=a->dyn_cur[1]=b.magicka;a->dyn_base[2]=a->dyn_cur[2]=b.fatigue;
    a->ai[0]=b.hello;a->ai[1]=b.fight;a->ai[2]=b.flee;a->ai[3]=b.alarm;a->disposition=b.disposition;
}
aw_actor_t *AW_ActorPlayer(void){
    if(!st)return NULL;
    if(!(st->player.flags&AWL_USED)){
        if(st->player_row!=AW_ACTOR_NONE)from_base(&st->player,AW_ACTOR_PLAYER_REF,st->player_row);
        else{memset(&st->player,0,sizeof(st->player));st->player.base=AW_ACTOR_NONE;}
        st->player.reference=AW_ACTOR_PLAYER_REF;st->player.flags|=AWL_USED;
    }
    return &st->player;
}
aw_actor_t *AW_ActorGet(uint32_t reference,int row,int create){
    int i,free_slot=-1;
    if(!st)return NULL;
    if(reference==AW_ACTOR_PLAYER_REF)return AW_ActorPlayer();
    for(i=0;i<AW_ACTOR_POOL;i++){
        aw_actor_t *a=&st->pool[i];
        if(!(a->flags&AWL_USED)){if(free_slot<0)free_slot=i;continue;}
        if(a->reference==reference && (row==AW_ACTOR_NONE || a->base==row))return a;
    }
    if(!create || row<0 || row>=st->nactors)return NULL;
    if(free_slot<0){
        /* full: drop an unchanged record (it comes back from its base when needed again) */
        for(i=0;i<AW_ACTOR_POOL;i++){
            int k=(st->cursor+i)%AW_ACTOR_POOL;
            if(!(st->pool[k].flags&AWL_CHANGED)){free_slot=k;st->stats.evicted++;break;}
        }
        if(free_slot<0){st->stats.full++;return NULL;}
        st->cursor=(free_slot+1)%AW_ACTOR_POOL;
    }
    from_base(&st->pool[free_slot],reference,row);
    st->stats.created++;
    return &st->pool[free_slot];
}
static void changed(aw_actor_t *a){
    if(!(a->flags&AWL_CHANGED))st->stats.changed++;
    a->flags|=AWL_CHANGED;
}

/* --- stats --- */
static float clampf(float v,float lo,float hi){return v<lo?lo:v>hi?hi:v;}
static short to_short(float v){v=clampf(v,-32768.0f,32767.0f);return (short)(v<0?v-0.5f:v+0.5f);}
static int dynamic(int stat){return stat>=AWA_HEALTH && stat<=AWA_FATIGUE?stat-AWA_HEALTH:-1;}
float AW_ActorStat(const aw_actor_t *a,int stat){
    int d=dynamic(stat);
    if(!a)return 0;
    if(stat>=AWA_ATTRIBUTE && stat<AWA_ATTRIBUTE+8){
        float v=(float)a->attr_base[stat]+a->attr_mod[stat];return v<0?0:v;}
    if(stat>=AWA_SKILL && stat<AWA_SKILL+27){
        float v=(float)a->skill_base[stat-AWA_SKILL]+a->skill_mod[stat-AWA_SKILL];return v<0?0:v;}
    if(d>=0){
        /* GetMagicka never reads below 0 (OpenMW OpGetDynamic) */
        return d==1 && a->dyn_cur[1]<0?0:a->dyn_cur[d];
    }
    switch(stat){
    case AWA_LEVEL:return a->level;
    case AWA_HELLO:case AWA_FIGHT:case AWA_FLEE:case AWA_ALARM:return a->ai[stat-AWA_HELLO];
    case AWA_DISPOSITION:return a->kind==0?a->disposition:0;
    case AWA_DEAD:return (a->flags&AWL_DEAD)?1:0;
    }
    return 0;
}
/* DynamicStat::setCurrent (OpenMW stat.cpp): an increase stops at the base unless ABOVE; a decrease stops at 0
 * unless BELOW. */
static void set_current(aw_actor_t *a,int d,float value,int below,int above){
    float *cur=&a->dyn_cur[d],base=a->dyn_base[d];
    if(value>*cur){
        if(value<=base || above)*cur=value;
        else if(*cur>base)return;
        else *cur=base;
    }else if(value>0 || below)*cur=value;
    else if(*cur>0)*cur=0;
}
void AW_ActorSetStat(aw_actor_t *a,int stat,float value){
    int d=dynamic(stat);
    if(!a)return;
    if(stat>=AWA_ATTRIBUTE && stat<AWA_ATTRIBUTE+8){
        /* SetStrength etc.: the base, the modifier and the damage cleared (setBase(value, true)) */
        a->attr_base[stat]=to_short(value);a->attr_mod[stat]=0;
    }else if(stat>=AWA_SKILL && stat<AWA_SKILL+27){
        if(a->kind!=0)return;                      /* creatures have no skills of their own to set */
        a->skill_base[stat-AWA_SKILL]=to_short(value);a->skill_mod[stat-AWA_SKILL]=0;
    }else if(d>=0){
        /* SetHealth etc.: the base, then the current to it (may rise above, OpenMW OpSetDynamic) */
        a->dyn_base[d]=value;set_current(a,d,value,1,1);
    }else switch(stat){
    case AWA_LEVEL:a->level=to_short(value);break;
    case AWA_HELLO:case AWA_FIGHT:case AWA_FLEE:case AWA_ALARM:
        a->ai[stat-AWA_HELLO]=(unsigned char)clampf(value,0,255);break;   /* kept in a byte, as the record's AIDT */
    case AWA_DISPOSITION:if(a->kind!=0)return;a->disposition=to_short(value);break;
    default:return;
    }
    changed(a);
}
/* modStat (OpenMW statsextensions.cpp): the modified value clamped to 100 unless fortified, the base 0..100. */
static void mod_stat(short *base_out,short *mod_out,float amount){
    float base=*base_out,modifier=*mod_out,modified=base+modifier,next;
    if((modifier<=0 || base>=100) && amount>0)amount=clampf(100-modified,0,amount);
    next=modified+amount;
    if(next<0){if(modified>=0)next=0;else if(next<modified)next=modified;}
    *base_out=to_short(clampf(base+amount,0,100));
    *mod_out=to_short(next-*base_out);
}
void AW_ActorModStat(aw_actor_t *a,int stat,float value){
    int d=dynamic(stat);
    if(!a)return;
    if(stat>=AWA_ATTRIBUTE && stat<AWA_ATTRIBUTE+8)mod_stat(&a->attr_base[stat],&a->attr_mod[stat],value);
    else if(stat>=AWA_SKILL && stat<AWA_SKILL+27){
        if(a->kind!=0)return;
        mod_stat(&a->skill_base[stat-AWA_SKILL],&a->skill_mod[stat-AWA_SKILL],value);
    }else if(d>=0){
        /* ModHealth etc.: base + VALUE (not below 0, fatigue may), current + VALUE (OpenMW OpModDynamic) */
        float cur=a->dyn_cur[d],base=a->dyn_base[d]+value;
        if(d!=2 && base<0)base=0;
        a->dyn_base[d]=base;set_current(a,d,cur+value,1,1);
    }else switch(stat){
    case AWA_LEVEL:a->level=to_short((float)a->level+value);break;
    case AWA_HELLO:case AWA_FIGHT:case AWA_FLEE:case AWA_ALARM:
        a->ai[stat-AWA_HELLO]=(unsigned char)clampf((float)a->ai[stat-AWA_HELLO]+value,0,255);break;
    case AWA_DISPOSITION:if(a->kind!=0)return;a->disposition=to_short((float)a->disposition+value);break;
    default:return;
    }
    changed(a);
}
void AW_ActorModCurrent(aw_actor_t *a,int stat,float value){
    int d=dynamic(stat);
    if(!a || d<0)return;
    /* ModCurrentHealth etc.: current only, never above the base; fatigue may go below 0 (a knockdown, which the
     * combat layer applies: OpenMW OpModCurrentDynamic) */
    set_current(a,d,a->dyn_cur[d]+value,d==2,0);
    if(d==0 && a->dyn_cur[0]<=0 && !(a->flags&AWL_DEAD) && a->dyn_base[0]>0)AW_ActorKill(a);
    changed(a);
}
float AW_ActorRatio(const aw_actor_t *a,int stat){
    int d=dynamic(stat);
    if(!a || d<0)return 0;
    return a->dyn_base[d]==0?1.0f:a->dyn_cur[d]/a->dyn_base[d];
}
void AW_ActorKill(aw_actor_t *a){
    if(!a || (a->flags&AWL_DEAD))return;
    a->flags|=AWL_DEAD|AWL_DIED;
    if(a->dyn_cur[0]>0)a->dyn_cur[0]=0;
    if(a->base<st->nactors && st->dead[a->base]<0xFFFF)st->dead[a->base]++;
    changed(a);
}
int AW_ActorOnDeath(aw_actor_t *a){
    if(!a || !(a->flags&AWL_DIED))return 0;
    a->flags&=~AWL_DIED;
    return 1;
}
int AW_ActorDeadCount(int row){return st && row>=0 && row<st->nactors?st->dead[row]:0;}

/* --- inventory --- */
static int base_count(const aw_actor_t *a,int item,int *equipped){
    aw_actor_base_t b;int i,n=0;unsigned char e[AINV_BYTES];
    if(equipped)*equipped=0;
    if(a->base==AW_ACTOR_NONE || !AW_ActorBase(a->base,&b))return 0;
    if(item==GOLD_ITEM)n+=(int)(b.gold>32767?32767:b.gold);
    for(i=0;i<b.inv_count;i++){
        if(!fetch(st->ainv.offset+(uint32_t)(b.inv_first+i)*AINV_BYTES,e,AINV_BYTES))break;
        if((int)U16(e)==item){n+=(int16_t)U16(e+2);if(equipped && (e[4]&AWI_INV_EQUIPPED))*equipped=1;}
    }
    return n;
}
int AW_ActorItemCount(const aw_actor_t *a,int item){
    int i,n;
    if(!st || !a || item<0)return 0;
    n=base_count(a,item,NULL);
    for(i=0;i<a->nitems;i++)if(a->items[i].item==item)n+=a->items[i].change;
    return n<0?0:n;
}
static int item_change(aw_actor_t *a,int item,int change){
    int i;
    for(i=0;i<a->nitems;i++)if(a->items[i].item==item)break;
    if(i==a->nitems){
        if(a->nitems==AW_ACTOR_ITEMS)return 0;
        a->items[i].item=(uint16_t)item;a->items[i].change=0;a->nitems++;
    }
    a->items[i].change=(int16_t)clampf((float)a->items[i].change+change,-32768,32767);
    if(!a->items[i].change)a->items[i]=a->items[--a->nitems];
    changed(a);
    return 1;
}
/* AddItem/RemoveItem: a negative count is read as the unsigned 16-bit number it is (OpenMW), 0 does nothing. */
static int script_count(int count){if(count<0)count=(int)(uint16_t)count;return count;}
int AW_ActorAddItem(aw_actor_t *a,int item,int count){
    if(!st || !a || item<0 || (uint32_t)item>=st->aitm.rows)return 0;
    count=script_count(count);
    if(!count)return 1;
    return item_change(a,item,count);
}
int AW_ActorRemoveItem(aw_actor_t *a,int item,int count){
    int have;
    if(!st || !a || item<0)return 0;
    count=script_count(count);have=AW_ActorItemCount(a,item);
    if(count>have)count=have;
    if(count<=0)return 0;
    return item_change(a,item,-count)?count:0;
}
int AW_ActorEquipped(const aw_actor_t *a,int entry){
    aw_actor_base_t b;unsigned char e[AINV_BYTES];
    if(!st || !a || a->base==AW_ACTOR_NONE || !AW_ActorBase(a->base,&b) || entry<0 || entry>=b.inv_count)return 0;
    if(!fetch(st->ainv.offset+(uint32_t)(b.inv_first+entry)*AINV_BYTES,e,AINV_BYTES))return 0;
    /* a worn item the scripts removed is no longer worn */
    return (e[4]&AWI_INV_EQUIPPED) && AW_ActorItemCount(a,(int)U16(e))>0;
}
int AW_ActorWeaponType(int row){
    aw_actor_base_t b;unsigned char e[AINV_BYTES];aw_item_t it;
    if(!st || !AW_ActorBase(row,&b) || b.weapon==0xFF || b.weapon>=b.inv_count)return -1;
    if(!fetch(st->ainv.offset+(uint32_t)(b.inv_first+b.weapon)*AINV_BYTES,e,AINV_BYTES))return -1;
    if(!AW_ActorItem((int)U16(e),&it) || it.kind!=AWK_WEAPON)return -1;
    return it.type;
}

/* --- spells --- */
static int base_spell(const aw_actor_t *a,int spell){
    aw_actor_base_t b;int i;unsigned char e[2];
    if(a->base==AW_ACTOR_NONE || !AW_ActorBase(a->base,&b))return 0;
    for(i=0;i<b.spell_count;i++){
        if(!fetch(st->aspl.offset+2u*(uint32_t)(b.spell_first+i),e,2))break;
        if((int)U16(e)==spell)return 1;
    }
    return 0;
}
int AW_ActorHasSpell(const aw_actor_t *a,int spell){
    int i;
    if(!st || !a || spell<0)return 0;
    for(i=0;i<a->nspells;i++)if(a->spells[i].spell==spell)return a->spells[i].change>0;
    return base_spell(a,spell);
}
static int spell_change(aw_actor_t *a,int spell,int has){
    int i,base;
    if(!st || !a || spell<0 || (uint32_t)spell>=st->aspt.rows)return 0;
    base=base_spell(a,spell);
    for(i=0;i<a->nspells;i++)if(a->spells[i].spell==spell)break;
    if(base==has){if(i<a->nspells){a->spells[i]=a->spells[--a->nspells];changed(a);}return 1;}
    if(i==a->nspells){if(a->nspells==AW_ACTOR_SPELLS)return 0;a->spells[i].spell=(uint16_t)spell;a->nspells++;}
    a->spells[i].change=(int16_t)(has?1:-1);
    changed(a);
    return 1;
}
/* GetCommonDisease / GetBlightDisease: any spell of TYPE (the ASPT row's type: 2 blight, 3 disease) among the
 * actor's base list and its changes (rule from OpenMW apps/openmw/mwmechanics/spells.cpp hasCommonDisease and
 * hasBlightDisease: a spell of that type in the actor's spell list) */
static int spell_type(int spell){
    unsigned char e[ASPT_BYTES];
    if(spell<0 || (uint32_t)spell>=st->aspt.rows || !fetch(st->aspt.offset+(uint32_t)spell*ASPT_BYTES,e,ASPT_BYTES))return -1;
    return e[2];
}
int AW_ActorHasSpellType(const aw_actor_t *a,int type){
    aw_actor_base_t b;int i,j,s;unsigned char e[2];
    if(!st || !a)return 0;
    for(i=0;i<a->nspells;i++)if(a->spells[i].change>0 && spell_type(a->spells[i].spell)==type)return 1;
    if(a->base==AW_ACTOR_NONE || !AW_ActorBase(a->base,&b))return 0;
    for(i=0;i<b.spell_count;i++){
        if(!fetch(st->aspl.offset+2u*(uint32_t)(b.spell_first+i),e,2))break;
        s=(int)U16(e);
        for(j=0;j<a->nspells;j++)if(a->spells[j].spell==s)break;
        if(j<a->nspells)continue;                  /* removed (an added one was counted above) */
        if(spell_type(s)==type)return 1;
    }
    return 0;
}
int AW_ActorAddSpell(aw_actor_t *a,int spell){return spell_change(a,spell,1);}
int AW_ActorRemoveSpell(aw_actor_t *a,int spell){return spell_change(a,spell,0);}

/* --- saved games: "AWAS" u8 version (1) u8 0 u16 records, u16 dead counts; then each record and each count,
 * big-endian; a record: u32 reference u16 base u16 flags i16 level i16 attr base/mod [16] i16 skill base/mod [54]
 * f32 dynamic base/current [6] u8 ai[4] i16 disposition u8 items u8 spells, then (u16 item i16 change) per item and
 * (u16 spell i16 change) per spell; a count: u16 base u16 count. The player's record is not here: its sheet is
 * saved with the character. --- */
#define RECORD_FIXED (4+2+2+2+32+108+24+4+2+2)
static unsigned char *put16(unsigned char *p,unsigned v){p[0]=(unsigned char)(v>>8);p[1]=(unsigned char)v;return p+2;}
static unsigned char *put32(unsigned char *p,uint32_t v){p[0]=(unsigned char)(v>>24);p[1]=(unsigned char)(v>>16);p[2]=(unsigned char)(v>>8);p[3]=(unsigned char)v;return p+4;}
static unsigned char *putf(unsigned char *p,float f){uint32_t u;memcpy(&u,&f,4);return put32(p,u);}
int AW_ActorStateExport(unsigned char *out,int capacity){
    int i,j,records=0,counts=0,need=10;unsigned char *p;
    if(!st)return 0;
    for(i=0;i<AW_ACTOR_POOL;i++)if((st->pool[i].flags&(AWL_USED|AWL_CHANGED))==(AWL_USED|AWL_CHANGED)){
        records++;need+=RECORD_FIXED+4*(st->pool[i].nitems+st->pool[i].nspells);}
    for(i=0;i<st->nactors;i++)if(st->dead[i]){counts++;need+=4;}
    if(!records && !counts)return 0;
    if(need>capacity)return -1;
    p=out;memcpy(p,"AWAS",4);p+=4;*p++=1;*p++=0;p=put16(p,(unsigned)records);p=put16(p,(unsigned)counts);
    for(i=0;i<AW_ACTOR_POOL;i++){
        const aw_actor_t *a=&st->pool[i];
        if((a->flags&(AWL_USED|AWL_CHANGED))!=(AWL_USED|AWL_CHANGED))continue;
        p=put32(p,a->reference);p=put16(p,a->base);p=put16(p,a->flags&(AWL_CHANGED|AWL_DEAD|AWL_DIED|AWL_COMBAT));
        p=put16(p,(unsigned)(uint16_t)a->level);
        for(j=0;j<8;j++){p=put16(p,(unsigned)(uint16_t)a->attr_base[j]);p=put16(p,(unsigned)(uint16_t)a->attr_mod[j]);}
        for(j=0;j<27;j++){p=put16(p,(unsigned)(uint16_t)a->skill_base[j]);p=put16(p,(unsigned)(uint16_t)a->skill_mod[j]);}
        for(j=0;j<3;j++){p=putf(p,a->dyn_base[j]);p=putf(p,a->dyn_cur[j]);}
        for(j=0;j<4;j++)*p++=a->ai[j];
        p=put16(p,(unsigned)(uint16_t)a->disposition);*p++=a->nitems;*p++=a->nspells;
        for(j=0;j<a->nitems;j++){p=put16(p,a->items[j].item);p=put16(p,(unsigned)(uint16_t)a->items[j].change);}
        for(j=0;j<a->nspells;j++){p=put16(p,a->spells[j].spell);p=put16(p,(unsigned)(uint16_t)a->spells[j].change);}
    }
    for(i=0;i<st->nactors;i++)if(st->dead[i]){p=put16(p,(unsigned)i);p=put16(p,st->dead[i]);}
    return (int)(p-out);
}
int AW_ActorStateImport(const unsigned char *data,int bytes){
    const unsigned char *p=data,*end=data+bytes;int i,j,records,counts;
    if(!st)return 0;
    memset(st->pool,0,sizeof(st->pool));memset(&st->player,0,sizeof(st->player));
    memset(st->dead,0,sizeof(uint16_t)*(unsigned long)st->nactors);
    if(!data || !bytes)return 1;                  /* a save without actor changes */
    if(bytes<10 || memcmp(p,"AWAS",4) || p[4]!=1)return 0;
    records=(int)U16(p+6);counts=(int)U16(p+8);p+=10;
    if(records>AW_ACTOR_POOL)return 0;
    for(i=0;i<records;i++){
        aw_actor_t *a=&st->pool[i];
        if(end-p<RECORD_FIXED)goto bad;
        a->reference=u32(p);a->base=(uint16_t)U16(p+4);a->flags=(uint16_t)(U16(p+6)|AWL_USED|AWL_CHANGED);p+=8;
        if(a->base>=st->nactors || a->reference==AW_ACTOR_PLAYER_REF)goto bad;
        a->level=(short)U16(p);p+=2;
        for(j=0;j<8;j++){a->attr_base[j]=(short)U16(p);a->attr_mod[j]=(short)U16(p+2);p+=4;}
        for(j=0;j<27;j++){a->skill_base[j]=(short)U16(p);a->skill_mod[j]=(short)U16(p+2);p+=4;}
        for(j=0;j<3;j++){a->dyn_base[j]=f32(p);a->dyn_cur[j]=f32(p+4);p+=8;
            if(!(a->dyn_base[j]>-1e7f && a->dyn_base[j]<1e7f) || !(a->dyn_cur[j]>-1e7f && a->dyn_cur[j]<1e7f))goto bad;}
        for(j=0;j<4;j++)a->ai[j]=*p++;
        a->disposition=(short)U16(p);a->nitems=p[2];a->nspells=p[3];p+=4;
        if(a->nitems>AW_ACTOR_ITEMS || a->nspells>AW_ACTOR_SPELLS || end-p<4*(a->nitems+a->nspells))goto bad;
        for(j=0;j<a->nitems;j++){a->items[j].item=(uint16_t)U16(p);a->items[j].change=(int16_t)U16(p+2);p+=4;
            if(a->items[j].item>=st->aitm.rows)goto bad;}
        for(j=0;j<a->nspells;j++){a->spells[j].spell=(uint16_t)U16(p);a->spells[j].change=(int16_t)U16(p+2);p+=4;
            if(a->spells[j].spell>=st->aspt.rows || (a->spells[j].change!=1 && a->spells[j].change!=-1))goto bad;}
        {aw_actor_base_t b;if(AW_ActorBase(a->base,&b)){a->kind=b.kind;a->record_flags=b.flags;}}
    }
    for(i=0;i<counts;i++){
        int row;
        if(end-p<4)goto bad;
        row=(int)U16(p);if(row>=st->nactors)goto bad;
        st->dead[row]=(uint16_t)U16(p+2);p+=4;
    }
    if(p!=end)goto bad;
    return 1;
bad:
    memset(st->pool,0,sizeof(st->pool));memset(st->dead,0,sizeof(uint16_t)*(unsigned long)st->nactors);
    return 0;
}
