/* SPDX-License-Identifier: GPL-2.0-or-later
 * The light test and the item tester (aw_cycleitems.h; LIGHTTEST-MAP-67, DBG-CYCLEITEMS-67, docs/ITEM_CYCLING.md). A
 * debug tool: nothing of it is kept while it does not run (the index is read when the tester starts and freed when it
 * ends), and it changes nothing in play. */
#include <stdio.h>
#include <string.h>
#include "aw_cycleitems.h"

static int field(char *out,int size,const char *p,int n)
{
    if(n<0 || n>=size)return 0;
    memcpy(out,p,(size_t)n);out[n]=0;return 1;
}
int AW_HoldableParse(const char *line,int n,aw_holdable_t *out)
{
    const char *f[6];int len[6],k=0,i,start=0;aw_holdable_t t;
    if(!line || !out || n<=0)return 0;
    for(i=0;i<=n;i++){
        if(i<n && (line[i]=='\n' || line[i]=='\r' || !line[i]))return 0;
        if(i==n || line[i]=='\t'){
            if(k==6)return 0;
            f[k]=line+start;len[k]=i-start;k++;start=i+1;
        }
    }
    if(k!=6 || len[0]<1 || len[1]<1 || len[2]<1 || len[4]<1 || len[5]!=1 || (f[5][0]!='0' && f[5][0]!='1'))return 0;
    memset(&t,0,sizeof(t));
    if(!field(t.name,sizeof(t.name),f[0],len[0]) || !field(t.id,sizeof(t.id),f[1],len[1]) ||
       !field(t.kind,sizeof(t.kind),f[2],len[2]) || !field(t.hands,sizeof(t.hands),f[3],len[3]) ||
       !field(t.action,sizeof(t.action),f[4],len[4]))return 0;
    if(strcmp(t.hands,"right") && strcmp(t.hands,"left") && strcmp(t.hands,"both"))return 0;
    t.equips=f[5][0]=='1';*out=t;return 1;
}
int AW_CycleHasAction(const aw_holdable_t *h)
{
    /* the weapons' attack groups (tools/holdable_items.py WEAPONS); block, none and pickprobe have no attack */
    return h && h->action[0] && strcmp(h->action,"none") && strcmp(h->action,"block") && strcmp(h->action,"pickprobe");
}
int AW_CycleHudLine(char *out,int size,const aw_holdable_t *h,int index,int total,int step)
{
    static const char *const steps[AW_CYCLE_STEPS]={"empty hands","hold","walk","action"};
    int n;
    if(!out || size<1)return 0;
    if(!h || step<0 || step>=AW_CYCLE_STEPS){out[0]=0;return 0;}
    n=snprintf(out,(size_t)size,"%s (%s)  %d/%d  %s",h->name,h->id,index,total,steps[step]);
    return n<0?0:(n<size?n:size-1);
}
int AW_LightHeldLine(char *out,int size,const char *left_name,const char *left_id,const char *right_name,
                     const char *right_id)
{
    int n,left,right;
    if(!out || size<1)return 0;
    left=left_id && left_id[0];right=right_id && right_id[0];
    if(!left && !right)n=snprintf(out,(size_t)size,"empty hands");
    else n=snprintf(out,(size_t)size,"%s%s%s%s%s%s%s%s%s",
                    left?(left_name && left_name[0]?left_name:left_id):"",left?" (":"",left?left_id:"",left?")":"",
                    left && right?"  +  ":"",
                    right?(right_name && right_name[0]?right_name:right_id):"",right?" (":"",right?right_id:"",
                    right?")":"");
    return n<0?0:(n<size?n:size-1);
}
static float ease(float a,float b,float u){u=u<0?0:u>1?1:u;u=u*u*(3-2*u);return a+(b-a)*u;}
float AW_LightWalkPitch(float t)
{
    /* the maintainer's walk: 10 s straight on, the head down to the hands to 15 s, back up to the end */
    if(t<10)return 0;
    if(t<15)return ease(0,AW_LIGHTWALK_DOWN,t-10);
    return ease(AW_LIGHTWALK_DOWN,0,t-15);
}

