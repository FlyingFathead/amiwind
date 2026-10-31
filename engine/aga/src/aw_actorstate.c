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
    section_t actb,ainv,aitm,aspt,aspl,aspc,aspe,aeff,amge,strs;
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
/* String INDEX of STRS into OUT (CAPACITY bytes), folded when FOLDED (the ids; a name to show keeps its case). */
static int string_at(int index,char *out,int capacity,int folded){
    unsigned char b[4];int n;
    out[0]=0;
    if(index<0 || (uint32_t)index>=st->strs.rows || !fetch(st->strs.offset+4u*(uint32_t)index,b,4))return 0;
    if(!fetch(st->strs.offset+4u*st->strs.rows+u32(b),out,(uint32_t)capacity-1)){
        /* near the end of the file: read what is there, a byte at a time */
        for(n=0;n<capacity-1;n++)if(!fetch(st->strs.offset+4u*st->strs.rows+u32(b)+(uint32_t)n,out+n,1))break;
        out[n]=0;
    }
    out[capacity-1]=0;
    if(folded)for(n=0;out[n];n++)out[n]=fold(out[n]);
    return 1;
}
static int string_of(int index,char *out,int capacity){return string_at(index,out,capacity,1);
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
    find_section(head,head_bytes,"ASPC",&st->aspc);
    find_section(head,head_bytes,"ASPE",&st->aspe);find_section(head,head_bytes,"AEFF",&st->aeff);
    find_section(head,head_bytes,"AMGE",&st->amge);    /* absent before v0.0.58: no effects to make or enchant with */     /* absent in a table before v0.0.58: no spells for sale */
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
/* A cure (v0.0.57, MWScript Cast of Cure Common Disease / Cure Blight Disease): every spell of TYPE goes from the
 * actor's list (rule from OpenMW apps/openmw/mwmechanics/spells.cpp purgeCommonDisease / purgeBlightDisease).
 * Returns how many were removed. */
int AW_ActorRemoveSpellType(aw_actor_t *a,int type){
    aw_actor_base_t b;int i,s,removed=0;unsigned char e[2];
    if(!st || !a)return 0;
    for(i=a->nspells-1;i>=0;i--)
        if(a->spells[i].change>0 && spell_type(a->spells[i].spell)==type && spell_change(a,a->spells[i].spell,0))removed++;
    if(a->base!=AW_ACTOR_NONE && AW_ActorBase(a->base,&b))
        for(i=0;i<b.spell_count;i++){
            if(!fetch(st->aspl.offset+2u*(uint32_t)(b.spell_first+i),e,2))break;
            s=(int)U16(e);
            if(spell_type(s)==type && AW_ActorHasSpell(a,s) && spell_change(a,s,0))removed++;
        }
    return removed;
}
int AW_ActorAddSpell(aw_actor_t *a,int spell){return spell_change(a,spell,1);}
int AW_ActorRemoveSpell(aw_actor_t *a,int spell){return spell_change(a,spell,0);}
int AW_ActorSpellInfo(int spell,int *type,char *name,int capacity,int *cost){
    unsigned char e[4];
    if(name && capacity>0)name[0]=0;
    if(cost)*cost=0;
    if(type)*type=st?spell_type(spell):-1;
    if(!st || spell<0 || (uint32_t)spell>=st->aspc.rows || !fetch(st->aspc.offset+4u*(uint32_t)spell,e,4))return 0;
    if(cost)*cost=(int)U16(e+2);
    if(name && U16(e)!=0xFFFF)string_at((int)U16(e),name,capacity,0);
    return 1;
}
int AW_ActorSpells(const aw_actor_t *a,int *out,int max){
    aw_actor_base_t b;int i,n=0;unsigned char e[2];
    if(!st || !a)return 0;
    if(a->base!=AW_ACTOR_NONE && AW_ActorBase(a->base,&b))
        for(i=0;i<b.spell_count && n<max;i++){
            if(!fetch(st->aspl.offset+2u*(uint32_t)(b.spell_first+i),e,2))break;
            if(AW_ActorHasSpell(a,(int)U16(e)))out[n++]=(int)U16(e);
        }
    for(i=0;i<a->nspells && n<max;i++)if(a->spells[i].change>0 && !base_spell(a,a->spells[i].spell))out[n++]=a->spells[i].spell;
    return n;
}

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
/* The items A holds now (its base list and the changes, gold not counted: it is the record's gold), with counts and
 * whether equipped; up to MAX; the count of distinct items. For a merchant's stock (the dialogue's Barter). */
int AW_ActorItems(const aw_actor_t *a,int *items,int *counts,int *equipped,int max){
    aw_actor_base_t b;int i,j,n=0,seen;unsigned char e[AINV_BYTES];
    if(!st || !a)return 0;
    if(a->base!=AW_ACTOR_NONE && AW_ActorBase(a->base,&b))
        for(i=0;i<b.inv_count && n<max;i++){
            int item;
            if(!fetch(st->ainv.offset+(uint32_t)(b.inv_first+i)*AINV_BYTES,e,AINV_BYTES))break;
            item=(int)U16(e);seen=0;
            if(item==GOLD_ITEM)continue;
            for(j=0;j<n;j++)if(items[j]==item)seen=1;
            if(seen || AW_ActorItemCount(a,item)<=0)continue;
            items[n]=item;counts[n]=AW_ActorItemCount(a,item);base_count(a,item,&equipped[n]);n++;
        }
    for(i=0;i<a->nitems && n<max;i++){
        int item=a->items[i].item;seen=0;
        if(item==GOLD_ITEM)continue;
        for(j=0;j<n;j++)if(items[j]==item)seen=1;
        if(seen || AW_ActorItemCount(a,item)<=0)continue;
        items[n]=item;counts[n]=AW_ActorItemCount(a,item);equipped[n]=0;n++;
    }
    return n;
}
/* The id of item ITEM (AITM), folded; 0 when there is none */
int AW_ActorItemId(int item,char *out,int capacity){
    aw_item_t it;
    if(capacity>0)out[0]=0;
    return AW_ActorItem(item,&it) && string_of((int)it.id,out,capacity);
}
/* --- things sold to merchants that did not stock them (BARTER-SOLD-ITEM-LOST-58) ---
 * They go into that merchant's stock and can be bought back, as in the original (OpenMW moves them into its
 * container). Allocated only once such a thing is sold (nothing kept before), carried in the saved game (AWSL). */
typedef struct {uint32_t reference;char id[40];int16_t count;} sold_t;
/* bounded: a playthrough never sells this many kinds to merchants that do not stock them; past it the oldest entry
 * goes (that merchant forgets it, as a restock would) */
#define AW_SOLD_MAX 1024
#define AW_SOLD_ENTRY 48            /* sizeof(sold_t), at most (46 on the 68k, 48 where uint32_t aligns to 4) */
AW_RESIDENT_GROWS("barter sold things (BARTER-SOLD-ITEM-LOST-58)",AW_SOLD_MAX,AW_SOLD_ENTRY);
typedef char aw_sold_entry_fits[sizeof(sold_t)<=AW_SOLD_ENTRY?1:-1];
static sold_t *sold;static int sold_count,sold_capacity;
static void sold_remove(int i){
    if(i<0 || i>=sold_count)return;
    memmove(sold+i,sold+i+1,sizeof(sold_t)*(size_t)(sold_count-i-1));sold_count--;   /* the order stays by age */
}
static int ci_equal(const char *a,const char *b){while(*a && fold(*a)==fold(*b)){a++;b++;}return !*a && !*b;}
void AW_SoldReset(void){free(sold);sold=NULL;sold_count=sold_capacity=0;}
int AW_SoldCount(void){return sold_count;}
int AW_SoldMax(void){return AW_SOLD_MAX;}
int AW_SoldAt(int i,uint32_t *reference,char *id,int capacity,int *count){
    if(i<0 || i>=sold_count || capacity<1)return 0;
    *reference=sold[i].reference;*count=sold[i].count;
    strncpy(id,sold[i].id,(size_t)capacity-1);id[capacity-1]=0;
    return 1;
}
int AW_SoldAdd(uint32_t reference,const char *id,int delta){
    int i;
    if(!id || !*id || strlen(id)>=sizeof(sold[0].id))return 0;
    for(i=0;i<sold_count;i++)if(sold[i].reference==reference && ci_equal(sold[i].id,id))break;
    if(i==sold_count){
        if(delta<=0)return 0;
        if(sold_count==AW_SOLD_MAX){sold_remove(0);i=sold_count;}   /* the oldest is forgotten */
        if(sold_count==sold_capacity){
            int grow=sold_capacity?sold_capacity*2:16;sold_t *n;
            if(grow>AW_SOLD_MAX)grow=AW_SOLD_MAX;
            n=(sold_t *)AW_TryMalloc(sizeof(sold_t)*(unsigned long)grow);
            if(!n)return 0;
            if(sold)memcpy(n,sold,sizeof(sold_t)*(size_t)sold_count);
            free(sold);sold=n;sold_capacity=grow;
        }
        sold[i].reference=reference;strcpy(sold[i].id,id);sold[i].count=0;sold_count++;
    }
    if(sold[i].count+delta<0 || sold[i].count+delta>32767)return 0;
    sold[i].count=(int16_t)(sold[i].count+delta);
    if(!sold[i].count)sold_remove(i);
    return 1;
}
/* "AWSL" u16 rows, then per row: u32 reference, u8 id length, the id, i16 count. The bytes written, -1 no room. */
int AW_SoldExport(unsigned char *out,int capacity){
    int k,need=6;unsigned char *q=out;
    for(k=0;k<sold_count;k++)need+=7+(int)strlen(sold[k].id);
    if(need>capacity)return -1;
    memcpy(q,"AWSL",4);q[4]=(unsigned char)(sold_count>>8);q[5]=(unsigned char)sold_count;q+=6;
    for(k=0;k<sold_count;k++){
        int len=(int)strlen(sold[k].id);uint16_t c=(uint16_t)sold[k].count;
        q[0]=(unsigned char)(sold[k].reference>>24);q[1]=(unsigned char)(sold[k].reference>>16);
        q[2]=(unsigned char)(sold[k].reference>>8);q[3]=(unsigned char)sold[k].reference;
        q[4]=(unsigned char)len;memcpy(q+5,sold[k].id,(size_t)len);q[5+len]=(unsigned char)(c>>8);q[6+len]=(unsigned char)c;
        q+=7+len;
    }
    return need;
}
/* The block written above, replacing what is kept; the bytes read, -1 unreadable (then none kept). */
int AW_SoldImport(const unsigned char *p,int bytes){
    int rows,k,at=6;char id[40];
    AW_SoldReset();
    if(!p || bytes<6 || memcmp(p,"AWSL",4))return -1;
    rows=(p[4]<<8)|p[5];
    for(k=0;k<rows;k++){
        int len;uint32_t ref;int16_t count;
        if(at+5>bytes || (len=p[at+4])>=(int)sizeof(id) || at+7+len>bytes){AW_SoldReset();return -1;}
        ref=((uint32_t)p[at]<<24)|((uint32_t)p[at+1]<<16)|((uint32_t)p[at+2]<<8)|p[at+3];
        memcpy(id,p+at+5,(size_t)len);id[len]=0;count=(int16_t)((p[at+5+len]<<8)|p[at+6+len]);
        if(count>0 && !AW_SoldAdd(ref,id,count)){AW_SoldReset();return -1;}
        at+=7+len;
    }
    return at;
}
/* --- magic effects and spell effects (Spellmaking, Enchanting): read only while a window or a cast needs them --- */
int AW_ActorMagicEffect(int index,aw_mgef_t *out){
    unsigned char e[12];uint32_t flags,bits;
    if(!st || index<0 || (uint32_t)index>=st->amge.rows || !fetch(st->amge.offset+12u*(uint32_t)index,e,12) || !e[9])return 0;
    flags=u32(e);bits=u32(e+4);
    memcpy(&out->base_cost,&bits,4);out->flags=flags;out->school=e[8];out->name[0]=0;
    if(U16(e+10)!=0xFFFF)string_at((int)U16(e+10),out->name,sizeof(out->name),0);
    return 1;
}
int AW_ActorSpellEffects(int spell,aw_spell_effect_t *out,int max){
    unsigned char e[14],r[4];int i,n;uint32_t first;
    if(!st || spell<0 || (uint32_t)spell>=st->aspe.rows || !fetch(st->aspe.offset+4u*(uint32_t)spell,r,4))return 0;
    first=U16(r);n=r[2]<max?r[2]:max;
    for(i=0;i<n;i++){
        if(first+(uint32_t)i>=st->aeff.rows || !fetch(st->aeff.offset+14u*(first+(uint32_t)i),e,14))return i;
        out[i].effect=(int16_t)U16(e);out[i].skill=(signed char)e[2];out[i].attribute=(signed char)e[3];out[i].range=e[4];
        out[i].area=U16(e+6);out[i].duration=U16(e+8);out[i].magnitude_min=U16(e+10);out[i].magnitude_max=U16(e+12);
    }
    return n;
}
/* --- things the player made: spells (Spellmaking) and enchanted items (Enchanting) ---
 * Bounded lists carried in the saved game (AWMD, AWEN); nothing allocated until the first is made. Older saves:
 * none. A made spell is the player's own (not an ASPT row); the casting code reads its effects from here. */
#define AW_MADE_MAX 64
AW_RESIDENT_GROWS("made spells (Spellmaking)",AW_MADE_MAX,AW_MADE_SPELL_BYTES);
AW_RESIDENT_GROWS("enchanted items (Enchanting)",AW_MADE_MAX,AW_MADE_ITEM_BYTES);
typedef char aw_made_spell_fits[sizeof(aw_made_spell_t)<=AW_MADE_SPELL_BYTES?1:-1];
typedef char aw_made_item_fits[sizeof(aw_made_item_t)<=AW_MADE_ITEM_BYTES?1:-1];
static aw_made_spell_t *made_spells;static int made_spell_count;
static aw_made_item_t *made_items;static int made_item_count;
void AW_MadeReset(void){free(made_spells);made_spells=NULL;made_spell_count=0;free(made_items);made_items=NULL;made_item_count=0;}
int AW_MadeSpellCount(void){return made_spell_count;}
int AW_MadeItemCount(void){return made_item_count;}
const aw_made_spell_t *AW_MadeSpellAt(int i){return i>=0 && i<made_spell_count?&made_spells[i]:NULL;}
const aw_made_item_t *AW_MadeItemAt(int i){return i>=0 && i<made_item_count?&made_items[i]:NULL;}
int AW_MadeSpellAdd(const aw_made_spell_t *s){
    if(!s || s->effects<1 || s->effects>AW_MADE_EFFECTS || made_spell_count>=AW_MADE_MAX)return -1;
    if(!made_spells && !(made_spells=(aw_made_spell_t *)AW_TryMalloc(sizeof(aw_made_spell_t)*AW_MADE_MAX)))return -1;
    made_spells[made_spell_count]=*s;made_spells[made_spell_count].name[sizeof(s->name)-1]=0;
    return made_spell_count++;
}
int AW_MadeItemAdd(const aw_made_item_t *m){
    if(!m || m->effects<1 || m->effects>AW_MADE_EFFECTS || made_item_count>=AW_MADE_MAX)return -1;
    if(!made_items && !(made_items=(aw_made_item_t *)AW_TryMalloc(sizeof(aw_made_item_t)*AW_MADE_MAX)))return -1;
    made_items[made_item_count]=*m;made_items[made_item_count].name[sizeof(m->name)-1]=0;
    made_items[made_item_count].base[sizeof(m->base)-1]=0;
    return made_item_count++;
}
/* one effect as 14 bytes, the AEFF layout */
static void put_effect(unsigned char *q,const aw_spell_effect_t *e){
    q[0]=(unsigned char)((uint16_t)e->effect>>8);q[1]=(unsigned char)e->effect;q[2]=(unsigned char)e->skill;
    q[3]=(unsigned char)e->attribute;q[4]=e->range;q[5]=0;
    q[6]=(unsigned char)(e->area>>8);q[7]=(unsigned char)e->area;q[8]=(unsigned char)(e->duration>>8);q[9]=(unsigned char)e->duration;
    q[10]=(unsigned char)(e->magnitude_min>>8);q[11]=(unsigned char)e->magnitude_min;
    q[12]=(unsigned char)(e->magnitude_max>>8);q[13]=(unsigned char)e->magnitude_max;
}
static void get_effect(const unsigned char *p,aw_spell_effect_t *e){
    e->effect=(int16_t)U16(p);e->skill=(signed char)p[2];e->attribute=(signed char)p[3];e->range=p[4];
    e->area=(unsigned short)U16(p+6);e->duration=(unsigned short)U16(p+8);
    e->magnitude_min=(unsigned short)U16(p+10);e->magnitude_max=(unsigned short)U16(p+12);
}
/* "AWMD" u8 spells, each: name[32] u8 effects, 14 bytes an effect; then "AWEN" u8 items, each: base[40] name[32]
 * f32 charge (bits) f32 charge max u8 cast type u8 effects, 14 bytes an effect. The bytes written, -1 no room. */
int AW_MadeExport(unsigned char *out,int capacity){
    int i,j,at=0,need=10;
    for(i=0;i<made_spell_count;i++)need+=33+14*made_spells[i].effects;
    for(i=0;i<made_item_count;i++)need+=82+14*made_items[i].effects;
    if(need>capacity)return -1;
    memcpy(out,"AWMD",4);out[4]=(unsigned char)made_spell_count;at=5;
    for(i=0;i<made_spell_count;i++){
        memcpy(out+at,made_spells[i].name,32);out[at+32]=(unsigned char)made_spells[i].effects;at+=33;
        for(j=0;j<made_spells[i].effects;j++,at+=14)put_effect(out+at,&made_spells[i].effect[j]);
    }
    memcpy(out+at,"AWEN",4);out[at+4]=(unsigned char)made_item_count;at+=5;
    for(i=0;i<made_item_count;i++){
        uint32_t u;const aw_made_item_t *m=&made_items[i];
        memcpy(out+at,m->base,40);memcpy(out+at+40,m->name,32);
        memcpy(&u,&m->charge,4);out[at+72]=(unsigned char)(u>>24);out[at+73]=(unsigned char)(u>>16);out[at+74]=(unsigned char)(u>>8);out[at+75]=(unsigned char)u;
        memcpy(&u,&m->charge_max,4);out[at+76]=(unsigned char)(u>>24);out[at+77]=(unsigned char)(u>>16);out[at+78]=(unsigned char)(u>>8);out[at+79]=(unsigned char)u;
        out[at+80]=m->cast_type;out[at+81]=(unsigned char)m->effects;at+=82;
        for(j=0;j<m->effects;j++,at+=14)put_effect(out+at,&m->effect[j]);
    }
    return at;
}
int AW_MadeImport(const unsigned char *p,int bytes){
    int i,j,n,at=5;
    AW_MadeReset();
    if(!p || bytes<10 || memcmp(p,"AWMD",4))return -1;
    n=p[4];
    for(i=0;i<n;i++){
        aw_made_spell_t s;
        if(at+33>bytes)goto bad;
        memset(&s,0,sizeof(s));memcpy(s.name,p+at,32);s.name[31]=0;s.effects=p[at+32];at+=33;
        if(s.effects<1 || s.effects>AW_MADE_EFFECTS || at+14*s.effects>bytes)goto bad;
        for(j=0;j<s.effects;j++,at+=14)get_effect(p+at,&s.effect[j]);
        if(AW_MadeSpellAdd(&s)<0)goto bad;
    }
    if(at+5>bytes || memcmp(p+at,"AWEN",4))goto bad;
    n=p[at+4];at+=5;
    for(i=0;i<n;i++){
        aw_made_item_t m;uint32_t u;
        if(at+82>bytes)goto bad;
        memset(&m,0,sizeof(m));memcpy(m.base,p+at,40);m.base[39]=0;memcpy(m.name,p+at+40,32);m.name[31]=0;
        u=u32(p+at+72);memcpy(&m.charge,&u,4);u=u32(p+at+76);memcpy(&m.charge_max,&u,4);
        m.cast_type=p[at+80];m.effects=p[at+81];at+=82;
        if(m.effects<1 || m.effects>AW_MADE_EFFECTS || at+14*m.effects>bytes)goto bad;
        for(j=0;j<m.effects;j++,at+=14)get_effect(p+at,&m.effect[j]);
        if(AW_MadeItemAdd(&m)<0)goto bad;
    }
    return at;
bad:
    AW_MadeReset();return -1;
}
/* --- filled soul gems (Enchanting; Soultrap fills them): the gem's id and the soul's creature (its ACTB row, the
 * soul's value read from it); bounded, saved (AWSG), nothing until the first is filled --- */
#define AW_GEMS_MAX 64
#define AW_GEM_BYTES 44
AW_RESIDENT_GROWS("filled soul gems (Enchanting)",AW_GEMS_MAX,AW_GEM_BYTES);
typedef struct {char gem[40];uint16_t creature;uint16_t pad;} gem_t;
typedef char aw_gem_fits[sizeof(gem_t)<=AW_GEM_BYTES?1:-1];
static gem_t *gems;static int gem_count;
void AW_GemsReset(void){free(gems);gems=NULL;gem_count=0;}
int AW_GemCount(void){return gem_count;}
int AW_GemAdd(const char *gem,int creature){
    if(!gem || !*gem || strlen(gem)>=sizeof(gems[0].gem) || creature<0 || creature>0xFFFE || gem_count>=AW_GEMS_MAX)return -1;
    if(!gems && !(gems=(gem_t *)AW_TryMalloc(sizeof(gem_t)*AW_GEMS_MAX)))return -1;
    strcpy(gems[gem_count].gem,gem);gems[gem_count].creature=(uint16_t)creature;gems[gem_count].pad=0;
    return gem_count++;
}
int AW_GemAt(int i,char *gem,int capacity,int *creature){
    if(i<0 || i>=gem_count || capacity<1)return 0;
    strncpy(gem,gems[i].gem,(size_t)capacity-1);gem[capacity-1]=0;*creature=gems[i].creature;
    return 1;
}
int AW_GemRemove(int i){
    if(i<0 || i>=gem_count)return 0;
    memmove(gems+i,gems+i+1,sizeof(gem_t)*(size_t)(gem_count-i-1));gem_count--;
    return 1;
}
/* the soul's value (the creature record's soul, ACTB): the charge an enchantment can hold */
int AW_GemSoul(int i){
    aw_actor_base_t b;
    if(i<0 || i>=gem_count || !AW_ActorBase(gems[i].creature,&b))return 0;
    return (int)b.soul;
}
/* "AWSG" u8 gems, each: u8 id length, the id, u16 creature row. The bytes written, -1 no room. */
int AW_GemsExport(unsigned char *out,int capacity){
    int i,at=5,need=5;
    for(i=0;i<gem_count;i++)need+=3+(int)strlen(gems[i].gem);
    if(need>capacity)return -1;
    memcpy(out,"AWSG",4);out[4]=(unsigned char)gem_count;
    for(i=0;i<gem_count;i++){
        int len=(int)strlen(gems[i].gem);
        out[at]=(unsigned char)len;memcpy(out+at+1,gems[i].gem,(size_t)len);
        out[at+1+len]=(unsigned char)(gems[i].creature>>8);out[at+2+len]=(unsigned char)gems[i].creature;at+=3+len;
    }
    return at;
}
int AW_GemsImport(const unsigned char *p,int bytes){
    int i,n,at=5;char gem[40];
    AW_GemsReset();
    if(!p || bytes<5 || memcmp(p,"AWSG",4))return -1;
    n=p[4];
    for(i=0;i<n;i++){
        int len;
        if(at+1>bytes || (len=p[at])>=(int)sizeof(gem) || at+3+len>bytes){AW_GemsReset();return -1;}
        memcpy(gem,p+at+1,(size_t)len);gem[len]=0;
        if(AW_GemAdd(gem,(int)U16(p+at+1+len))<0){AW_GemsReset();return -1;}
        at+=3+len;
    }
    return at;
}
/* --- places a script revealed on the map (ShowMap; OpenMW guiextensions.cpp OpShowMap: every exterior cell whose
 * name holds the text becomes known) --- the texts, kept for the map's place markers (INGAME-MAP-ORIGINAL-57) and
 * saved (AWMP); nothing until the first ShowMap, a bounded list */
#define AW_REVEALED_MAX 128
#define AW_REVEALED_BYTES 32
AW_RESIDENT_GROWS("places revealed by ShowMap",AW_REVEALED_MAX,AW_REVEALED_BYTES);
static char (*revealed)[AW_REVEALED_BYTES];static int revealed_count;
void AW_RevealedReset(void){free(revealed);revealed=NULL;revealed_count=0;}
int AW_RevealedCount(void){return revealed_count;}
const char *AW_RevealedAt(int i){return i>=0 && i<revealed_count?revealed[i]:NULL;}
int AW_RevealedAdd(const char *text){
    int i;
    if(!text || !*text || strlen(text)>=AW_REVEALED_BYTES)return 0;
    for(i=0;i<revealed_count;i++)if(ci_equal(revealed[i],text))return 1;   /* known already */
    if(revealed_count>=AW_REVEALED_MAX)return 0;
    if(!revealed && !(revealed=(char (*)[AW_REVEALED_BYTES])AW_TryMalloc((unsigned long)AW_REVEALED_BYTES*AW_REVEALED_MAX)))return 0;
    strcpy(revealed[revealed_count++],text);
    return 1;
}
/* "AWMP" u8 count, each u8 length and the text. Bytes written, -1 no room. */
int AW_RevealedExport(unsigned char *out,int capacity){
    int i,at=5,need=5;
    for(i=0;i<revealed_count;i++)need+=1+(int)strlen(revealed[i]);
    if(need>capacity)return -1;
    memcpy(out,"AWMP",4);out[4]=(unsigned char)revealed_count;
    for(i=0;i<revealed_count;i++){int n=(int)strlen(revealed[i]);out[at]=(unsigned char)n;memcpy(out+at+1,revealed[i],(size_t)n);at+=1+n;}
    return at;
}
int AW_RevealedImport(const unsigned char *p,int bytes){
    int i,n,at=5;char text[AW_REVEALED_BYTES];
    AW_RevealedReset();
    if(!p || bytes<5 || memcmp(p,"AWMP",4))return -1;
    n=p[4];
    for(i=0;i<n;i++){
        int len;
        if(at+1>bytes || (len=p[at])>=AW_REVEALED_BYTES || at+1+len>bytes){AW_RevealedReset();return -1;}
        memcpy(text,p+at+1,(size_t)len);text[len]=0;at+=1+len;
        if(!AW_RevealedAdd(text)){AW_RevealedReset();return -1;}
    }
    return at;
}
