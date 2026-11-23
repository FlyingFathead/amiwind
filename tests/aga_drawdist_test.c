/* SPDX-License-Identifier: GPL-2.0-or-later
 * The draw distance's one owner (REGIONAL-DRAW-DISTANCE-68, engine/aga/src/aw_fog.c with the location fog,
 * aw_fog_location.c). One number, written by one rule from its inputs (the region's default from the table, the
 * player's own value when Auto is off, the map's limit, the location fog that only shortens), so:
 *   - whatever the order of the events (a walk across the Solstheim border, a load inside Solstheim, a load outside,
 *     the Options value, a place with its own shorter fog entered and left) and wherever Auto is switched in that
 *     order, the value at the end is the rule's for the final state;
 *   - the rule runs only on events: frames without a change run it 0 times (the old AW_DrawDistance ran it on every
 *     call), the table is read once;
 *   - a walk across a border eases over about a second, an arrival applies at once from the arrival point;
 *   - the table's trial rows (Solstheim's 540) apply only with aw_fog_region_trial on, a default row always.
 * The world here: cell x <= -2 the Moesring Mountains (catalogue index 9), x == -1 Brodir Grove (4), both Solstheim,
 * trial rows at 540; x == 7 a region with a default row at 400 (12); x == 5 Ald'ruhn (fog 280 by day, 240 at night),
 * x >= 20 no region; everything else the Ashlands (1, no row: the universal 300). The CHIM world reaches 1000. */
#include "quakedef.h"
#include "aw_sky.h"
#include "aw_links.h"
#include <assert.h>
#include <stdarg.h>
server_t sv;client_state_t cl;
float xcenter,ycenter,xscale,yscale;
vec3_t vpn={1,0,0},r_origin,vright,vup,modelorg;
viddef_t vid;refdef_t r_refdef;short *d_pzbuffer;unsigned int d_zwidth;
int r_daylight=256;
static int inside;
int AW_Interior(void){return inside;}
int R_SkyExterior(void){return !inside;}
const unsigned char *R_DayNightFogColours(void){return NULL;}
unsigned char R_DayNightSkyPixel(unsigned char c,float x,float y,float z,int fog){(void)x;(void)y;(void)z;(void)fog;return c;}
static byte fog_colours[4096];
byte *COM_LoadHunkFile(char *p){(void)p;return fog_colours;}
static void (*distance_command)(void);
static int argc=1;static char *argument="";
int Cmd_Argc(void){return argc;}
char *Cmd_Argv(int n){(void)n;return argument;}
void Cmd_AddCommand(char *name,void (*fn)(void)){if(!strcmp(name,"aw_fog_distance"))distance_command=fn;}
static char said[2048];
void Con_Printf(char *fmt,...){va_list a;va_start(a,fmt);vsnprintf(said+strlen(said),sizeof said-strlen(said),fmt,a);va_end(a);}
cvar_t aw_drawdistance={"aw_drawdistance","300",true,false,300};
static cvar_t *cvars[48];static int ncvars;
void Cvar_RegisterVariable(cvar_t *v){v->value=(float)atof(v->string);assert(ncvars<48);cvars[ncvars++]=v;}
static cvar_t *cvar(const char *name){
 int i;if(!strcmp(name,"aw_drawdistance"))return &aw_drawdistance;
 for(i=ncvars-1;i>=0;i--)if(!strcmp(cvars[i]->name,name))return cvars[i];
 assert(!"unknown cvar");return NULL;
}
void Cvar_SetValue(char *name,float value){cvar(name)->value=value;}
/* the image's tables: world/region-draw.txt (tools/region_draw.py) and the location fog's */
static const char region_table[]="# test table: index distance state id\nuniversal 300\n4 540 trial brodir grove region\n"
                                 "9 540 trial moesring mountains region\n12 400 default some default region\nbad line\n";