#ifndef AW_CYCLE_HOST_TEST
#include "quakedef.h"
#include "aw_inventory.h"
#include "aw_hand_models.h"
#include "aw_combat.h"
#include "aw_tryalloc.h"
float (*aw_view_held_gap)(int hand);
extern int (*aw_mwscript_paused)(void);   /* aw_mwhost.c: the game's scripts wait while it says so */
/* aw_lighttest_scripts 1: the game's scripts run in the corridor too (default 0: paused there) */
static cvar_t lighttest_scripts={"aw_lighttest_scripts","0"};
static int scripts_paused(void){return AW_LightTestActive() && !lighttest_scripts.value;}
/* the seconds of each step (game time on the host clock: at the emulator's warp it runs that much faster) */
#define EMPTY_S 0.6
#define HOLD_S 1.5
#define ACTION_S 1.6
#define PRESS_S 0.5
#define SETTLE_S 1.0     /* dbg lighttest 1: after the arrival, before the walk */
static char *index_text;            /* the index while the tester runs (about 40 KB), freed when it ends */
static long index_size,next_line;
static int running,total,current,step,pressed,failures,measured,granted;
static double step_t;
static aw_holdable_t item;
static float worst[AW_CYCLE_STEPS],worst_all;
static char worst_id[64],only_kind[32];   /* dbg cycleitems kind K: only the items of that kind */
static edict_t *player(void)
{
    if(!sv.active || svs.maxclients!=1 || !svs.clients || !svs.clients[0].edict)return NULL;
    return svs.clients[0].edict;
}
/* ---- the held items' line (the corridor's only overlay; the console gets it when it changes) ---- */
static char held_ids[2][64],held_names[2][96],held_text[200];
static void held_refresh(void)
{
    static const int slots[2]={AW_SLOT_LEFT,AW_SLOT_RIGHT};
    aw_inventory_item_t it;int s,changed=0;char line[200];
    for(s=0;s<2;s++){
        const char *id=aw_state.inventory.equipped[slots[s]];
        if(!strcmp(id,held_ids[s]))continue;
        changed=1;Q_strncpy(held_ids[s],(char *)id,63);held_ids[s][63]=0;held_names[s][0]=0;
        if(id[0] && AW_InventoryRead(id,&it)){Q_strncpy(held_names[s],it.name,95);held_names[s][95]=0;}
    }
    AW_LightHeldLine(line,sizeof(line),held_names[0],held_ids[0],held_names[1],held_ids[1]);
    if(changed || strcmp(line,held_text)){strcpy(held_text,line);Con_Printf("LIGHTTEST held: %s\n",held_text);}
}
/* ---- the walk (dbg lighttest 1, and every item of the tester) ---- */
static int walking,walk_pending,walk_corridor;
static double walk_t,walk_start_at;
static vec3_t walk_from;
static void walk_end(const char *why)
{
    edict_t *p=player();vec3_t d;
    if(!walking)return;
    Cbuf_AddText("-forward\n");walking=0;cl.viewangles[PITCH]=0;
    if(p){VectorSubtract(p->v.origin,walk_from,d);}else{VectorCopy(vec3_origin,d);}
    Con_Printf("LIGHTTEST walk %s: %.0f units in %.1f s\n",why?why:"done",sqrt(d[0]*d[0]+d[1]*d[1]),realtime-walk_t);
}
static void walk_begin(void)
{
    edict_t *p=player();
    if(!p)return;
    if(walking)walk_end("again");
    VectorCopy(p->v.origin,walk_from);walk_corridor=AW_LightTestActive();
    cl.viewangles[PITCH]=0;Cbuf_AddText("+forward\n");walking=1;walk_t=realtime;
    Con_Printf("LIGHTTEST walk: %.0f s forward, the head down to the hands from 10 to 15 s; held: %s\n",
               (double)AW_LIGHTWALK_S,held_text[0]?held_text:"-");
}
static void walk_frame(void)
{
    double t;
    if(walk_start_at>0 && realtime>=walk_start_at){walk_start_at=0;walk_begin();}
    if(!walking)return;
    if(!player()){walk_end("ended: the game ended");return;}
    if(walk_corridor && !AW_LightTestActive()){walk_end("ended: left the corridor");return;}
    t=realtime-walk_t;
    if(t>=AW_LIGHTWALK_S){walk_end(NULL);return;}
    cl.viewangles[PITCH]=AW_LightWalkPitch((float)t);
}
/* ---- the item tester ---- */
static void release_keys(void)
{
    walk_end("stopped");Cbuf_AddText("-attack\n");pressed=0;
}
static int pending_first,in_field;  /* waiting for the corridor to load (its first item); running in it */
static int here;                    /* dbg cycleitems here: where the player stands, not in the corridor */
static void stop(const char *why)
{
    if(!running)return;
    release_keys();running=0;
    if(index_text){free(index_text);index_text=NULL;}
    Con_Printf("CYCLEITEMS RESULT %s %d of %d items checked, %d with the grip off the hand; worst grip %.2f units (%s)%s%s\n",
               failures?"FAIL":"PASS",current,total,failures,worst_all,worst_id[0]?worst_id:"none",why?": ":"",
               why?why:"");
    /* back to the captured game from the corridor (aw_gallery.c) */
    if(in_field){in_field=0;AW_GalleryLightTestLeave();}
}
static int kind_wanted(const aw_holdable_t *h){return !only_kind[0] || !Q_strcasecmp((char *)h->kind,only_kind);}
/* the next whole row of the index of the kind asked for (one that does not parse is named and skipped): 1 with ITEM */
static int next_item(void)
{
    while(next_line<index_size){
        long end=next_line;
        while(end<index_size && index_text[end]!='\n')end++;
        if(AW_HoldableParse(index_text+next_line,(int)(end-next_line),&item)){
            next_line=end+1;
            if(!kind_wanted(&item))continue;
            current++;return 1;
        }
        if(end>next_line)Con_Printf("CYCLEITEMS: an index row that does not read, left out (byte %ld).\n",next_line);
        next_line=end+1;
    }
    return 0;
}
static void hands_up(void)
{
    edict_t *p=player();eval_t *goal=p?GetEdictFieldValue(p,"aw_hand_goal"):NULL;
    if(goal && goal->_float!=1)Cbuf_AddText("impulse 202\n");
}
static void empty_hands(void)
{
    int s,slots[2]={AW_SLOT_LEFT,AW_SLOT_RIGHT};char id[64];
    AW_CombatEquipmentStore();
    for(s=0;s<2;s++){
        Q_strncpy(id,aw_state.inventory.equipped[slots[s]],63);id[63]=0;
        if(id[0])AW_InventoryUnequip(&aw_state,id);
    }
    AW_CombatEquipmentChanged();
}
static int hold(void)
{
    aw_inventory_item_t it;
    if(!AW_InventoryRead(item.id,&it)){Con_Printf("CYCLEITEMS %d/%d %s: not in this image's catalogue.\n",current,total,item.id);return 0;}
    granted=0;
    if(AW_StateGet(&aw_state,AW_ITEM,it.id)<1){
        if(!AW_ItemAdd(&aw_state,it.id,1)){Con_Printf("CYCLEITEMS %d/%d %s: no room for it.\n",current,total,item.id);return 0;}
        granted=1;
    }
    if(!item.equips || !AW_InventoryCanEquip(&it)){
        Con_Printf("CYCLEITEMS %d/%d %s (%s): not held yet (%s).\n",current,total,item.id,item.kind,
                   item.equips?"refused by the inventory":"the inventory does not equip it");
        return 0;
    }
    AW_CombatEquipmentStore();
    if(!AW_InventoryEquipped(&aw_state,it.id) && !AW_InventoryEquip(&aw_state,&it)){
        Con_Printf("CYCLEITEMS %d/%d %s: equip refused.\n",current,total,item.id);return 0;
    }
    AW_CombatEquipmentChanged();hands_up();return 1;
}
static void let_go(void)
{
    int32_t n=AW_StateGet(&aw_state,AW_ITEM,item.id);
    empty_hands();
    /* the test grant taken back (only one the tester gave): the player's own items stay, the inventory stays small */
    if(granted && n>0)AW_StateSet(&aw_state,AW_ITEM,item.id,n-1);
    granted=0;
}
static int hand_of(void){return !strcmp(item.hands,"left")?AW_HAND_LEFT:AW_HAND_RIGHT;}
static void measure(void)
{
    float g;
    if(step<AW_CYCLE_HOLD || !aw_view_held_gap || (g=aw_view_held_gap(hand_of()))<0)return;
    measured++;
    if(g>worst[step])worst[step]=g;
}
static void report_item(void)
{
    float m=worst[AW_CYCLE_HOLD];int s,off;
    for(s=AW_CYCLE_HOLD;s<AW_CYCLE_STEPS;s++)if(worst[s]>m)m=worst[s];
    off=measured && m>2.0f;
    if(off)failures++;
    if(measured && m>worst_all){worst_all=m;Q_strncpy(worst_id,item.id,63);worst_id[63]=0;}
    if(measured)Con_Printf("CYCLEITEMS %d/%d %s (%s, %s, %s): grip %s, worst %.2f units (hold %.2f, walk %.2f, action %.2f) "
        "over %d frames\n",current,total,item.id,item.kind,item.hands,item.action,off?"OFF THE HAND":"in the hand",m,
        worst[AW_CYCLE_HOLD],worst[AW_CYCLE_WALK],worst[AW_CYCLE_ACTION],measured);
    else Con_Printf("CYCLEITEMS %d/%d %s (%s, %s, %s): held, walked and used; grip not measured in this view\n",current,
        total,item.id,item.kind,item.hands,item.action);
}
static void begin_item(void)
{
    memset(worst,0,sizeof(worst));measured=0;
    /* every item from the corridor's west end, the head straight (nothing happens outside the corridor) */
    AW_GalleryLightTestCenter();cl.viewangles[PITCH]=0;
    step=AW_CYCLE_EMPTY;step_t=realtime;empty_hands();hands_up();
}
static void start(int first);
static int field_ready;
void AW_CycleItemsFrame(void)
{
    double t;
    if(field_ready){
        int first=pending_first;
        field_ready=0;pending_first=0;
        if(first>0 && AW_LightTestActive())start(first);
    }
    if(AW_LightTestActive())held_refresh();
    walk_frame();
    if(!running)return;
    if(!player()){stop("the game ended");return;}
    if(in_field && !AW_LightTestActive()){in_field=0;stop("left the light test corridor");return;}
    t=realtime-step_t;
    measure();
    switch(step){
    case AW_CYCLE_EMPTY:
        if(t<EMPTY_S)return;
        if(!hold()){let_go();if(next_item())begin_item();else stop(NULL);return;}
        step=AW_CYCLE_HOLD;step_t=realtime;return;
    case AW_CYCLE_HOLD:
        if(t<HOLD_S)return;
        step=AW_CYCLE_WALK;step_t=realtime;walk_begin();return;
    case AW_CYCLE_WALK:
        if(walking)return;          /* walk_frame ends it after its AW_LIGHTWALK_S seconds */
        step=AW_CYCLE_ACTION;step_t=realtime;
        if(AW_CycleHasAction(&item)){hands_up();Cbuf_AddText("+attack\n");pressed=1;}
        return;
    case AW_CYCLE_ACTION:
        if(pressed && t>=PRESS_S){Cbuf_AddText("-attack\n");pressed=0;}
        if(t<ACTION_S)return;
        report_item();let_go();
        if(next_item())begin_item();else stop(NULL);
        return;
    }
}
static void start(int first)
{
    FILE *f=NULL;long size,at;int i;aw_holdable_t row;
    if(running){Con_Printf("The item tester is already running (dbg cycleitems stop).\n");return;}
    if(!player()){Con_Printf("Start or load a game first.\n");return;}
    /* the light test corridor first (in every image, like the torch test room): the tester starts when the player is
     * there */
    if(!here && !AW_LightTestActive() && pending_first<=0 && AW_GalleryLightTestEnter()){
        pending_first=first>0?first:1;Con_Printf("CYCLEITEMS: to the light test corridor.\n");return;
    }
    in_field=AW_LightTestActive();
    size=COM_FOpenFile(AW_HOLDABLE_PATH,&f);
    if(!f || size<6){if(f)fclose(f);Con_Printf("No holdable item index (%s) in this image.\n",AW_HOLDABLE_PATH);return;}
    if(!(index_text=(char *)AW_TryMalloc((unsigned long)size+1))){
        fclose(f);Con_Printf("No memory for the item index (%ld bytes).\n",size);return;
    }
    if(fread(index_text,1,(size_t)size,f)!=(size_t)size || memcmp(index_text,"AWHI1\n",6)){
        fclose(f);free(index_text);index_text=NULL;Con_Printf("The holdable item index does not read.\n");return;
    }
    fclose(f);index_text[size]=0;index_size=size;
    /* the items of the kind asked for (all without one) */
    for(total=0,at=6,i=6;i<=size;i++)if(i==size || index_text[i]=='\n'){
        if(i>at && AW_HoldableParse(index_text+at,(int)(i-at),&row) && kind_wanted(&row))total++;
        at=i+1;
    }
    next_line=6;current=0;failures=0;worst_all=0;worst_id[0]=0;running=1;
    while(current<first-1 && next_item());
    if(!next_item()){stop("no item from there");return;}
    Con_Printf("CYCLEITEMS: %d items%s%s (%ld bytes of index); each: empty hands, held, walked, used.\n",total,
               only_kind[0]?" of the kind ":"",only_kind,size);
    begin_item();
}
static void command(void)
{
    const char *a=Cmd_Argc()>1?Cmd_Argv(1):"";
    if(!*a || !Q_strcasecmp((char *)a,"start")){only_kind[0]=0;start(Cmd_Argc()>2?Q_atoi(Cmd_Argv(2)):1);return;}
    if(!Q_strcasecmp((char *)a,"from") && Cmd_Argc()>2){only_kind[0]=0;start(Q_atoi(Cmd_Argv(2)));return;}
    if(!Q_strcasecmp((char *)a,"kind") && Cmd_Argc()>2){
        int i,n=0;
        if(running){Con_Printf("The item tester is already running (dbg cycleitems stop).\n");return;}
        for(i=2;i<Cmd_Argc();i++){
            if(n+(int)strlen(Cmd_Argv(i))+2>(int)sizeof(only_kind)){only_kind[0]=0;Con_Printf("No such kind.\n");return;}
            if(n)only_kind[n++]=' ';
            strcpy(only_kind+n,Cmd_Argv(i));n+=(int)strlen(Cmd_Argv(i));
        }
        start(1);return;
    }
    if(!Q_strcasecmp((char *)a,"here")){only_kind[0]=0;here=1;start(Cmd_Argc()>2?Q_atoi(Cmd_Argv(2)):1);here=0;return;}
    if(!Q_strcasecmp((char *)a,"stop")){if(running)stop("stopped");else Con_Printf("The item tester is not running.\n");return;}
    if(!Q_strcasecmp((char *)a,"status")){
        if(running)Con_Printf("CYCLEITEMS: item %d of %d (%s), %d with the grip off the hand so far.\n",current,total,
                              item.id,failures);
        else Con_Printf("The item tester is not running.\n");
        return;
    }
    Con_Printf("Usage: dbg cycleitems [start [N] | from N | kind KIND | here [N] | status | stop]\n");
}
/* dbg lighttest: into the corridor; dbg lighttest 1: and the walk; center, stop, exit */
static void lighttest_command(void)
{
    const char *a=Cmd_Argc()>1?Cmd_Argv(1):"";
    if(Cmd_Argc()>2 || (*a && strcmp(a,"1") && Q_strcasecmp((char *)a,"center") && Q_strcasecmp((char *)a,"stop") &&
       Q_strcasecmp((char *)a,"exit"))){
        Con_Printf("Usage: dbg lighttest [1 | center | stop | exit]\n");return;
    }
    if(!Q_strcasecmp((char *)a,"exit")){
        walk_start_at=0;walk_pending=0;walk_end("stopped");
        if(running)stop("left the light test corridor");else AW_GalleryLightTestLeave();
        return;
    }
    if(!Q_strcasecmp((char *)a,"stop")){walk_start_at=0;walk_end("stopped");return;}
    if(running){Con_Printf("The item tester walks by itself (dbg cycleitems stop first).\n");return;}
    if(!Q_strcasecmp((char *)a,"center")){AW_GalleryLightTestCenter();cl.viewangles[PITCH]=0;return;}
    if(AW_LightTestActive()){
        if(!*a){Con_Printf("LIGHTTEST: in the light test corridor, the game's scripts %s; held: %s.\n",
                           scripts_paused()?"paused":"running",held_text[0]?held_text:"-");return;}
        walk_end("again");AW_GalleryLightTestCenter();walk_start_at=realtime+SETTLE_S/2;return;
    }
    if(!AW_GalleryLightTestEnter())return;
    walk_pending=!strcmp(a,"1");
    Con_Printf("LIGHTTEST: to the light test corridor, the game's scripts paused (aw_lighttest_scripts 1 runs them)%s.\n",
               walk_pending?"; the walk starts there":"");
}
int AW_CycleItemsActive(void){return running;}
/* the player is in the corridor (its spawn): a waiting tester starts at its next frame, a waiting walk a moment later */
void AW_LightTestReady(void)
{
    held_ids[0][0]=held_ids[1][0]=held_text[0]=0;
    if(pending_first>0 && !running)field_ready=1;
    if(walk_pending){walk_pending=0;walk_start_at=realtime+SETTLE_S;}
}
void AW_CycleItemsDraw(void)
{
    char line[200];int w;
    if(!vid.buffer)return;
    if(running){if(!AW_CycleHudLine(line,sizeof(line),&item,current,total,step))return;}
    else if(AW_LightTestActive() && held_text[0])strcpy(line,held_text);
    else return;
    w=(int)strlen(line)*4+4;
    Draw_Fill(0,0,w<(int)vid.width?w:(int)vid.width,8,255);
    AW_SmallString(2,1,line);
    scr_copyeverything=1;
}
void AW_CycleItemsInit(void)
{
    Cmd_AddCommand("aw_cycleitems",command);Cmd_AddCommand("aw_lighttest",lighttest_command);
    Cvar_RegisterVariable(&lighttest_scripts);aw_mwscript_paused=scripts_paused;
}
#endif
