/* SPDX-License-Identifier: GPL-2.0-or-later
 * dbg spawn (DBG-SPAWN-MENU-67, aw_dbgspawn.h): a list box of the people and creatures the build has a model for, as
 * the dbg tp box shows the places (aw_listbox.c: type to find, Up/Down, Enter or a click), with the buttons All / NPCs /
 * Creatures, the selected one's level, health, magicka and Fight with its race and class (a creature: its type), and
 * the switch "spawn in with base attributes" (Space or a click; on by default). The rows come from the actor table's
 * bases (aw_actors.c AW_ActorsBaseEach: the record id and the name of every base that spawns a living actor), held only
 * while the box is open and freed when it closes; a row's properties are read from the actor record (ACTB) when it is
 * selected. Enter spawns the selected one in front of the player (aw_mwhost.c AW_MwscriptSpawn): with the switch on as
 * the game makes it (stats, behaviour, items, its script), off its model only. dbg spawn ID [model] does the same
 * without the box; dbg despawn (aw_companion.c) and dbg despawn all (aw_mwhost.c) take them away again.
 */
#ifndef AW_DBGSPAWN_RULES_ONLY
#include "quakedef.h"
#include "aw_listbox.h"
#include "aw_actors.h"
#include "aw_actorstate.h"
#include "aw_tryalloc.h"
#else
#include <stdio.h>
#include <string.h>
#endif
#include "aw_dbgspawn.h"

/* ---- the rules (no engine dependency) ---- */
static int fold(int c){return c>='A' && c<='Z'?c+32:c;}
int AW_SpawnLabel(const char *name,const char *id,char *out,int size){
    int ni=id?(int)strlen(id):0,nn=name?(int)strlen(name):0,i,k=0;
    if(!ni || size<2 || ni+1>size)return -1;
    if(nn && nn+ni+2>size)nn=size-ni-2;          /* the name gives way: the id must stay whole to be spawned */
    if(nn<0)nn=0;
    for(i=0;i<nn;i++)out[k++]=(char)((unsigned char)name[i]<32?' ':name[i]);   /* a tab or a control: a space */
    if(k)out[k++]='\t';
    memcpy(out+k,id,(size_t)ni);k+=ni;out[k]=0;
    return k;
}
int AW_SpawnLabelId(const char *label,char *out,int size){
    const char *s=label?strchr(label,'\t'):NULL;int n;
    s=s?s+1:label;
    if(size>0)out[0]=0;
    if(!s || !*s || (n=(int)strlen(s))+1>size)return 0;
    memcpy(out,s,(size_t)n+1);
    return 1;
}
/* by name (up to the tab, which sorts before every character: "Rat" before "Rat Queen"), case ignored, then by id */
int AW_SpawnCompare(const char *a,const char *b){
    int x,y;
    for(;;a++,b++){
        x=fold((unsigned char)*a);y=fold((unsigned char)*b);
        if(x!=y || !x)return x-y;
    }
}
int AW_SpawnDetail(const aw_spawn_facts_t *f,char *out,int size){
    static const char *const types[4]={"creature","daedra","undead","humanoid"};
    char line[192];int n;
    if(size<1)return 0;
    if(!f){out[0]=0;return 0;}
    if(f->kind)sprintf(line,"Level %d, health %d, magicka %d, Fight %d\t%s",f->level,f->health,f->magicka,f->fight,
                       f->type>=0 && f->type<4?types[f->type]:"creature");
    else sprintf(line,"Level %d, health %d, magicka %d, Fight %d\t%.31s%s%.31s",f->level,f->health,f->magicka,f->fight,
                 f->race,f->race[0] && f->cls[0]?" ":"",f->cls);
    n=(int)strlen(line);if(n>size-1)n=size-1;
    memcpy(out,line,(size_t)n);out[n]=0;
    return n;
}
int AW_SpawnHow(const char *word){
    if(!word || !*word)return 1;
    if(!strcmp(word,"full") || !strcmp(word,"attributes"))return 1;
    if(!strcmp(word,"model") || !strcmp(word,"placeholder"))return 0;
    return -1;
}

#ifndef AW_DBGSPAWN_RULES_ONLY
/* ---- the box ---- */
extern int AW_MwscriptActors(void);
static struct {
    char *labels;unsigned long used,cap;     /* the labels one after another, each ending in a NUL */
    unsigned long *at;unsigned char *kind;   /* per row: where its label starts, 0 NPC 1 creature */
    int count,max,shown,failed;
    int *order;                              /* the rows the box shows, sorted, each label once */
} rows;
static int spawn_full=1;                     /* "spawn in with base attributes": on by default */
static char detail_line[AW_SPAWN_DETAIL];
static int detail_row=-1;