static int table_opens;
int COM_FOpenFile(char *name,FILE **f){
 const char *text=NULL;
 if(!strcmp(name,"world/region-draw.txt")){text=region_table;table_opens++;}
 else if(!strcmp(name,"world/fog-locations.txt"))text="Ald'ruhn 280 240\n";
 if(!text){*f=NULL;return -1;}
 *f=tmpfile();assert(*f);fputs(text,*f);rewind(*f);return (int)strlen(text);
}
/* map coordinates are the original world's on the frame maps; a room is off the world */
int AW_WorldToSource(const char *name,const float *local,float *world){
 if(inside || !name || !name[0])return 0;
 world[0]=local[0];world[1]=local[1];world[2]=local[2];return 1;
}
static int cell_of(const float *p){return (int)floor(p[0]/8192.0);}
int AW_RegionIndexAt(const float *p){int x=cell_of(p);return x==-1?4:x<-1?9:x==7?12:x>=20?-1:1;}
const char *AW_RegionNameAt(const float *p){int x=cell_of(p);return x==5?"Ashlands Region / Ald'ruhn":x<0?"Moesring Mountains":x>=20?NULL:"Ashlands Region";}
/* the rule's one call of the map limit: counts the rule's runs */
extern int (*aw_chim_view_reach)(void);
static int rule_runs;
static int world_reach(void){rule_runs++;return 1000;}
void AW_FogLocationInit(void);
int AW_SkyHazeNow(void);
static byte pixels[5];static short depth[5];
/* one rendered frame: what reads the distance each frame in the game */
static void frames(int n){
 int i;
 for(i=0;i<n;i++){cl.time+=.04;AW_CullBegin();AW_FogDraw();(void)AW_SkyHazeNow();(void)AW_DrawDistance();}
}
static int at_cell;
static void view_at(int x){r_refdef.vieworg[0]=(x+.5f)*8192;r_refdef.vieworg[1]=4096;r_refdef.vieworg[2]=0;}
static void walk_to(int x){while(at_cell!=x){at_cell+=x>at_cell?1:-1;view_at(at_cell);frames(1);}}
static void load(int x){
 float p[3];p[0]=(x+.5f)*8192;p[1]=4096;p[2]=0;
 strcpy(sv.name,x<0?"sl0051":"vf0001");AW_DrawDistanceArrive(p);at_cell=x;view_at(x);frames(1);
}
static void ev_cross_in(void){walk_to(0);walk_to(-1);}       /* across the border into Solstheim */
static void ev_load_inside(void){load(-3);}
static void ev_load_outside(void){load(2);}
static void ev_value(void){AW_SetDrawDistance(450);frames(1);}  /* the Options value: Auto off with it */
static void ev_enter_place(void){walk_to(4);walk_to(5);}
static void ev_leave_place(void){walk_to(5);walk_to(6);}
static void ev_auto_on(void){AW_SetDrawDistanceAuto(1);frames(1);}
static void ev_auto_off(void){AW_SetDrawDistanceAuto(0);frames(1);}
/* The rule, written out for the final state: what every order must end at. */
static int expected(void){
 int region=AW_RegionIndexAt(r_refdef.vieworg),solstheim=region==4 || region==9,d;
 int def=solstheim && cvar("aw_fog_region_trial")->value>0?540:region==12?400:300;
 d=cvar("aw_drawdistance_auto")->value?def:(int)aw_drawdistance.value;
 if(d>1000)d=1000;                                  /* the CHIM world's reach */
 if(at_cell==5 && d>280)d=280;                      /* Ald'ruhn by day */
 return d;
}
static void fresh(void){
 Cvar_SetValue("aw_drawdistance",300);Cvar_SetValue("aw_drawdistance_auto",1);Cvar_SetValue("aw_fog_region_trial",1);
 r_daylight=256;load(2);
}
typedef void (*event_t)(void);
static event_t base[6]={ev_cross_in,ev_load_inside,ev_load_outside,ev_value,ev_enter_place,ev_leave_place};
static const struct {event_t f;const char *name;} base_names[6]={{ev_cross_in,"cross-in"},{ev_load_inside,"load-inside"},
    {ev_load_outside,"load-outside"},{ev_value,"value-450"},{ev_enter_place,"enter-aldruhn"},{ev_leave_place,"leave-aldruhn"}};
static int orders,checked;
/* every order of the six events, with an Auto switch (on or off) in every position */
static void permute(event_t *e,int k){
 int i,position,turn;event_t t;
 if(k==1){
  for(turn=0;turn<2;turn++)for(position=0;position<=6;position++){
   fresh();
   for(i=0;i<=6;i++){
    if(i==position)(turn?ev_auto_on:ev_auto_off)();
    if(i<6)e[i]();
   }
   frames(30);                                      /* any ease ends within a second */
   if(AW_DrawDistance()!=expected()){
    int j,n;fprintf(stderr,"order:");for(j=0;j<6;j++)for(n=0;n<6;n++)if(e[j]==base_names[n].f)fprintf(stderr," %s",base_names[n].name);
    fprintf(stderr,"; Auto %s at %d; cell %d; got %d, the rule %d; auto %g value %g\n",turn?"on":"off",position,at_cell,
           AW_DrawDistance(),expected(),cvar("aw_drawdistance_auto")->value,aw_drawdistance.value);
   }
   assert(AW_DrawDistance()==expected());checked++;
  }
  orders++;return;
 }
 for(i=0;i<k;i++){
  permute(e,k-1);
  if(k%2){t=e[0];e[0]=e[k-1];e[k-1]=t;}else{t=e[i];e[i]=e[k-1];e[k-1]=t;}
 }
}
int main(void){
 int i,runs,mid;float p[3];
 for(i=0;i<4096;i++)fog_colours[i]=(byte)(i>>8);
 vid.buffer=pixels;vid.rowbytes=5;d_pzbuffer=depth;d_zwidth=5;r_refdef.vrect.width=5;r_refdef.vrect.height=1;
 AW_FogLocationInit();AW_FogInit();
 assert(cvar("aw_drawdistance_auto")->value==1 && cvar("aw_drawdistance_auto")->archive);   /* Auto on by default, saved */
 assert(cvar("aw_fog_region_trial")->value==0 && cvar("aw_fog_region_trial")->archive);     /* the trial rows off */
 aw_chim_view_reach=world_reach;sv.active=1;
 /* trial off (the default): Solstheim takes the universal 300; a default row applies without the trial switch */
 load(-3);frames(2);assert(AW_DrawDistance()==300);
 load(7);frames(2);assert(AW_DrawDistance()==400);
 /* the arrival uses the arrival point, not the view of the map before (stale until the next frame) */
 Cvar_SetValue("aw_fog_region_trial",1);load(2);frames(2);assert(AW_DrawDistance()==300);
 p[0]=-2.5f*8192;p[1]=4096;p[2]=0;strcpy(sv.name,"sl0051");AW_DrawDistanceArrive(p);
 assert(AW_DrawDistance()==540);                    /* before any frame: the ring is primed at 540 */
 at_cell=-3;view_at(-3);frames(1);assert(AW_DrawDistance()==540);
 assert(table_opens==1);                            /* the table is read once */
 /* quiet frames run the rule 0 times, however often the distance is read */
 frames(5);runs=rule_runs;frames(200);for(i=0;i<1000;i++)(void)AW_DrawDistance();
 assert(rule_runs==runs);
 r_daylight=128;frames(5);assert(rule_runs==runs);  /* the daylight matters only in a place with its own fog */
 r_daylight=256;
 /* one event = one run */
 AW_SetDrawDistanceAuto(1);assert(rule_runs==runs+1);
 /* a walk across the border eases over about a second; then it holds */
 load(0);frames(2);assert(AW_DrawDistance()==300);
 at_cell=-1;view_at(-1);frames(1);mid=AW_DrawDistance();assert(mid>300 && mid<540);
 frames(10);assert(AW_DrawDistance()>mid && AW_DrawDistance()<540);
 frames(20);assert(AW_DrawDistance()==540);runs=rule_runs;frames(50);assert(rule_runs==runs);
 /* back out: the same way down; a jump (a load) applies at once */
 at_cell=0;view_at(0);frames(1);assert(AW_DrawDistance()<540 && AW_DrawDistance()>300);
 load(-3);assert(AW_DrawDistance()==540);
 /* the location fog only shortens, with Auto and without; its night value follows the daylight */
 load(4);walk_to(5);assert(AW_DrawDistance()==280);
 r_daylight=128;frames(1);assert(AW_DrawDistance()==240);r_daylight=256;frames(1);assert(AW_DrawDistance()==280);
 /* Auto off: the player's value everywhere (unchecking starts it at the region's distance in effect: no jump) */
 load(-3);AW_SetDrawDistanceAuto(0);assert(aw_drawdistance.value==540 && AW_DrawDistance()==540);
 AW_SetDrawDistance(450);assert(AW_DrawDistance()==450 && !cvar("aw_drawdistance_auto")->value);
 load(2);frames(2);assert(AW_DrawDistance()==450);walk_to(5);assert(AW_DrawDistance()==280);
 /* the console's raw cvars reach the rule through the watch */
 Cvar_SetValue("aw_drawdistance",600);frames(1);assert(AW_DrawDistance()==280);walk_to(6);assert(AW_DrawDistance()==600);
 Cvar_SetValue("aw_drawdistance_auto",1);frames(1);assert(AW_DrawDistance()==300);
 /* dbg fog distance: N is the player's value (Auto off), "auto" turns Auto on; the report says which */
 assert(distance_command);argc=2;argument="500";distance_command();
 assert(AW_DrawDistance()==500 && !cvar("aw_drawdistance_auto")->value);
 argument="auto";said[0]=0;distance_command();assert(cvar("aw_drawdistance_auto")->value && AW_DrawDistance()==300);
 assert(strstr(said,"auto"));argc=1;said[0]=0;distance_command();assert(strstr(said,"auto, 300 local units"));
 argc=2;argument="5000";distance_command();assert(cvar("aw_drawdistance_auto")->value);argc=1;   /* invalid: unchanged */
 /* a cell without a region: the universal default, never the last region's (that would depend on the way taken) */
 load(-3);frames(1);assert(AW_DrawDistance()==540);load(25);frames(1);assert(AW_DrawDistance()==300);
 /* every order */
 permute(base,6);
 assert(orders==720 && checked==720*14);
 puts("draw distance: one owner; the same end value in every order of 6 events with Auto switched in each of 7 places "
      "(10080 runs); 0 rule runs on quiet frames; ease over a second, arrivals at once; trial rows off by default");
 return 0;
}