static void rows_free(void){
    free(rows.labels);free(rows.at);free(rows.kind);free(rows.order);
    memset(&rows,0,sizeof(rows));detail_row=-1;detail_line[0]=0;
}
/* a block of WANT bytes holding the HAVE bytes of P (P freed); NULL no memory (P kept) */
static void *grown(void *p,unsigned long have,unsigned long want){
    void *q=AW_TryMalloc(want);
    if(!q)return NULL;
    if(p){memcpy(q,p,have);free(p);}
    return q;
}
static void take(void *ctx,const char *id,const char *name,int kind){
    char text[AW_SPAWN_LABEL];int n;void *q;
    (void)ctx;
    if(rows.failed || (n=AW_SpawnLabel(name,id,text,sizeof(text)))<0)return;
    if(rows.count>=rows.max){
        int wanted=rows.max?rows.max*2:512;
        if(!(q=grown(rows.at,sizeof(unsigned long)*(unsigned long)rows.count,sizeof(unsigned long)*(unsigned long)wanted))){rows.failed=1;return;}
        rows.at=(unsigned long *)q;
        if(!(q=grown(rows.kind,(unsigned long)rows.count,(unsigned long)wanted))){rows.failed=1;return;}
        rows.kind=(unsigned char *)q;rows.max=wanted;
    }
    if(rows.used+(unsigned long)n+1>rows.cap){
        unsigned long cap=rows.cap?rows.cap*2:16384;
        while(cap<rows.used+(unsigned long)n+1)cap*=2;
        if(!(q=grown(rows.labels,rows.used,cap))){rows.failed=1;return;}
        rows.labels=(char *)q;rows.cap=cap;
    }
    rows.at[rows.count]=rows.used;rows.kind[rows.count]=(unsigned char)(kind?1:0);rows.count++;
    memcpy(rows.labels+rows.used,text,(size_t)n+1);rows.used+=(unsigned long)n+1;
}
static const char *label_of(int i){return rows.labels+rows.at[i];}
static int by_label(const void *a,const void *b){
    int x=AW_SpawnCompare(label_of(*(const int *)a),label_of(*(const int *)b));
    return x?x:strcmp(label_of(*(const int *)a),label_of(*(const int *)b));
}
static const char *label(void *ctx,int row){(void)ctx;return row>=0 && row<rows.shown?label_of(rows.order[row]):"";}
static int category(void *ctx,int row){
    (void)ctx;
    return row>=0 && row<rows.shown?(rows.kind[rows.order[row]]?AW_SPAWN_CAT_CREATURE:AW_SPAWN_CAT_NPC):AW_SPAWN_CAT_ALL;
}
/* the selected row's properties from its actor record: read when the selection changes, kept while it stays */
static const char *detail(void *ctx,int row){
    aw_spawn_facts_t f;aw_actor_base_t b;char id[64];int r;
    (void)ctx;
    if(row==detail_row)return detail_line;
    detail_row=row;detail_line[0]=0;
    if(row<0 || row>=rows.shown || !AW_SpawnLabelId(label(NULL,row),id,sizeof(id)) || !AW_MwscriptActors() ||
       (r=AW_ActorFind(id))==AW_ACTOR_NONE || !AW_ActorBase(r,&b))return detail_line;
    memset(&f,0,sizeof(f));
    f.kind=b.kind;f.level=b.level;f.health=b.health;f.magicka=b.magicka;f.fight=b.fight;f.flee=b.flee;f.type=b.type;
    if(!b.kind){(void)AW_ActorString((int)b.race,f.race,sizeof(f.race));(void)AW_ActorString((int)b.clas,f.cls,sizeof(f.cls));}
    (void)AW_SpawnDetail(&f,detail_line,sizeof(detail_line));
    return detail_line;
}
static void chosen(void *ctx,int row){
    char id[64];
    (void)ctx;
    if(row>=0 && row<rows.shown && AW_SpawnLabelId(label(NULL,row),id,sizeof(id)))(void)AW_MwscriptSpawn(id,spawn_full);
}
static void closed(void *ctx){(void)ctx;rows_free();}
static void open_box(void){
    static const char *const names[AW_SPAWN_CATS]={"All","NPCs","Creatures"};
    aw_listbox_spec_t s;int i,k,n;
    if(AW_ListBoxActive()){Con_Printf("dbg spawn: another list is open.\n");return;}
    rows_free();
    n=AW_ActorsBaseEach(take,NULL);
    if(n<0 || rows.failed || !rows.count ||
       !(rows.order=(int *)AW_TryMalloc(sizeof(int)*(unsigned long)rows.count))){
        Con_Printf(n<0?"dbg spawn: this build has no actor table (maps/chim-actors.cca).\n":
                   rows.failed || rows.count?"dbg spawn: not enough memory for the list (dbg spawn ID).\n":
                   "dbg spawn: no person or creature of this build has a model.\n");
        rows_free();return;
    }
    for(i=0;i<rows.count;i++)rows.order[i]=i;
    qsort(rows.order,(size_t)rows.count,sizeof(int),by_label);
    for(i=k=0;i<rows.count;i++)   /* a record with two bases (a scaled copy) is listed once */
        if(!k || strcmp(label_of(rows.order[i]),label_of(rows.order[k-1])))rows.order[k++]=rows.order[i];
    rows.shown=k;
    memset(&s,0,sizeof(s));
    s.title="Spawn: people and creatures";s.count=rows.shown;s.label=label;s.chosen=chosen;s.closed=closed;
    s.category_names=names;s.categories=AW_SPAWN_CATS;s.category=category;
    s.detail=detail;s.check="spawn in with base attributes";s.checked=&spawn_full;
    if(!AW_ListBoxOpen(&s)){Con_Printf("dbg spawn: the list cannot open now (dbg spawn ID).\n");rows_free();return;}
    Con_Printf("dbg spawn: %d people and creatures, %lu bytes held while the list is open.\n",rows.shown,
               rows.cap+(sizeof(unsigned long)+1+sizeof(int))*(unsigned long)rows.max);
}
void AW_SpawnCommand(const char *id,const char *how){
    int full;
    if(!sv.active){Con_Printf("dbg spawn: start the game first.\n");return;}
    if(!id || !*id){open_box();return;}
    if((full=AW_SpawnHow(how))<0){
        Con_Printf("Usage: dbg spawn [ID [model]] (no ID: the list; model: only its model, a placeholder)\n");return;}
    (void)AW_MwscriptSpawn(id,full);
}
#endif
