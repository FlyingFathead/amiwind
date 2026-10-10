/* SPDX-License-Identifier: GPL-2.0-or-later
 * CHIM through the engine's own entry points on a synthetic world written by
 * tests/chim_fixture.py (run in its directory). model.c is included for the
 * brush decoders; aw_scenery.c (the hook owner), world.c (collision),
 * r_efrag.c (efrags), mathlib.c and the chim/ sources are linked.
 *
 *   legacy     no chim/world.cwi: no hook is set, nothing changes
 *   inactive   CHIM data, but the map names no frame: nothing loads
 *   ring       prime, sharing, placements once, efrags, collision against
 *              SV_ClipMoveToEntity, reach copies, moving, read budgets,
 *              streaming over several frames, map change; the frame world:
 *              terrain grafted into the map's world model (structure, hull 0
 *              and hull 1, water contents, PVS rows, surface caches moved,
 *              static efrags and edict leaves linked again, frozen actors)
 *   spawn      the spawn hook loads and grafts the ring before any trace
 *   evict      a zone smaller than the frame: LRU eviction and reloads
 *   cache      -chimcache: shared models survive a map change
 *   graftmodes the incremental frame world equals the full rebuild, frame by
 *              frame (CHIM-REBUILD-COST-33)
 *   budget     chunks join within the per-frame budget; the ground stays
 *   ahead      prefetch ahead of the player; the ring follows the view distance
 *   pin        a streamed model keeps its file open while every other file
 *              of the world is opened between its steps (CHIM-PACK-LRU-STREAM-35)
 *   baddata    damaged model images (one decoded whole, one streamed) and a
 *              texture with a mip offset outside its pixels: the loads fail,
 *              the map runs on (CHIM-BRUSH-BAD-DATA-35, H15)
 *   efragcap   a low efrag limit: placements wait unlinked, the nearest first,
 *              no Host_Error; all link again when the limit is back (CHIM-EFRAG-UNCAPPED-35)
 *   farfail    the frame world fails after the far terrain loaded: the map keeps
 *              the far terrain as its floor (CHIM-GRAFT-FAIL-NO-FLOOR-35)
 */
#include <assert.h>
#include <setjmp.h>
#include <stdarg.h>
#include <stdint.h>
#include <sys/stat.h>
#include "../engine/aga/src/model.c"
#include "d_local.h"
#include "chim/chim_local.h"
#include "aw_horizon.h"

qboolean aw_loading_music=false;
static short same_short(short v){return v;}
static int same_long(int v){return v;}
static float same_float(float v){return v;}
short (*LittleShort)(short)=same_short;
int (*LittleLong)(int)=same_long;
float (*LittleFloat)(float)=same_float;
static texture_t notexture;
texture_t *r_notexture_mip=&notexture;

/* ---------------------------------------------------------------- engine stubs */

#define HEAP_BYTES (16*1024*1024)
static byte *heap;
static int low, high;
quakeparms_t host_parms;
int host_framecount, r_framecount, r_visframecount;
client_state_t cl;
client_static_t cls;
server_t sv;
viddef_t vid;
entity_t cl_entities[MAX_EDICTS];
entity_t cl_static_entities[MAX_STATIC_ENTITIES];
efrag_t cl_efrags[MAX_EFRAGS];
entity_t *cl_visedicts[MAX_VISEDICTS];
int cl_numvisedicts;
int aw_efrags_used, aw_efrags_peak;
char *pr_strings = "\0func_wall\0";
void (*aw_chim_player)(vec3_t);
int (*aw_chim_frozen)(edict_t *);
void (*aw_chim_spawn)(vec3_t);
int (*aw_chim_floor)(const vec3_t origin, float *lowest, float *surface);	/* aw_walk.c (the terrain floor hook chim_far.c sets) */
const char *(*aw_chim_town_map)(const char *);
mleaf_t *r_viewleaf, *r_oldviewleaf;
int (*aw_chim_rcount)(char *out, int size, long frames);
static double fake_clock;
double Sys_FloatTime(void){return fake_clock+=0.0001;}
int pr_edict_size = sizeof(edict_t);
int SV_HullPointContents (hull_t *hull, int num, vec3_t p);
/* common.c's links and the progs globals SV_LinkEdict reaches. */
void ClearLink(link_t *l){l->prev=l->next=l;}
void RemoveLink(link_t *l){l->next->prev=l->prev;l->prev->next=l->next;}
void InsertLinkBefore(link_t *l,link_t *before){l->next=before;l->prev=before->prev;l->prev->next=l;l->next->prev=l;}
globalvars_t *pr_global_struct;
void PR_ExecuteProgram(func_t f){assert(!"no triggers in this test");}
static edict_t edicts[8];
int com_argc = 1;
static char *argv_storage[4] = {"test", NULL, NULL, NULL};
char **com_argv = argv_storage;
static int expect_error;
static jmp_buf failure;
#define VectorSet(v,x,y,z) ((v)[0]=(x),(v)[1]=(y),(v)[2]=(z))

void *Hunk_AllocName(int size,char *name){
    byte *p;
    assert(size>=0);size=16+((size+15)&~15);
    assert(low+high+size<=HEAP_BYTES);p=heap+low;low+=size;memset(p,0,size);return p+16;
}
int Hunk_LowMark(void){return low;}
void Hunk_FreeToLowMark(int mark){assert(mark>=0 && mark<=low);memset(heap+mark,0,low-mark);low=mark;}
int Hunk_HighMark(void){return high;}
void Hunk_FreeToHighMark(int mark){assert(mark>=0 && mark<=high);high=mark;}
void *Hunk_TempAlloc(int size){abort();}
void Sys_Error(char *fmt,...){
    va_list args;
    if(!expect_error){va_start(args,fmt);vfprintf(stderr,fmt,args);va_end(args);fputc('\n',stderr);abort();}
    longjmp(failure,1);
}
void Host_Error(char *fmt,...){va_list args;va_start(args,fmt);vfprintf(stderr,fmt,args);va_end(args);abort();}
static char console[8192];static int console_used,console_capture;
void Con_Printf(char *fmt,...){
    va_list args;
    if(console_capture && console_used<(int)sizeof(console)-1){
        va_start(args,fmt);console_used+=vsnprintf(console+console_used,sizeof(console)-console_used,fmt,args);va_end(args);
        if(console_used>(int)sizeof(console)-1)console_used=sizeof(console)-1;
    }
    if(!getenv("CHIM_VERBOSE"))return;
    va_start(args,fmt);vprintf(fmt,args);va_end(args);
}
void Con_DPrintf(char *fmt,...){}
void *Cache_Check(cache_user_t *c){return NULL;}
void Cache_Free(cache_user_t *c){abort();}
void R_InitSky(texture_t *tx){}
int Q_strncmp(char *a,char *b,int n){return strncmp(a,b,n);}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
void Q_strncpy(char *a,char *b,int n){strncpy(a,b,n);}
int Q_atoi(char *s){return atoi(s);}
int COM_CheckParm(char *p){int i;for(i=1;i<com_argc;i++)if(!strcmp(com_argv[i],p))return i;return 0;}
void COM_FileBase(char *in,char *out){
    char *slash=strrchr(in,'/'),*dot;const char *s=slash?slash+1:in;
    strncpy(out,s,31);out[31]=0;dot=strrchr(out,'.');if(dot)*dot=0;
}
static long opens;
int COM_FOpenFile(char *name,FILE **file){
    long size;
    *file=fopen(name,"rb");if(!*file)return -1;
    opens++;
    fseek(*file,0,SEEK_END);size=ftell(*file);fseek(*file,0,SEEK_SET);return (int)size;
}
static cvar_t *cvars[48];static int numcvars;
/* As cvar.c: a second registration of the same variable is refused. */
void Cvar_RegisterVariable(cvar_t *v){
    int i;for(i=0;i<numcvars;i++)if(cvars[i]==v)return;
    assert(numcvars<48);v->value=(float)atof(v->string);cvars[numcvars++]=v;
}
static void set_cvar(const char *name,float value){
    int i;for(i=0;i<numcvars;i++)if(!strcmp(cvars[i]->name,name)){cvars[i]->value=value;return;}
    abort();
}
void Cvar_SetValue(char *name,float value){set_cvar(name,value);}
static xcommand_t chim_tp_command,chim_command;
static char *cmd_args[4];static int cmd_argc;
void Cmd_AddCommand(char *name,xcommand_t f){if(!strcmp(name,"chim_tp"))chim_tp_command=f;if(!strcmp(name,"chim"))chim_command=f;}
int Cmd_Argc(void){return cmd_argc;}
char *Cmd_Argv(int i){return i<cmd_argc?cmd_args[i]:"";}
float Q_atof(char *s){return (float)atof(s);}
/* common.c's COM_Parse, as Quake has it (chim_statics.c reads entity text). */
char com_token[1024];
char *COM_Parse(char *data){
    int c,len=0;
    com_token[0]=0;
    if(!data)return NULL;
skipwhite:
    while((c=*data)<=' '){if(!c)return NULL;data++;}
    if(c=='/' && data[1]=='/'){while(*data && *data!='\n')data++;goto skipwhite;}
    if(c=='\"'){
        data++;
        while(1){c=*data++;if(c=='\"' || !c){com_token[len]=0;return data;}com_token[len++]=c;}
    }
    if(c=='{' || c=='}' || c==')' || c=='(' || c=='\'' || c==':'){com_token[len++]=c;com_token[len]=0;return data+1;}
    do{com_token[len++]=c;data++;c=*data;if(c=='{' || c=='}' || c==')' || c=='(' || c=='\'' || c==':')break;}while(c>32);
    com_token[len]=0;return data;
}
int (*aw_chim_entity)(char **data);
/* What Mod_ForName and the sprite loader reach (streamed statics). The
 * test's alias model is missing, so the loaders behind these never run. */
int r_pixbytes=1;unsigned short d_8to16table[256];int com_filesize;
void Q_memset(void *d,int f,int n){memset(d,f,n);}
void Q_memcpy(void *d,void *s,int n){memcpy(d,s,n);}
byte *COM_LoadStackFile(char *path,void *buffer,int size){return NULL;}
void *Cache_Alloc(cache_user_t *c,int size,char *name){abort();}
void Draw_BeginDisc(void){}
void Draw_EndDisc(void){}
void AW_LogBegin(int log){}
void AW_LogEnd(int log){}
void AW_LogPrintf(int log,const char *format,...){}
server_static_t svs;
void AW_BarrierClip(vec3_t a,vec3_t b,vec3_t c,vec3_t d,edict_t *e,trace_t *t){}
eval_t *GetEdictFieldValue(edict_t *e,char *name){return NULL;}
int SV_ModelIndex(char *name){return 1;}
int AW_NodeVisible(short *bounds){return 1;}
float R_SpriteEntityScale(const entity_t *e){return 1;}
static char subtitle[64];static int subtitles;
/* zone.c's load peak: the Hunk in use (low + high), as after a load. */
int AW_HeapLoadPeak(void){return low+high;}
void AW_UISubtitle(const char *name,const char *text,double duration){strncpy(subtitle,text,sizeof(subtitle)-1);subtitles++;}
/* aw_fog.c's view distance: the setting (0: the world's draw distance),
 * limited on a CHIM map by its world's data, as AW_DrawDistance does. */
int (*aw_chim_view_reach)(void);
/* aw_hud.c: original coordinates on the active frame (the debug HUD's GLOBAL row and cell). */
int (*aw_chim_source)(const float *local,float *world);
/* aw_fog.c's far terrain hook and aw_horizon.c's grid rasterizer (tested in
 * aga_chim_far_test.c): here only that the frame's layer is handed over. */
void (*aw_chim_far_draw)(byte colour,int distance);
static const aw_horizon_grid_t *far_drawn;static int far_draws;
void AW_HorizonGrid(const aw_horizon_grid_t *grid,byte colour,int distance,int cull){
    (void)colour;(void)distance;(void)cull;far_drawn=grid;far_draws++;
}
void AW_HorizonGridCounts(long *out){memset(out,0,9*sizeof *out);}
cvar_t aw_drawdistance={"aw_drawdistance","0"};
int AW_DrawDistance(void){
    int r=aw_chim_view_reach?aw_chim_view_reach():0,d=(int)aw_drawdistance.value;
    if(d<=0)d=(int)chim_frame.settings.draw_distance;
    return r>0 && d>r?r:d;
}

/* ---------------------------------------------------------------- world */

/* A world model with one split plane x = 0: leaf 1 in front, leaf 2 behind. */
static model_t world;
static mnode_t world_nodes[1];
static mleaf_t world_leafs[3];
static mplane_t world_plane;
static void make_world(void){
    memset(&world,0,sizeof(world));memset(world_nodes,0,sizeof(world_nodes));memset(world_leafs,0,sizeof(world_leafs));
    memset(&world_plane,0,sizeof(world_plane));world_plane.normal[0]=1;world_plane.type=0;
    world_nodes[0].plane=&world_plane;
    world_nodes[0].children[0]=(mnode_t *)&world_leafs[1];world_nodes[0].children[1]=(mnode_t *)&world_leafs[2];
    world_leafs[0].contents=CONTENTS_SOLID;world_leafs[1].contents=CONTENTS_EMPTY;world_leafs[2].contents=CONTENTS_EMPTY;
    world.nodes=world_nodes;world.leafs=world_leafs;world.numleafs=2;world.type=mod_brush;strcpy(world.name,"maps/chimtest.bsp");
    /* The standing hulls as model.c sets them for every brush model. */
    VectorSet(world.hulls[1].clip_mins,-7.32f,-7.12f,-16.625f);VectorSet(world.hulls[1].clip_maxs,7.32f,7.12f,16.625f);
    VectorSet(world.hulls[2].clip_mins,-32,-32,-24);VectorSet(world.hulls[2].clip_maxs,32,32,64);
}
static int leaf_holds(mleaf_t *leaf,const entity_t *ent){
    efrag_t *ef;
    for(ef=leaf->efrags;ef;ef=ef->leafnext)if(ef->entity==ent)return 1;
    return 0;
}
static int leaf_count(mleaf_t *leaf){efrag_t *ef;int n=0;for(ef=leaf->efrags;ef;ef=ef->leafnext)n++;return n;}
static int world_efrags(void){int i,n=0;for(i=1;i<=world.numleafs;i++)n+=leaf_count(&world.leafs[i]);return n;}
static mleaf_t *leaf_at(float x,float y,float z){vec3_t p;p[0]=x;p[1]=y;p[2]=z;return Mod_PointInLeaf(p,&world);}
static int contents_at(float x,float y,float z){vec3_t p;p[0]=x;p[1]=y;p[2]=z;return SV_PointContents(p);}
/* Every efrag of an entity sits in a leaf of the current world that lists it. */
static void efrags_in_world(const entity_t *ent){
    efrag_t *ef;
    for(ef=ent->efrag;ef;ef=ef->entnext){
        assert(ef->leaf>=world.leafs+1 && ef->leaf<=world.leafs+world.numleafs);
        assert(leaf_holds(ef->leaf,ent));
    }
}
static void free_efrags_clean(void){efrag_t *ef;for(ef=cl.free_efrags;ef;ef=ef->entnext)assert(!ef->leaf);}

/* The frame world obeys Quake's world rules: faces on their node's plane and
 * their vertexes on it, marks inside the surfaces, hull 0 = the node tree.
 * Checked for every node Quake can reach from the root (the incremental pool
 * has free ranges between chunks that nothing reaches). */
static int reached;
static void check_node(mnode_t *n){
    int j,k,e;
    if(n->contents<0)return;
    reached++;
    assert(n>=world.nodes && n<world.nodes+world.numnodes);
    {
        assert(n->plane>=world.planes && n->plane<world.planes+world.numplanes);
        assert(n->firstsurface+n->numsurfaces<=world.numsurfaces);
        for(j=0;j<2;j++){
            mnode_t *c=n->children[j];
            assert(c->parent==n || (mleaf_t *)c==world.leafs);
            if(c->contents<0)assert((mleaf_t *)c>=world.leafs && (mleaf_t *)c<=world.leafs+world.numleafs);
            else assert(c>=world.nodes && c<world.nodes+world.numnodes);
        }
        for(j=n->firstsurface;j<n->firstsurface+n->numsurfaces;j++){
            msurface_t *s=&world.surfaces[j];
            assert(s->plane->dist==n->plane->dist && VectorCompare(s->plane->normal,n->plane->normal));
            for(k=0;k<s->numedges;k++){
                int se=world.surfedges[s->firstedge+k];
                mvertex_t *v;
                e=se<0?-se:se;assert(e>0 && e<world.numedges);
                v=&world.vertexes[world.edges[e].v[se<0?1:0]];
                assert(fabs(DotProduct(v->position,s->plane->normal)-s->plane->dist)<0.01);
            }
        }
    }
    check_node(n->children[0]);check_node(n->children[1]);
}
static void check_world(void){
    int i,j;
    assert(world.nodes==(mnode_t *)world.nodes && world.nodes->contents==0 && world.hulls[0].firstclipnode==0);
    assert(world.hulls[0].lastclipnode==world.numnodes-1 && world.edgecache_count==world.numedges);
    reached=0;check_node(world.nodes);
    assert(reached>0 && reached<=world.numnodes);
    for(i=1;i<=world.numleafs;i++){
        mleaf_t *l=&world.leafs[i];
        for(j=0;j<l->nummarksurfaces;j++)
            assert(l->firstmarksurface[j]>=world.surfaces && l->firstmarksurface[j]<world.surfaces+world.numsurfaces);
    }
    for(i=0;i<400;i++){
        /* Off every plane: Quake sends a point on a plane to the front in hull
         * traces but to the back in Mod_PointInLeaf. */
        vec3_t p;p[0]=-499.63f+(float)((i*37)%1000);p[1]=-499.71f+(float)((i*53)%1000);p[2]=-59.77f+(float)((i*11)%140);
        assert(SV_HullPointContents(&world.hulls[0],0,p)==Mod_PointInLeaf(p,&world)->contents);
    }
}

/* ---------------------------------------------------------------- helpers */

static const char *frame_map="{\n\"classname\" \"worldspawn\"\n\"_chim_frame\" \"0 0\"\n}\n{\n\"classname\" \"info_player_start\"\n}\n";
/* _chim_frame outside the worldspawn does not count. */
static const char *plain_map="{\n\"classname\" \"worldspawn\"\n\"wad\" \"x.wad\"\n}\n{\n\"_chim_frame\" \"0 0\"\n}\n";

static void reset_engine(void){
    low=high=0;memset(heap,0,HEAP_BYTES);
    host_parms.memsize=HEAP_BYTES;host_parms.membase=heap;
    memset(&cl,0,sizeof(cl));memset(&cls,0,sizeof(cls));memset(&sv,0,sizeof(sv));
    make_world();
    R_ClearEfrags(false);
}
/* SV_SpawnServer's order: world model and area nodes, then the catalogue;
 * then three actors are spawned and linked, and the client connects. */
static void begin_map(const char *entities){
    int i;
    if(getenv("CHIM_DEBUG"))set_cvar("chim_debug",(float)atoi(getenv("CHIM_DEBUG")));
    /* The full-zone methods (CHIM-CHUNK-LOAD-FAIL-33): 0 is the first method of each. */
    if(getenv("CHIM_RELEASE"))set_cvar("chim_release",(float)atoi(getenv("CHIM_RELEASE")));
    if(getenv("CHIM_PARTIAL"))set_cvar("chim_partial",(float)atoi(getenv("CHIM_PARTIAL")));
    strcpy(sv.name,"chimtest");sv.active=true;
    VectorSet(world.mins,-384,-384,-1024);VectorSet(world.maxs,384,384,2048);
    sv.worldmodel=&world;sv.models[1]=&world;
    memset(edicts,0,sizeof(edicts));sv.edicts=edicts;sv.num_edicts=5;sv.max_edicts=8;
    /* Edict 0 is the world, as SV_SpawnServer sets it up. */
    edicts[0].v.modelindex=1;edicts[0].v.solid=SOLID_BSP;edicts[0].v.movetype=MOVETYPE_PUSH;
    SV_ClearWorld();
    AW_SceneryBegin(entities);
    VectorSet(edicts[2].v.origin,64,64,40);edicts[2].v.movetype=MOVETYPE_STEP;
    VectorSet(edicts[3].v.origin,-330,-330,40);edicts[3].v.movetype=MOVETYPE_STEP;
    VectorSet(edicts[4].v.origin,-330,-330,40);edicts[4].v.movetype=MOVETYPE_PUSH;
    for(i=2;i<5;i++){
        edicts[i].v.modelindex=2;VectorSet(edicts[i].v.mins,-8,-8,-8);VectorSet(edicts[i].v.maxs,8,8,8);
        SV_LinkEdict(&edicts[i],false);
    }
    cls.signon=SIGNONS;cl.worldmodel=&world;cl.viewentity=1;
}
/* An edict's leaf numbers name the leaf of the world holding its origin. */
static void edict_leaf_ok(edict_t *e){
    int leafnum=(int)(Mod_PointInLeaf(e->v.origin,&world)-world.leafs)-1,i;
    for(i=0;i<e->num_leafs;i++)if(e->leafnums[i]==leafnum)return;
    assert(!"edict not linked to its own leaf");
}
/* Host_ClearMemory's order: the efrag pool goes first, then the catalogue. */
static void end_map(void){
    R_ClearEfrags(true);
    AW_SceneryClear();
    /* The map's own world model is back as it was loaded. */
    assert(world.nodes==world_nodes && world.leafs==world_leafs && world.numleafs==2 && !world.edgecache);
    Hunk_FreeToLowMark(0);
    make_world();
}
static void frame_at(float x,float y,float z){
    host_framecount++;r_framecount++;
    VectorSet(cl_entities[1].origin,x,y,z);
    AW_SceneryLink();
    assert(ChimZone_Check_Integrity());
}
static int active_count(void){return chim_frame.active;}
static int entry_at(float x,float y){
    int i;
    for(i=0;i<chim_frame.count;i++){chim_entry_t *e=&chim_frame.entries[i];
        if(x>=e->low[0] && x<e->high[0] && y>=e->low[1] && y<e->high[1])return i;}
    return -1;
}
/* Every placement of an active chunk is drawn by exactly one chunk, the owner
 * when it is active; efrags in the world leaves are exactly those linked. */
static int check_once(void){
    static unsigned char seen[1024];
    int i,j,linked=0,leaves=0,n,efrags,one,most,ef_n;efrag_t *ef;
    memset(seen,0,sizeof(seen));
    for(i=0;i<chim_frame.count;i++){
        chim_entry_t *e=&chim_frame.entries[i];chim_chunk_t *c=e->chunk.data;
        if(e->state!=CHIM_STATE_ACTIVE)continue;
        for(j=0;j<c->records;j++){
            chim_place_t *p=&c->places[j];
            if(!p->linked){assert(!p->ent.efrag);continue;}
            assert(p->pid<1024 && !seen[p->pid]);seen[p->pid]=1;linked++;
            if(j>=c->owned)assert(chim_frame.entries[p->owner].state!=CHIM_STATE_ACTIVE || chim_frame.entries[p->owner].partial);
            /* Drawn (efrags) unless the view chunk's placement list hides it. */
            if(p->leaves){assert(p->ent.model && p->ent.efrag);leaves+=p->leaves;}
            else assert(p->ent.model && !p->ent.efrag && chim_frame.view_entry>=0);
        }
    }
    for(i=0;i<chim_frame.count;i++){
        chim_entry_t *e=&chim_frame.entries[i];chim_chunk_t *c=e->chunk.data;
        if(e->state!=CHIM_STATE_ACTIVE)continue;
        /* Every placement drawn by one chunk, unless the story hides it (0.5)
         * or its chunk is partially active and its model has no room yet
         * (CHIM-CHUNK-LOAD-FAIL-33): only a partial chunk lacks a model. */
        for(j=0;j<c->records;j++){
            if(!c->places[j].ent.model){assert(e->partial && !c->places[j].linked);continue;}
            assert(seen[c->places[j].pid] || ((c->places[j].flags&CHIM_RECORD_STORY_HIDDEN) &&
                chim_story_hidden && chim_story_hidden()));
        }
        if(!e->partial)for(j=0;j<c->models;j++)assert(c->model_list[j].model);
    }
    ChimChunks_Counts(&n,&efrags,&one,&most);
    assert(n==linked && efrags==leaves);
    {int sc,sl,se,sm,sb;ChimStatics_Counts(&sc,&sl,&se,&sm,&sb);leaves+=se;}
    for(i=0;i<cl.num_statics;i++){efrags_in_world(&cl_static_entities[i]);for(ef_n=0,ef=cl_static_entities[i].efrag;ef;ef=ef->entnext)ef_n++;leaves+=ef_n;}
    assert(world_efrags()==leaves);
    free_efrags_clean();
    return linked;
}
static model_t *placement_any(void){
    int i,j;
    for(i=0;i<chim_frame.count;i++){
        chim_entry_t *e=&chim_frame.entries[i];chim_chunk_t *c=e->chunk.data;
        if(e->state!=CHIM_STATE_ACTIVE)continue;
        for(j=0;j<c->records;j++)if(c->places[j].linked)return c->places[j].ent.model;
    }
    abort();
}
static chim_place_t *placement(unsigned pid){
    int i,j;
    for(i=0;i<chim_frame.count;i++){
        chim_entry_t *e=&chim_frame.entries[i];chim_chunk_t *c=e->chunk.data;
        if(e->state!=CHIM_STATE_ACTIVE)continue;
        /* The fixture's ids; a later frame of a world counts on from its first id. */
        for(j=0;j<c->records;j++)if(c->places[j].pid==pid+chim_frame.first_pid && c->places[j].linked)return &c->places[j];
    }
    return NULL;
}

/* The trace a world.c brush entity gives for the same model, origin and yaw. */
static trace_t reference(model_t *m,const vec3_t origin,float yaw,vec3_t a,vec3_t mins,vec3_t maxs,vec3_t b){
    edict_t e;
    memset(&e,0,sizeof(e));e.v.solid=SOLID_BSP;e.v.movetype=MOVETYPE_PUSH;e.v.modelindex=3;
    VectorCopy(origin,e.v.origin);e.v.angles[1]=yaw;sv.models[3]=m;
    return SV_ClipMoveToEntity(&e,a,mins,maxs,b);
}
/* The world's own trace (hull 1 of the frame world). */
static trace_t world_trace(vec3_t a,vec3_t mins,vec3_t maxs,vec3_t b){
    static const vec3_t zero={0,0,0};
    return reference(&world,zero,0,a,mins,maxs,b);
}
static trace_t chim_trace(vec3_t a,vec3_t mins,vec3_t maxs,vec3_t b){
    trace_t t;
    memset(&t,0,sizeof(t));t.fraction=1;VectorCopy(b,t.endpos);
    AW_SceneryClip(a,mins,maxs,b,&t);
    return t;
}
static int close3(const vec3_t a,const vec3_t b){return fabs(a[0]-b[0])<1e-3 && fabs(a[1]-b[1])<1e-3 && fabs(a[2]-b[2])<1e-3;}
static void same_trace(const trace_t *a,const trace_t *b){
    assert(fabs(a->fraction-b->fraction)<1e-5);
    assert(a->allsolid==b->allsolid && a->startsolid==b->startsolid);
    assert(close3(a->endpos,b->endpos));
    if(a->fraction<1)assert(close3(a->plane.normal,b->plane.normal));
}

/* ---------------------------------------------------------------- scenarios */

static void legacy(void){
    reset_engine();Chim_Init();
    assert(!aw_chim_map_begin && !aw_chim_link && !aw_chim_clip && !aw_chim_player && !aw_chim_map_end);
    assert(!aw_chim_frozen && !aw_chim_spawn && !aw_chim_rcount && !aw_chim_town_map && !aw_chim_source);
    begin_map(frame_map);frame_at(0,0,40);
    assert(!Chim_Active() && low==0 && opens==0);
    printf("legacy ok\n");
}

static void inactive(void){
    reset_engine();Chim_Init();
    assert(aw_chim_map_begin && aw_chim_link && aw_chim_clip && aw_chim_player && aw_chim_map_end);
    assert(aw_chim_frozen && aw_chim_spawn && aw_chim_rcount && aw_chim_town_map && aw_chim_source);
    {float l[3]={1,2,3},w[3];assert(!aw_chim_source(l,w));} /* no frame map yet */
    {   /* A town runs as its CHIM frame map when maps/<town>-chim.bsp exists. */
        FILE *f;mkdir("maps",0777);f=fopen("maps/balmora-chim.bsp","wb");assert(f);fputs("x",f);fclose(f);
        assert(!strcmp(aw_chim_town_map("balmora"),"maps/balmora-chim.bsp"));
        assert(!aw_chim_town_map("seyda") && !strcmp(aw_chim_town_map("balmora"),"maps/balmora-chim.bsp"));
        set_cvar("chim_towns",0);assert(!aw_chim_town_map("balmora"));set_cvar("chim_towns",1);
        assert(aw_chim_town_map("balmora"));
        /* "chim" lists every town of the table with its mode. */
        console_used=0;console[0]=0;console_capture=1;assert(chim_command);chim_command();
        assert(strstr(console,"balmora      CHIM: maps/balmora-chim.bsp"));
        assert(strstr(console,"seyda        legacy (no frame map)"));
        /* The entity budgets are stated with the defines' names. */
        assert(strstr(console,"limits: static entities 0 of 512 (MAX_STATIC_ENTITIES)") && strstr(console,"(MAX_MSGLEN)"));
        set_cvar("chim_towns",0);console_used=0;console[0]=0;chim_command();
        assert(strstr(console,"balmora      legacy (chim_towns 0)"));
        set_cvar("chim_towns",1);console_capture=0;
        remove("maps/balmora-chim.bsp");
    }
    {   /* No CHIM fields on a map that is not a CHIM frame. */
        char text[256]="";assert(!aw_chim_rcount(text,sizeof text,1) && !text[0]);
    }
    opens=0;begin_map(plain_map);frame_at(0,0,40);
    assert(!Chim_Active() && low==0 && opens==0);
    end_map();
    printf("inactive ok\n");
}

static msurface_t *stay_surf,*leave_surf;
static surfcache_t *stay_block,*leave_block;

static void ring(void){
    vec3_t mins={-7.32f,-7.12f,-16.625f},maxs={7.32f,7.12f,16.625f},a,b;
    trace_t t,r;chim_place_t *p;int i,k,ticks,models,busy,linked;
    unsigned long before;
    reset_engine();Chim_Init();
    begin_map(frame_map);
    assert(Chim_Active() && low>0);
    {   /* The inverse of chim_tp: world = local x 4 + frame centre (Z x 4). */
        float l[3]={10,-3.5f,5},w[3];
        assert(aw_chim_source(l,w));
        assert(w[0]==40+chim_frame.frame.centre[0] && w[1]==-14+chim_frame.frame.centre[1] && w[2]==20);
    }
    /* Prime: the whole ring is loaded before the first frame. */
    frame_at(64,64,40);
    assert(active_count()>0 && !ChimModels_Busy());
    for(i=0;i<chim_frame.count;i++){
        chim_entry_t *e=&chim_frame.entries[i];
        float r=chim_frame.settings.draw_distance+chim_frame.settings.hysteresis;
        assert((e->state==CHIM_STATE_ACTIVE)==(e->distance<=r*r));
    }
    linked=check_once();
    models=(int)chim_world.model_loads;
    printf("prime: active=%d loaded=%d linked=%d models=%lu textures=%lu reads=%lu bytes=%lu streamed=%lu\n",
        chim_frame.active,chim_frame.loaded,linked,chim_world.model_loads,chim_world.texture_loads,
        chim_world.reads,chim_world.bytes_read,chim_world.streamed_models);
    /* Shared model 0 placed by pid 0 and pid 2: one model block. */
    {
        chim_zone_stats_t s;ChimZone_Stats(&s);
        assert(s.kind_blocks[CHIM_KIND_MODEL]==models);
        printf("zone: used=%d models=%d/%d textures=%d/%d chunks=%d/%d terrain=%d/%d index=%d buffer=%d\n",
            s.used_bytes,s.kind_blocks[CHIM_KIND_MODEL],s.kind_bytes[CHIM_KIND_MODEL],
            s.kind_blocks[CHIM_KIND_TEXTURE],s.kind_bytes[CHIM_KIND_TEXTURE],
            s.kind_blocks[CHIM_KIND_CHUNK],s.kind_bytes[CHIM_KIND_CHUNK],
            s.kind_blocks[CHIM_KIND_TERRAIN],s.kind_bytes[CHIM_KIND_TERRAIN],
            s.kind_bytes[CHIM_KIND_INDEX],s.kind_bytes[CHIM_KIND_BUFFER]);
    }
    check_world();
    /* The world is the map's own model; the terrain is in it. */
    assert(world.numleafs>active_count() && world.numsurfaces>=active_count() && world.lightdata);
    /* pid 0: model 0 at (32,32,0), inside one chunk: one air leaf. */
    p=placement(0);assert(p && p->leaves==1 && leaf_holds(leaf_at(32,32,40),&p->ent));
    /* pid 4: model 1 at (0,32,0), box y -9..73: four chunks, four air leaves. */
    p=placement(4);assert(p && p->leaves==4 && leaf_holds(leaf_at(-64,32,40),&p->ent) && leaf_holds(leaf_at(64,32,40),&p->ent));
    assert(leaf_holds(leaf_at(-64,-64,40),&p->ent) && leaf_holds(leaf_at(64,-64,40),&p->ent));
    /* Culling by leaf: when only the leaf west of x = 0 is visible,
     * R_StoreEfrags (from R_RecursiveWorldNode for visible leaves) sends
     * exactly the placements linked there, each once. */
    {
        int sent,one,placements,expect=0,j;mleaf_t *west=leaf_at(-64,32,40);
        r_framecount++;cl_numvisedicts=0;
        R_StoreEfrags(&west->efrags);
        for(i=0;i<chim_frame.count;i++){
            chim_chunk_t *c=chim_frame.entries[i].chunk.data;
            if(chim_frame.entries[i].state!=CHIM_STATE_ACTIVE)continue;
            for(j=0;j<c->records;j++)if(c->places[j].linked && leaf_holds(west,&c->places[j].ent))expect++;
        }
        ChimChunks_LastFrame(&sent,&one,&placements);
        assert(sent==expect && sent>=1 && sent<placements && cl_numvisedicts==leaf_count(west));
        assert(placement(4)->ent.visframe==r_framecount && placement(0)->ent.visframe!=r_framecount);
        printf("leaf culling: %d of %d placements sent\n",sent,placements);
    }
    /* The PVS: each chunk's row (it sees its neighbours) became a leaf row;
     * leaves of a chunk two away are not potentially visible. */
    {
        mleaf_t *here=leaf_at(64,64,40),*near=leaf_at(-64,64,40),*far=leaf_at(-200,64,40);
        byte *vis=Mod_LeafPVS(here,&world);
        int ni=(int)(near-world.leafs)-1,fi=(int)(far-world.leafs)-1;
        assert(here->compressed_vis && far->contents==CONTENTS_EMPTY);
        assert(vis[ni>>3]&(1<<(ni&7)));
        assert(!(vis[fi>>3]&(1<<(fi&7))));
        printf("pvs: leaf %d sees %d, not %d\n",(int)(here-world.leafs),(int)(near-world.leafs),(int)(far-world.leafs));
    }
    /* Contents: ground solid, air empty, the pond chunk water. */
    assert(contents_at(64,64,-5)==CONTENTS_SOLID && contents_at(64,64,5)==CONTENTS_EMPTY);
    i=entry_at(-330,-330);
    if(chim_frame.entries[i].state==CHIM_STATE_ACTIVE)assert(contents_at(-330,-330,-10)==CONTENTS_WATER);
    /* Actors: one in the ring runs, one outside it is frozen, a pusher never. */
    assert(!ChimChunks_Frozen(&edicts[2]) && !ChimChunks_Frozen(&edicts[4]));
    assert(ChimChunks_Frozen(&edicts[3])==(chim_frame.entries[i].state!=CHIM_STATE_ACTIVE));
    edict_leaf_ok(&edicts[2]);edict_leaf_ok(&edicts[3]);
    ChimChunks_Report();ChimGraft_Report();
    /* Collision: straight down onto pid 0, the same as world.c's. */
    p=placement(0);
    VectorSet(a,32,32,200);VectorSet(b,32,32,40);
    t=chim_trace(a,mins,maxs,b);r=reference(p->ent.model,p->ent.origin,0,a,mins,maxs,b);
    printf("down: chim %g %g %d %d ref %g %g %d %d\n",t.fraction,t.endpos[2],t.allsolid,t.startsolid,r.fraction,r.endpos[2],r.allsolid,r.startsolid);
    assert(t.fraction<1 && fabs(t.endpos[2]-(64+16.625))<0.1);
    same_trace(&t,&r);
    /* Yawed pid 3 (model 1, yaw 45) from 16 directions. The view from the
     * chunk at (64,64) does not list it (format 0.3 placement row): not
     * drawn, still solid. */
    p=placement(3);assert(p && p->ent.angles[1]==45 && !p->leaves && !p->ent.efrag && ChimChunks_Hidden()==1);
    for(k=0;k<16;k++){
        VectorSet(a,p->ent.origin[0]+60*cos(k*M_PI/8),p->ent.origin[1]+60*sin(k*M_PI/8),p->ent.origin[2]+20);
        VectorCopy(p->ent.origin,b);b[2]+=20;
        t=chim_trace(a,mins,maxs,b);r=reference(p->ent.model,p->ent.origin,45,a,mins,maxs,b);
        assert(t.fraction<1);same_trace(&t,&r);
    }
    /* Terrain is the world's hull: ground at z = 0, also across a chunk edge. */
    VectorSet(a,100,-15,200);VectorSet(b,100,-15,-100);
    t=world_trace(a,mins,maxs,b);assert(t.fraction<1 && fabs(t.endpos[2]-16.625)<0.1 && t.plane.normal[2]>0.99);
    VectorSet(a,-60,10,30);VectorSet(b,60,10,30);
    t=world_trace(a,mins,maxs,b);assert(t.fraction==1 && !t.startsolid);
    /* Placements no longer carry the terrain: their own clip misses it. */
    VectorSet(a,100,-15,200);VectorSet(b,100,-15,-100);
    t=chim_trace(a,mins,maxs,b);assert(t.fraction==1);
    /* Nothing collides in a chunk that is not active. */
    i=entry_at(-200,-200);assert(i>=0 && chim_frame.entries[i].state!=CHIM_STATE_ACTIVE);
    VectorSet(a,-200,-200,200);VectorSet(b,-200,-200,-100);
    t=world_trace(a,mins,maxs,b);assert(t.fraction==1);
    /* A static entity (as CL_ParseStatic links one) and a surface cache
     * block on a chunk that stays in the ring on the trip east and back
     * (x 256..384), and one on a chunk that leaves it (x -128..0). */
    {
        static surfcache_t stay,leave;
        cl_static_entities[0].model=placement(0)->ent.model;VectorSet(cl_static_entities[0].origin,40,90,0);
        cl.num_statics=1;R_AddEfrags(&cl_static_entities[0]);
        stay_surf=leaf_at(320,64,40)->firstmarksurface[0];stay_surf->cachehead=&stay;stay.owner=&stay_surf->cachehead;
        leave_surf=leaf_at(-64,-64,40)->firstmarksurface[0];leave_surf->cachehead=&leave;leave.owner=&leave_surf->cachehead;
        stay_block=&stay;leave_block=&leave;
        check_once();
    }

    /* Reach copy: east of the frame, pid 1's owner chunk drops out of the
     * active ring while the chunk holding its reach copy stays. */
    set_cvar("chim_read_kib",4);
    for(ticks=0;ticks<200;ticks++)frame_at(440,64,40);
    assert(!ChimModels_Busy());
    i=entry_at(64,64);assert(chim_frame.entries[i].state!=CHIM_STATE_ACTIVE);
    p=placement(1);assert(p);
    /* Another view chunk lists pid 3 again: drawn. */
    {chim_place_t *q=placement(3);assert(!q || q->leaves>0);}
    {
        int owner=p->owner,holder=-1,j;
        for(j=0;j<chim_frame.count;j++){chim_chunk_t *c=chim_frame.entries[j].chunk.data;
            if(chim_frame.entries[j].state==CHIM_STATE_ACTIVE && p>=c->places && p<c->places+c->records)holder=j;}
        assert(holder>=0 && holder!=owner && chim_frame.entries[owner].state!=CHIM_STATE_ACTIVE);
    }
    check_once();
    /* Back: the owner takes over its placement again. */
    for(ticks=0;ticks<200;ticks++)frame_at(64,64,40);
    p=placement(1);assert(p);
    {
        chim_chunk_t *c=chim_frame.entries[p->owner].chunk.data;
        assert(p>=c->places && p<c->places+c->owned);
    }
    check_once();
    check_world();
    /* The cache block of the chunk that stayed moved with its surface; the
     * other one was let go. */
    assert(stay_block->owner && *stay_block->owner==stay_block && stay_block->owner==&leaf_at(320,64,40)->firstmarksurface[0]->cachehead);
    assert(!leave_block->owner);
    efrags_in_world(&cl_static_entities[0]);
    edict_leaf_ok(&edicts[2]);edict_leaf_ok(&edicts[3]);
    printf("reach copies ok\n");

    /* Walk to the far corner with a small budget: model 0 is shared with
     * pid 2 there and is not read again; reads stay within the budget. */
    before=chim_world.model_loads;busy=0;
    {
        /* Pack reads plus the section reads of a stream (model.c's counter). */
        unsigned long last=chim_world.bytes_read+aw_load_disk_bytes,most=0,now,urgent=0,was;int margin,ahead,urgent_frames=0;
        ChimChunks_Streaming(&margin,&was,&ahead);
        for(ticks=0;ticks<400;ticks++){
            frame_at(-200,-200,40);
            now=chim_world.bytes_read+aw_load_disk_bytes;
            ChimChunks_Streaming(&margin,&urgent,&ahead);
            /* The jump lands the player where nothing is loaded: the chunks
             * within the collision margin load at once, past the budget when
             * they must (ground first); the ground under the player is there
             * from the first frame. Every other frame keeps the budget. */
            if(!ticks)assert(chim_frame.entries[entry_at(-200,-200)].grafted);
            if(urgent!=was)urgent_frames++;
            else if(now-last>most)most=now-last;
            was=urgent;last=now;
            if(ChimModels_Busy())busy++;
        }
        printf("walk: model loads %lu, streamed frames %d, largest frame read %lu (budget 4096, buffer %d, largest lump 40000), %d frames with urgent loads\n",
            chim_world.model_loads-before,busy,most,chim_world.buffer_bytes,urgent_frames);
        assert(urgent_frames<=2);
        /* A frame reads its budget plus at most one unit: a whole image that
         * fits the loading buffer, or one section of a streamed image. */
        assert(most<=4096+40000+1024 && most<=4096+(unsigned long)chim_world.buffer_bytes+40000);
    }
    i=entry_at(-200,-200);assert(chim_frame.entries[i].state==CHIM_STATE_ACTIVE);
    p=placement(2);assert(p && p->model==0);
    check_once();
    /* The big model (id 2, larger than the loading buffer) was streamed, and
     * it is the only model read on this walk: model 0 is shared. */
    assert(chim_world.streamed_models==1 && busy>=1 && chim_world.model_loads-before==1);
    p=placement(5);assert(p && p->model==2);
    /* The pond is in the world now: water, and its actor runs. */
    check_world();
    assert(contents_at(-330,-330,-10)==CONTENTS_WATER && contents_at(-330,-330,10)==CONTENTS_EMPTY);
    assert(!ChimChunks_Frozen(&edicts[3]) && ChimChunks_Frozen(&edicts[2])==(chim_frame.entries[entry_at(64,64)].state!=CHIM_STATE_ACTIVE));
    edict_leaf_ok(&edicts[3]);
    {
        int rebuilds,grafts,leafs,surfs,bytes;
        ChimGraft_Stats(&rebuilds,&grafts,&leafs,&surfs,&bytes);
        printf("frame world: %d rebuilds, %d chunks, %d leaves, %d surfaces, %d bytes\n",rebuilds,grafts,leafs,surfs,bytes);
        assert(grafts==active_count() && rebuilds>=3);
        /* dbg rcount's CHIM fields: active/grafted/loaded chunks first. */
        {
            char text[256];int a2,g2,l2;
            assert(aw_chim_rcount(text,sizeof text,1));
            printf("rcount fields:%s%c",text,10);
            assert(sscanf(text," | chim %d/%d/%d",&a2,&g2,&l2)==3 && a2==active_count() && g2==grafts && l2==chim_frame.loaded);
            assert(strstr(text," rb ") && strstr(text," pool ") && strstr(text," zone ") && strstr(text," op "));
        }
    }
    VectorSet(a,-200,-200,200);VectorSet(b,-200,-200,40);
    t=chim_trace(a,mins,maxs,b);assert(t.fraction<1 && fabs(t.endpos[2]-(64+16.625))<0.1);

    /* Map change: everything goes with the Hunk; no locked block is left. */
    end_map();
    {
        chim_zone_stats_t s;ChimZone_Stats(&s);
        assert(s.banks==0 && s.blocks==0);
    }
    assert(!Chim_Active());
    printf("ring ok\n");
}

/* A zone that holds the ring but not the whole frame: walking around evicts
 * least recently used models and chunks and reloads them when needed. */
static void evict(void){
    int ticks,i;chim_zone_stats_t s;
    reset_engine();Chim_Init();
    set_cvar("chim_zone_kib",(float)atoi(getenv("CHIM_ZONE_KIB")));
    set_cvar("chim_reserve_kib",0);
    begin_map(frame_map);assert(Chim_Active());
    for(i=0;i<4;i++){
        float x=i&1?-180:180,y=i&2?-180:180;
        for(ticks=0;ticks<100;ticks++)frame_at(x,y,40);
        check_once();
    }
    for(ticks=0;ticks<100;ticks++)frame_at(180,180,40);
    check_once();
    /* With room for the frame world, every active chunk is grafted; when a
     * rebuild finds no room, the chunks wait ungrafted and their actors stay
     * frozen. */
    {
        int rebuilds,grafts,leafs,surfs,bytes,grafted=0;
        ChimGraft_Stats(&rebuilds,&grafts,&leafs,&surfs,&bytes);
        for(i=0;i<chim_frame.count;i++){
            grafted+=chim_frame.entries[i].grafted;
            if(chim_frame.entries[i].grafted)assert(chim_frame.entries[i].state==CHIM_STATE_ACTIVE);
        }
        printf("evict: %d active, %d grafted, %d rebuilds\n",active_count(),grafted,rebuilds);
        assert(grafted==grafts);
        /* Rebuilds that found no room were retried and the world caught up. */
        assert(grafted==active_count());
        assert(ChimChunks_Frozen(&edicts[2])==!chim_frame.entries[entry_at(64,64)].grafted);
    }
    ChimZone_Stats(&s);
    printf("evict: evictions=%lu failures=%lu model_loads=%lu chunk_loads=%lu failed=%lu\n",
        s.evictions,s.failures,chim_world.model_loads,chim_world.chunk_loads,chim_world.failed_loads);
    /* A small zone evicts (LRU) or, when locked blocks leave no run large
     * enough, fails at once without evicting anything (H15). */
    printf("evict: unsatisfiable requests %lu%c",ChimZone_Unsatisfiable(),10);
    assert(s.evictions>0 || ChimZone_Unsatisfiable()>0);
    end_map();
    printf("evict ok\n");
}

/* CHIM-CHUNK-LOAD-FAIL-33: a zone too small for the ring's models. The
 * chunks within the collision margin of the player must always have their
 * ground in the frame world (no hole to fall into), a model without room
 * must not keep its chunk's ground out (partial activation), and loads must
 * not chase each other (thrash). CHIM_FIRST_METHOD runs chim_release 0 and
 * chim_partial 0 and expects the hole the owner fell through. */
static int ground_holes(float x,float y){
    int i,n=0;float m=chim_frame.settings.collision_margin;
    for(i=0;i<chim_frame.count;i++){chim_entry_t *e=&chim_frame.entries[i];
        float dx=x<e->low[0]?e->low[0]-x:x>e->high[0]?x-e->high[0]:0;
        float dy=y<e->low[1]?e->low[1]-y:y>e->high[1]?y-e->high[1]:0;
        if(dx*dx+dy*dy<=m*m && !(e->state==CHIM_STATE_ACTIVE && e->grafted))n++;}
    return n;
}
static void fullzone(void){
    static chim_user_t hog[64];
    int ticks,i,n=0,holes=0,steps=0,first=getenv("CHIM_FIRST_METHOD")!=NULL,k,e5;
    unsigned long band,ring,partial,zone,data,loads0;chim_zone_stats_t s;
    reset_engine();Chim_Init();
    set_cvar("chim_zone_kib",256);
    set_cvar("chim_reserve_kib",0);
    if(first){set_cvar("chim_release",0);set_cvar("chim_partial",0);}
    begin_map(frame_map);assert(Chim_Active());
    for(ticks=0;ticks<60;ticks++)frame_at(32,32,40);
    check_once();
    /* Starve the zone: nothing cached, and no free run of 30 KiB or more,
     * so model 2 (about 43 KB) never has room while the rest does. */
    for(k=1;k<CHIM_KINDS;k++)ChimZone_EvictKind(k,NULL);
    for(ChimZone_Stats(&s);s.largest_free>30*1024 && n<64;ChimZone_Stats(&s),n++){
        assert(ChimZone_Alloc(&hog[n],s.largest_free-30*1024,CHIM_KIND_BUFFER,99));
        ChimZone_Lock(hog[n].data);
    }
    assert(ChimZone_LargestUnlocked()<=30*1024);
    loads0=chim_world.model_loads;
    /* The pond chunk, where model 2 stands: its ground must be there. */
    e5=entry_at(-330,-300);
    for(ticks=0;ticks<120;ticks++){frame_at(-330,-300,40);if(ticks>=10){holes+=ground_holes(-330,-300)>0;steps++;}}
    check_once();
    ChimChunks_Pressure(&band,&ring,&partial,&zone,&data);
    printf("fullzone %s: %d of %d steps with a hole under the player; failed %lu for room, %lu bad data; released %lu+%lu; partial %lu; model loads %lu%c",
        first?"first method":"default",holes,steps,zone,data,band,ring,partial,chim_world.model_loads-loads0,10);
    assert(!data && zone>0);
    if(first)assert(holes==steps && chim_frame.entries[e5].state!=CHIM_STATE_ACTIVE);
    else{
        assert(holes==0 && partial>0);
        assert(chim_frame.entries[e5].state==CHIM_STATE_ACTIVE && chim_frame.entries[e5].partial);
        /* The model arrives when there is room, and the chunk completes. */
        for(i=0;i<n;i++){ChimZone_Unlock(hog[i].data);ChimZone_Free(&hog[i]);}
        for(ticks=0;ticks<120;ticks++)frame_at(-330,-300,40);
        check_once();
        assert(chim_frame.entries[e5].state==CHIM_STATE_ACTIVE && !chim_frame.entries[e5].partial);
        n=0;
    }
    /* No loads chasing each other while starved. */
    assert(chim_world.model_loads-loads0<=8);
    for(i=0;i<n;i++){ChimZone_Unlock(hog[i].data);ChimZone_Free(&hog[i]);}
    end_map();
    set_cvar("chim_release",1);set_cvar("chim_partial",1);
    printf("fullzone ok%c",10);
}

/* The spawn hook loads and grafts the ring around the arrival point at
 * once, before any trace and before the first physics or client frame. */
static void spawn(void){
    vec3_t at;
    reset_engine();Chim_Init();
    begin_map(frame_map);
    assert(aw_chim_spawn && !active_count());
    assert(contents_at(64,64,-5)==CONTENTS_EMPTY);	/* nothing grafted yet */
    VectorSet(at,64,64,40);aw_chim_spawn(at);
    assert(active_count()>0 && contents_at(64,64,-5)==CONTENTS_SOLID);
    check_world();check_once();
    /* chim_tp X Y takes original Morrowind coordinates: local = (world -
     * frame origin) x 0.25; the frame origin of the test frame is 0 0. The
     * player lands on the ground (standing hull half height 16.625). */
    {
        static client_t client;edict_t *player=&edicts[1];
        memset(player,0,sizeof(*player));
        VectorSet(player->v.mins,-7.32f,-7.12f,-16.625f);VectorSet(player->v.maxs,7.32f,7.12f,16.625f);
        player->v.solid=SOLID_SLIDEBOX;player->v.movetype=MOVETYPE_WALK;
        client.edict=player;svs.clients=&client;svs.maxclients=1;
        cmd_args[0]="chim_tp";cmd_args[1]="-1200";cmd_args[2]="-400";cmd_argc=3;
        assert(chim_tp_command);chim_tp_command();
        assert(fabs(player->v.origin[0]+300)<.01 && fabs(player->v.origin[1]+100)<.01);
        assert(fabs(player->v.origin[2]-(16.625f+1))<.1);
        /* The ring there was loaded first. */
        assert(chim_frame.entries[entry_at(-300,-100)].grafted);
        /* Outside the frame: refused, the player stays. */
        cmd_args[1]="99999";chim_tp_command();
        assert(fabs(player->v.origin[0]+300)<.01);
        svs.clients=NULL;svs.maxclients=0;cmd_argc=0;
    }
    end_map();
    printf("spawn ok\n");
}

/* A Balmora-sized frame (24 x 24 chunks, 64 sectors, 400 placements of 40
 * models): priming the ring stays linear in the ring's work. The first real
 * run hung at "Loading" with a scheduler that rescanned every chunk and every
 * resident block for each step (CHIM-SCHEDULER-SCAN-33). */
extern unsigned long chim_need_calls;
static void bigframe(void){
    vec3_t at;unsigned long before;int i,linked;
    reset_engine();Chim_Init();
    set_cvar("chim_zone_kib",8192);set_cvar("chim_reserve_kib",0);
    begin_map(frame_map);assert(Chim_Active() && chim_frame.count==576);
    VectorSet(world.mins,-1536,-1536,-1024);VectorSet(world.maxs,1536,1536,2048);
    before=chim_need_calls;
    VectorSet(at,0,0,40);aw_chim_spawn(at);
    linked=check_once();
    printf("bigframe: %d active, %d loaded, %lu need calls, %lu model loads, %d linked%c",
        active_count(),chim_frame.loaded,chim_need_calls-before,chim_world.model_loads,linked,10);
    assert(active_count()>=60 && chim_world.model_loads>=10);
    /* Each step of the prime visits the candidates nearest first; the old
     * scan took about a hundred times more. */
    assert(chim_need_calls-before < (unsigned long)(chim_frame.loaded+chim_world.model_loads+active_count())*40);
    check_world();
    for(i=0;i<20;i++)frame_at(300,300,40);
    check_once();check_world();
    end_map();
    printf("bigframe ok%c",10);
}

/* -chimcache: models and textures in the persistent bank survive the map. */
static void cache(void){
    unsigned long loads;int ticks;
    com_argc=3;argv_storage[1]="-chimcache";argv_storage[2]="2048";
    reset_engine();Chim_Init();
    begin_map(frame_map);
    for(ticks=0;ticks<5;ticks++)frame_at(64,64,40);
    loads=chim_world.model_loads;assert(loads>0);
    end_map();
    {
        chim_zone_stats_t s;ChimZone_Stats(&s);
        assert(s.banks==1 && s.kind_blocks[CHIM_KIND_MODEL]>0 && !s.kind_blocks[CHIM_KIND_CHUNK]);
    }
    begin_map(frame_map);
    for(ticks=0;ticks<5;ticks++)frame_at(64,64,40);
    assert(chim_world.model_loads==loads);
    check_once();
    end_map();
    printf("cache ok\n");
}

/* CHIM-ZONE-RING-THRASH-33: in a zone too small for the load ring, a player
 * standing still reads nothing once the ring has settled when prefetch only
 * uses free room (chim_prefetch_room 1); with prefetch allowed to evict, the
 * prefetched chunks evict each other's models in turn and reads go on. */
static void still(void){
    int room,ticks,i;unsigned long reads[2],ev[2];chim_zone_stats_t s;
    for(room=1;room>=0;room--){
        reset_engine();Chim_Init();
        set_cvar("chim_zone_kib",(float)atoi(getenv("CHIM_ZONE_KIB")));
        set_cvar("chim_reserve_kib",0);set_cvar("chim_prefetch_room",room);
        begin_map(frame_map);assert(Chim_Active());
        for(ticks=0;ticks<300;ticks++)frame_at(150,150,40);
        check_once();
        ChimZone_Stats(&s);reads[room]=chim_world.reads;ev[room]=s.evictions;
        for(ticks=0;ticks<300;ticks++)frame_at(150,150,40);
        ChimZone_Stats(&s);reads[room]=chim_world.reads-reads[room];ev[room]=s.evictions-ev[room];
        for(i=0;i<chim_frame.count;i++)
            if(chim_frame.entries[i].state==CHIM_STATE_ACTIVE)assert(chim_frame.entries[i].grafted);
        printf("still room %d: %lu reads, %lu evictions in 300 ticks; held %lu%c",room,reads[room],ev[room],
            ChimChunks_PrefetchHeld(),10);
        end_map();
    }
    set_cvar("chim_prefetch_room",1);
    assert(reads[1]==0 && ev[1]==0);
    printf("still ok%c",10);
}

/* CHIM-ZONE-RING-THRASH-33: a jump across the frame in a full zone. The old
 * ring's terrain stays locked by the frame world until a rebuild drops it;
 * with the frame-world slots reserved at map start that rebuild finds room
 * (Balmora in FS-UAE: CHIM-ZONE-RING-THRASH-33); here, in a zone too small
 * for a full slot, the slots are capped at a twelfth of the zone and the
 * player lands either way. */
static void jump(void){
    static client_t client;edict_t *player=&edicts[1];int pool,ticks,landed[2];
    unsigned long failures,outgrown;int s0,s1;
    for(pool=0;pool<2;pool++){
        reset_engine();Chim_Init();
        set_cvar("chim_zone_kib",(float)atoi(getenv("CHIM_ZONE_KIB")));
        set_cvar("chim_reserve_kib",0);set_cvar("chim_pool_kib",pool?512:0);
        begin_map(frame_map);assert(Chim_Active());
        for(ticks=0;ticks<300;ticks++)frame_at(150,150,40);
        memset(player,0,sizeof(*player));
        VectorSet(player->v.mins,-7.32f,-7.12f,-16.625f);VectorSet(player->v.maxs,7.32f,7.12f,16.625f);
        player->v.solid=SOLID_SLIDEBOX;player->v.movetype=MOVETYPE_WALK;VectorSet(player->v.origin,150,150,40);
        client.edict=player;svs.clients=&client;svs.maxclients=1;
        cmd_args[0]="chim_tp";cmd_args[1]="-1200";cmd_args[2]="-1200";cmd_argc=3;
        chim_tp_command();
        landed[pool]=fabs(player->v.origin[0]+300)<.01 && fabs(player->v.origin[1]+300)<.01;
        ChimGraft_Slots(&s0,&s1,&outgrown,&failures);
        printf("jump pool %d KiB: landed %d, slots %d/%d KiB, failed rebuilds %lu%c",pool?512:0,landed[pool],
            s0/1024,s1/1024,failures,10);
        svs.clients=NULL;svs.maxclients=0;cmd_argc=0;
        end_map();
    }
    set_cvar("chim_pool_kib",384);
    assert(landed[0] && landed[1]);
    printf("jump ok%c",10);
}

/* CHIM-ZONE-RING-THRASH-33: the frame-world slots reserved at map start are
 * used by every rebuild while they fit, fall back to per-rebuild allocation
 * when outgrown, and leave nothing behind at the map's end; the ring
 * overrides change how many chunks are active and loaded. */
static void slots(void){
    int s0,s1,i,ticks,act[3],loaded[3];unsigned long outgrown,failures;chim_zone_stats_t s;
    /* The full rebuild (chim_graft_mode 0, the first method) and its slots. */
    for(i=0;i<2;i++){
        reset_engine();Chim_Init();
        set_cvar("chim_graft_mode",0);
        set_cvar("chim_pool_kib",i?1:256);
        begin_map(frame_map);assert(Chim_Active());
        for(ticks=0;ticks<4;ticks++){
            float x=ticks&1?-180:180,y=ticks&2?-180:180;int k;
            for(k=0;k<60;k++)frame_at(x,y,40);
            check_once();check_world();
        }
        ChimGraft_Slots(&s0,&s1,&outgrown,&failures);
        printf("slots %d: %d %d KiB, outgrown %lu, failed %lu, active %d%c",i,s0/1024,s1/1024,outgrown,failures,active_count(),10);
        if(!i)assert(s0==256*1024 && s1==256*1024 && !outgrown);
        else assert(outgrown>=1 && (!s0 || !s1));
        assert(!failures);
        for(ticks=0;ticks<chim_frame.count;ticks++)
            if(chim_frame.entries[ticks].state==CHIM_STATE_ACTIVE)assert(chim_frame.entries[ticks].grafted);
        end_map();
        ChimZone_Stats(&s);assert(!s.kind_blocks[CHIM_KIND_WORLD]);
        set_cvar("chim_pool_kib",0);
    }
    set_cvar("chim_pool_kib",384);
    /* The incremental pool (chim_graft_mode 1): one block, twice
     * chim_pool_kib, reserved at map start and used in place; a reserve too
     * small for a layout falls back to blocks sized for the ring. */
    for(i=0;i<2;i++){
        reset_engine();Chim_Init();
        set_cvar("chim_graft_mode",1);
        set_cvar("chim_pool_kib",i?1:256);
        begin_map(frame_map);assert(Chim_Active() && ChimGraft_Incremental());
        for(ticks=0;ticks<4;ticks++){
            float x=ticks&1?-180:180,y=ticks&2?-180:180;int k;
            for(k=0;k<60;k++)frame_at(x,y,40);
            check_once();check_world();
        }
        ChimGraft_Slots(&s0,&s1,&outgrown,&failures);
        printf("pool %d: %d %d KiB, outgrown %lu, failed %lu, active %d%c",i,s0/1024,s1/1024,outgrown,failures,active_count(),10);
        if(!i)assert(s0==512*1024 && !s1 && !outgrown);
        else assert(!s0 && !s1);
        assert(!failures);
        for(ticks=0;ticks<chim_frame.count;ticks++)
            if(chim_frame.entries[ticks].state==CHIM_STATE_ACTIVE)assert(chim_frame.entries[ticks].grafted);
        end_map();
        ChimZone_Stats(&s);assert(!s.kind_blocks[CHIM_KIND_WORLD] && !s.locked_bytes);
    }
    set_cvar("chim_pool_kib",384);
    /* Ring overrides: the world's settings, a shorter draw distance, no prefetch. */
    for(i=0;i<3;i++){
        reset_engine();Chim_Init();
        set_cvar("chim_draw_distance",i==1?120:0);set_cvar("chim_prefetch",i==2?0:-1);
        begin_map(frame_map);
        for(ticks=0;ticks<60;ticks++)frame_at(0,0,40);
        act[i]=active_count();loaded[i]=chim_frame.loaded;
        end_map();
    }
    set_cvar("chim_draw_distance",0);set_cvar("chim_prefetch",-1);
    printf("ring: active %d/%d/%d loaded %d/%d/%d%c",act[0],act[1],act[2],loaded[0],loaded[1],loaded[2],10);
    assert(act[1]<act[0] && act[2]==act[0] && loaded[2]<=loaded[0]);
    printf("slots ok%c",10);
}

/* Format 0.4 seams, on a world written by the CHIM builder (seam.txt: x y
 * stand, the lowest origin whose standing box clears the highest ground
 * under it, the neighbour chunk's included): a box dropped there stands on
 * that ground. visits.txt: points for the clipnodes visited per hull 1
 * point test in the frame world (the builder counts its chunk alone). */
static int hull_visits(hull_t *h,int num,const vec3_t p){
    int n=0;
    while(num>=0){
        dclipnode_t *node=h->clipnodes+num;mplane_t *plane=h->planes+node->planenum;
        float d=plane->type<3?p[plane->type]-plane->dist:DotProduct(plane->normal,p)-plane->dist;
        n++;num=d<0?node->children[1]:node->children[0];
    }
    return n;
}
static int compare_ints(const void *a,const void *b){return *(const int *)a-*(const int *)b;}
static void seam(void){
    FILE *f;float x,y,z,over=0;int n=0,bad=0,high=0,i,count=0,*v=malloc(sizeof(int)*20000);double sum=0;
    vec3_t mins={-7.32f,-7.12f,-16.625f},maxs={7.32f,7.12f,16.625f},start,end,at;trace_t tr;
    reset_engine();Chim_Init();
    set_cvar("chim_zone_kib",8192);set_cvar("chim_reserve_kib",0);
    begin_map(frame_map);assert(Chim_Active());
    VectorSet(world.mins,-512,-512,-1024);VectorSet(world.maxs,512,512,2048);
    f=fopen("seam.txt","r");assert(f && v);
    while(fscanf(f,"%f %f %f",&x,&y,&z)==3){
        VectorSet(at,x,y,z);aw_chim_spawn(at);
        assert(chim_frame.entries[entry_at(x,y)].grafted);
        VectorSet(start,x,y,z+12);VectorSet(end,x,y,z-12);
        tr=SV_ClipMoveToEntity(&edicts[0],start,mins,maxs,end);
        /* On the highest ground under the box: never below it (the seam,
         * format 0.4) and never above it (the terrain hull's edge bevels,
         * CHIM-TERRAIN-HULL-BEVELS-33). */
        if(!tr.startsolid && !tr.allsolid && tr.endpos[2]-z>0.25f){
            high++;if(tr.endpos[2]-z>over)over=tr.endpos[2]-z;
        }
        if(tr.startsolid || tr.allsolid || tr.endpos[2]<z-0.25f || tr.endpos[2]>z+0.25f){
            if(bad<5)printf("seam: %.2f %.2f stands at %.3f, expected %.3f (start solid %d)\n",x,y,tr.endpos[2],z,tr.startsolid);
            bad++;
        }
        n++;
    }
    fclose(f);
    f=fopen("visits.txt","r");assert(f);
    while(count<20000 && fscanf(f,"%f %f %f",&x,&y,&z)==3){
        VectorSet(at,x,y,z);
        if(!chim_frame.entries[entry_at(x,y)].grafted)aw_chim_spawn(at);
        v[count]=hull_visits(&world.hulls[1],world.hulls[1].firstclipnode,at);sum+=v[count++];
    }
    fclose(f);
    qsort(v,count,sizeof(int),compare_ints);
    printf("seam: %d samples, %d off the ground, %d above it (at most %.2f); hull 1 visits per point test: mean %.1f, p95 %d, max %d over %d points\n",
        n,bad,high,over,sum/count,v[count*95/100],v[count-1],count);
    assert(n>0 && !bad && over<=0.25f);
    for(i=0;i<chim_frame.count;i++)if(chim_frame.entries[i].grafted)assert(chim_frame.entries[i].state==CHIM_STATE_ACTIVE);
    free(v);
    end_map();
    printf("seam ok\n");
}


/* ---------------------------------------------------------------- CHIM-REBUILD-COST-33 */

/* A frame-world fingerprint that does not depend on where a chunk sits in
 * the pool: each leaf named by its chunk and its leaf in the chunk's own
 * template (grid leaves by their bounds); free ranges are skipped. */
static unsigned long long fp_mix(unsigned long long h,unsigned long long v){return (h^v)*1099511628211ULL+(v>>7);}
static unsigned long long leaf_key(mleaf_t *l){
    int e,loc,idx=(int)(l-world.leafs);
    if(idx<=0 || !l->parent)return 0;
    ChimGraft_LeafOwner(idx,&e,&loc);
    if(e>=0)return ((unsigned long long)(e+1)<<20)|(unsigned)loc;
    return 0xfff00000ULL^((unsigned long long)(unsigned short)l->minmaxs[0]<<32)^((unsigned long long)(unsigned short)l->minmaxs[1]<<16)^
        (unsigned long long)(unsigned short)l->minmaxs[3]^((unsigned long long)(unsigned short)l->minmaxs[4]<<48);
}
static unsigned long long efrag_sum(const entity_t *ent){
    const efrag_t *ef;unsigned long long sum=0;
    for(ef=ent->efrag;ef;ef=ef->entnext)sum+=leaf_key(ef->leaf)*2654435761ULL+1;
    return sum;
}
static unsigned long long fingerprint(float span,float step){
    unsigned long long h=1469598103934665603ULL;int i,j,k;float x,y;
    vec3_t mins={-7.32f,-7.12f,-16.625f},maxs={7.32f,7.12f,16.625f},a,b;trace_t t;
    for(i=0;i<chim_frame.count;i++)h=fp_mix(h,(unsigned long long)chim_frame.entries[i].grafted*(i+1));
    for(x=-span;x<=span;x+=step)for(y=-span;y<=span;y+=step){
        vec3_t pt;mleaf_t *l;byte *vis;unsigned long long sum=0;
        pt[0]=x+.37f;pt[1]=y+.61f;pt[2]=5.3f;
        l=Mod_PointInLeaf(pt,&world);
        h=fp_mix(h,leaf_key(l));h=fp_mix(h,(unsigned long long)(l->contents+16));
        vis=Mod_LeafPVS(l,&world);
        for(i=0;i<world.numleafs;i++)if(vis[i>>3]&(1<<(i&7)))sum+=leaf_key(&world.leafs[i+1])*0x100000001b3ULL;
        h=fp_mix(h,sum);
        VectorSet(a,pt[0],pt[1],200);VectorSet(b,pt[0],pt[1],-100);
        t=world_trace(a,mins,maxs,b);h=fp_mix(h,(unsigned long long)(long long)(t.endpos[2]*64));
    }
    for(i=0;i<chim_frame.count;i++){
        chim_chunk_t *c=chim_frame.entries[i].chunk.data;
        if(chim_frame.entries[i].state!=CHIM_STATE_ACTIVE)continue;
        for(j=0;j<c->records;j++)if(c->places[j].linked)h=fp_mix(h,c->places[j].pid*1000003ULL+efrag_sum(&c->places[j].ent));
    }
    for(i=0;i<cl.num_statics;i++)h=fp_mix(h,efrag_sum(&cl_static_entities[i]));
    for(i=2;i<5;i++){
        unsigned long long sum=0;
        for(k=0;k<edicts[i].num_leafs;k++)sum+=leaf_key(&world.leafs[edicts[i].leafnums[k]+1])*31+7;
        h=fp_mix(h,sum);
    }
    return h;
}

/* Both methods give the same frame world, frame by frame: the incremental
 * pool (chim_graft_mode 1, no budget) against the full rebuild (0) on the
 * same walk, by leaves, contents, vis rows, ground, placement and static
 * efrags and edict leaves; and the incremental one copies only the chunks
 * that join. */
#define WALK_STEPS 400
static int walk_point(int big,int t,float *x,float *y){
    /* Walk 16 units a frame (8 in the small frame) around a loop, a jump in
     * the middle. */
    float r=big?1000:300,sp=big?16:8,len=8*r,d=t*sp;int leg;
    if(t==WALK_STEPS/2){*x=-r;*y=r;return 1;}
    if(t>WALK_STEPS/2)d=(t-WALK_STEPS/2)*sp+4*r;
    while(d>=len)d-=len;
    leg=(int)(d/(2*r));d-=leg*2*r;
    switch(leg){case 0:*x=-r+d;*y=-r;break;case 1:*x=r;*y=-r+d;break;case 2:*x=r-d;*y=r;break;default:*x=-r;*y=r-d;}
    return 0;
}
static void graftmodes(void){
    static unsigned long long fp[2][WALK_STEPS];
    int big=getenv("CHIM_BIG")!=NULL,mode,t;unsigned long copied[2],adds,removes,repacks,relinked,urgent;
    float x,y,span=big?1500:380,step=big?60:40;
    for(mode=0;mode<2;mode++){
        reset_engine();Chim_Init();
        set_cvar("chim_graft_mode",mode);set_cvar("chim_graft_kib",0);
        if(big){set_cvar("chim_zone_kib",8192);set_cvar("chim_reserve_kib",0);}
        begin_map(frame_map);assert(Chim_Active() && ChimGraft_Incremental()==mode);
        if(big){VectorSet(world.mins,-1536,-1536,-1024);VectorSet(world.maxs,1536,1536,2048);}
        walk_point(big,0,&x,&y);frame_at(x,y,40);
        cl_static_entities[0].model=placement_any();VectorSet(cl_static_entities[0].origin,x+40,y+20,0);
        cl.num_statics=1;R_AddEfrags(&cl_static_entities[0]);
        for(t=0;t<WALK_STEPS;t++){
            walk_point(big,t,&x,&y);
            VectorSet(edicts[2].v.origin,x+30,y,40);SV_LinkEdict(&edicts[2],false);
            frame_at(x,y,40);
            if(!(t%(big?20:4))){check_world();check_once();}
            fp[mode][t]=fingerprint(span,step);
        }
        ChimGraft_Totals(&adds,&removes,&repacks,&copied[mode],&relinked,&urgent);
        printf("graftmodes %d: %lu chunk copies, %lu joined, %lu left, %lu repacks, %lu relinked%c",mode,copied[mode],adds,removes,repacks,relinked,10);
        /* The first layout when the ring arrives is the one repack. */
        if(mode)assert(copied[1]==adds && repacks==1);
        end_map();
    }
    for(t=0;t<WALK_STEPS;t++)if(fp[0][t]!=fp[1][t]){printf("graftmodes: frame %d differs%c",t,10);assert(!"frame worlds differ");}
    assert(copied[1]*3<copied[0]);
    set_cvar("chim_graft_mode",1);set_cvar("chim_graft_kib",16);
    printf("graftmodes ok%c",10);
}

/* The per-frame budget (CHIM-REBUILD-COST-33, "don't block the traffic"):
 * walking, chunks join a few bytes a frame (at least one chunk, more only
 * within the collision margin), the ground under and around the player is
 * always there (safety margin > the collision margin), and nothing is
 * rebuilt whole after the first layout. */
static void budget(void){
    int big=getenv("CHIM_BIG")!=NULL,t,i,margin,ahead,worst_margin=1<<30,most=0,frames_pending=0;
    unsigned long adds,removes,repacks,copied,relinked,urgent,last_adds=0,last_urgent=0,urgent_loads,repacks0;
    float x,y,kib=0.25f;
    reset_engine();Chim_Init();
    set_cvar("chim_graft_kib",kib);
    if(big){set_cvar("chim_zone_kib",8192);set_cvar("chim_reserve_kib",0);}
    begin_map(frame_map);assert(ChimGraft_Incremental());
    if(big){VectorSet(world.mins,-1536,-1536,-1024);VectorSet(world.maxs,1536,1536,2048);}
    walk_point(big,0,&x,&y);frame_at(x,y,40);
    ChimGraft_Totals(&adds,&removes,&repacks0,&copied,&relinked,&urgent);
    last_adds=adds;last_urgent=urgent;
    ChimChunks_Streaming(&margin,&urgent_loads,&ahead);
    for(t=1;t<WALK_STEPS/2;t++){
        walk_point(big,t,&x,&y);frame_at(x,y,40);
        ChimGraft_Totals(&adds,&removes,&repacks,&copied,&relinked,&urgent);
        ChimChunks_Streaming(&margin,&urgent_loads,&ahead);
        if(margin>=0 && margin<worst_margin)worst_margin=margin;
        /* One chunk a frame at this budget, unless within the collision margin. */
        if((int)(adds-last_adds)>most)most=(int)(adds-last_adds);
        assert(adds-last_adds<=1+(urgent-last_urgent));
        last_adds=adds;last_urgent=urgent;
        for(i=0;i<chim_frame.count;i++)
            if(chim_frame.entries[i].state==CHIM_STATE_ACTIVE && !chim_frame.entries[i].grafted){frames_pending++;break;}
        assert(chim_frame.entries[entry_at(x,y)].grafted);
        if(!(t%10)){check_world();check_once();}
    }
    printf("budget: %lu joined, %lu left, %lu repacks after the first layout, most %d joined in a frame, %d frames with chunks waiting, nearest chunk without ground %d units (collision margin %d), %lu urgent joins, %lu urgent loads%c",
        adds,removes,repacks-repacks0,most,frames_pending,worst_margin,(int)chim_frame.settings.collision_margin,urgent,urgent_loads,10);
    assert(repacks==repacks0 && copied==adds && (frames_pending>0 || !big));
    assert(worst_margin>(int)chim_frame.settings.collision_margin && !urgent);
    for(t=0;t<200;t++)frame_at(x,y,40);
    for(i=0;i<chim_frame.count;i++)if(chim_frame.entries[i].state==CHIM_STATE_ACTIVE)assert(chim_frame.entries[i].grafted);
    check_world();check_once();
    end_map();
    set_cvar("chim_graft_kib",16);
    printf("budget ok%c",10);
}

/* CHIM-GRAFT-REPACK-EMPTY-33 (owner, v0.0.33 final3, Seyda Neen: "frame world
 * repacked (marks full): 0 chunks", the world gone and the player falling):
 * a ring that outgrows the frame world's block in a zone with no free run
 * for a larger one. The repack keeps the old block and the nearest chunks
 * that fit it: the ground under the player stays, never 0 chunks.
 * CHIM_FIRST_METHOD runs chim_graft_trim 0 and expects the empty world. */
static void trim(void){
    static chim_user_t hog[1024];
    int n=0,i,k,t,first=getenv("CHIM_FIRST_METHOD")!=NULL,holes=0,steps=0,empty=0,least=1<<30,trimmed;
    int pool=atoi(getenv("CHIM_POOL_KIB")?getenv("CHIM_POOL_KIB"):"16"),piece=24*1024;
    unsigned long trims;chim_zone_stats_t s;float x,y;
    reset_engine();Chim_Init();
    set_cvar("chim_zone_kib",8192);set_cvar("chim_reserve_kib",0);set_cvar("chim_pool_kib",pool);
    if(first)set_cvar("chim_graft_trim",0);
    begin_map(frame_map);assert(ChimGraft_Incremental());
    VectorSet(world.mins,-1536,-1536,-1024);VectorSet(world.maxs,1536,1536,2048);
    /* At the frame's corner the ring is a quarter of the centre's: it fits. */
    for(t=0;t<60;t++)frame_at(-1500,-1500,40);
    check_once();
    {int r,g,l,sf,b,s0,s1;unsigned long og,fl;ChimGraft_Stats(&r,&g,&l,&sf,&b);ChimGraft_Slots(&s0,&s1,&og,&fl);
     printf("trim corner: %d chunks grafted, %d active, %d bytes, slot %d%c",g,active_count(),b,s0,10);
     assert(g==active_count() && g>0);}
    /* Fragment the zone: every other piece stays taken, so no free run can
     * hold a larger block while chunks and models still find room. */
    for(ChimZone_Stats(&s);s.largest_free>piece && n<1024;ChimZone_Stats(&s),n++){
        assert(ChimZone_Alloc(&hog[n],piece,CHIM_KIND_BUFFER,99));ChimZone_Lock(hog[n].data);}
    for(i=0;i<n;i+=2){ChimZone_Unlock(hog[i].data);ChimZone_Free(&hog[i]);}
    ChimZone_Stats(&s);printf("trim zone: largest free %ld bytes, %ld free%c",(long)s.largest_free,(long)s.free_bytes,10);
    /* Walk to the centre: the ring grows past the block. */
    for(k=0;k<=30;k++){
        x=y=-1500+k*50.0f;
        for(t=0;t<8;t++){
            int r,g,l,sf,b;frame_at(x,y,40);ChimGraft_Stats(&r,&g,&l,&sf,&b);
            if(g<least)least=g;
            if(!g)empty++;
            if(t>=2){holes+=ground_holes(x,y)>0;steps++;}
        }
    }
    ChimGraft_Trims(&trims,&trimmed);
    printf("trim %s: %lu trimmed repacks, fewest chunks %d, %d ticks with no chunk, %d of %d steps with a hole under the player%c",
        first?"first method":"default",trims,least,empty,holes,steps,10);
    if(first)assert(empty>0 && !trims);
    else{
        assert(trims>0 && least>0 && !empty && !holes);
        {vec3_t a,b,mins,maxs;trace_t tr;VectorSet(a,x,y,40);VectorSet(b,x,y,-400);VectorSet(mins,-16,-16,-24);VectorSet(maxs,16,16,32);
         tr=world_trace(a,mins,maxs,b);assert(tr.fraction<1 && tr.plane.normal[2]>0.7f);}
        /* With room again the whole ring is laid out. */
        for(i=1;i<n;i+=2){ChimZone_Unlock(hog[i].data);ChimZone_Free(&hog[i]);}
        n=0;
        ChimZone_Stats(&s);printf("trim freed: largest free %ld%c",(long)s.largest_free,10);
        for(t=0;t<60;t++)frame_at(x,y,40);
        ChimGraft_Trims(&trims,&trimmed);assert(!trimmed);
        for(i=0;i<chim_frame.count;i++)if(chim_frame.entries[i].state==CHIM_STATE_ACTIVE)assert(chim_frame.entries[i].grafted);
        check_world();check_once();
    }
    for(i=1;i<n;i+=2){ChimZone_Unlock(hog[i].data);ChimZone_Free(&hog[i]);}
    end_map();
    set_cvar("chim_graft_trim",1);set_cvar("chim_pool_kib",384);
    printf("trim ok%c",10);
}

/* Prefetch ahead: walking east, chunks east of the load radius are read
 * ahead (towards the point the prefetch margin ahead), none to the west;
 * with chim_lookahead 0 none are. The ring's radii follow the view
 * distance, limited by the world's visibility data and said by "chim". */
static int loaded_beyond(float x,float y,float load,int east){
    int i,n=0;
    for(i=0;i<chim_frame.count;i++){
        chim_entry_t *e=&chim_frame.entries[i];
        float cx=(e->low[0]+e->high[0])*.5f;
        if(e->state==CHIM_STATE_ABSENT || e->distance<=load*load)continue;
        if(east?cx>x:cx<x)n++;
    }
    (void)y;return n;
}
extern int (*aw_chim_view_reach)(void);
static void ahead(void){
    int look,t,east[2],west[2];float x=-150,load;
    for(look=0;look<2;look++){
        reset_engine();Chim_Init();
        set_cvar("chim_lookahead",look?-1:0);
        begin_map(frame_map);
        for(t=0;t<60;t++)frame_at(-150,0,40);
        for(t=0;t<30;t++){x=-150+t*4;frame_at(x,0,40);}
        load=ChimChunks_LoadRadius();
        east[look]=loaded_beyond(x,0,load,1);west[look]=loaded_beyond(x,0,load,0);
        printf("ahead %d: %d chunks read ahead east, %d west%c",look,east[look],west[look],10);
        check_once();check_world();
        end_map();
    }
    set_cvar("chim_lookahead",-1);
    assert(east[1]>0 && east[0]==0 && west[1]==west[0]);
    /* The ring follows the view distance; on a CHIM map the world's data
     * (draw distance + hysteresis) limits it, and "chim" says so. */
    reset_engine();Chim_Init();begin_map(frame_map);frame_at(0,0,40);
    assert(aw_chim_view_reach && aw_chim_view_reach()==(int)(chim_frame.settings.draw_distance+chim_frame.settings.hysteresis));
    aw_drawdistance.value=120;
    assert(fabs(ChimChunks_ActiveRadius()-(120+chim_frame.settings.hysteresis))<.01);
    aw_drawdistance.value=5000;
    assert(fabs(Chim_ViewDistance()-aw_chim_view_reach())<.01);
    console_used=0;console[0]=0;console_capture=1;chim_command();console_capture=0;
    assert(strstr(console,"ring: view") && strstr(console,"visibility data reaches") && strstr(console,"chim_graft_kib"));
    aw_drawdistance.value=0;
    end_map();
    printf("ahead ok%c",10);
}

/* ---------------------------------------------------------------- world format 0.5 */

/* The index's version in place (header bytes 8..11, big-endian major and minor). */
static void set_version(int major,int minor){
    FILE *f=fopen("chim/world.cwi","r+b");byte b[4];
    assert(f);b[0]=(byte)(major>>8);b[1]=(byte)major;b[2]=(byte)(minor>>8);b[3]=(byte)minor;
    fseek(f,8,SEEK_SET);assert(fwrite(b,1,4,f)==4);fclose(f);
}
/* 0.4 to 0.6 are read; 0.7 and 1.5 are refused whole, with a console line. */
static void formats(void){
    static const int version[5][2]={{0,4},{0,5},{0,6},{0,7},{1,5}};int k;
    for(k=0;k<5;k++){
        set_version(version[k][0],version[k][1]);
        reset_engine();Chim_Init();
        console_used=0;console[0]=0;console_capture=1;
        begin_map(frame_map);
        console_capture=0;
        if(k<3){
            assert(Chim_Active() && chim_world.minor==version[k][1]);
            frame_at(64,64,40);assert(active_count()>0);check_once();check_world();
        }else{
            char said[96];
            sprintf(said,"world format %d.%d; this engine reads 0.4 to 0.6",version[k][0],version[k][1]);
            assert(!Chim_Active() && strstr(console,said));
        }
        end_map();
    }
    set_version(0,5);
    printf("formats ok%c",10);
}

/* Placements flagged story hidden (0.5; aw_opening.c's "aw_story_hidden"
 * rule) are not drawn and not solid while the story hides them. */
static int story_flag;
/* The frame's far terrain (CHIM-FAR-TERRAIN-33): maps/chimtest.far beside the
 * frame map (written by the Python test) loads into the low Hunk at map start,
 * reaches the fog hook with the frame-local origin, and goes with the map. */
static void far(void){
    int before,i;const aw_horizon_grid_t *l;
    for(i=0;i<2;i++){
        reset_engine();Chim_Init();
        assert(aw_chim_far_draw);
        before=low;begin_map(frame_map);assert(Chim_Active());
        if(!i){
            l=ChimFar_Layer();assert(ChimFar_Loaded() && l);
            assert(l->nx==9 && l->ny==7 && l->block==4 && l->heights[3*9+5]==35);
            assert(fabs(l->step-256)<.001 && fabs(l->x0-(-1024))<.01 && fabs(l->y0-(-768))<.01);
            assert(low-before>=2*9*7);     /* the heights are in the low Hunk */
            far_draws=0;frame_at(64,64,40);aw_chim_far_draw(15,540);assert(far_draws==1 && far_drawn==l);
            set_cvar("chim_far",0);aw_chim_far_draw(15,540);assert(far_draws==1);set_cvar("chim_far",1);
            console_used=0;console[0]=0;console_capture=1;chim_command();console_capture=0;assert(strstr(console,"far terrain (chim_far 1, reach 896): maps/chimtest.far, 9 x 7"));
            remove("maps/chimtest.far");
        }else{
            assert(!ChimFar_Loaded());far_draws=0;aw_chim_far_draw(15,540);assert(!far_draws);
        }
        end_map();assert(!ChimFar_Loaded());
    }
    puts("far: the frame map's far terrain loads into the low Hunk, reaches the fog hook, goes with the map; none: nothing drawn");
}
static int story_rule(void){return story_flag;}
static void story(void){
    vec3_t mins={-7.32f,-7.12f,-16.625f},maxs={7.32f,7.12f,16.625f},a,b;trace_t t;int k;
    for(k=0;k<2;k++){
        reset_engine();Chim_Init();
        chim_story_hidden=story_rule;story_flag=k;
        begin_map(frame_map);frame_at(64,64,40);check_once();
        if(k)assert(!placement(0) && placement(4));
        else assert(placement(0) && placement(0)->leaves==1);
        VectorSet(a,32,32,200);VectorSet(b,32,32,40);t=chim_trace(a,mins,maxs,b);
        assert(k?t.fraction==1:t.fraction<1);
        end_map();
    }
    chim_story_hidden=NULL;
    printf("story ok%c",10);
}

/* "_chim_edge" "closed" (M3): at the frame's bounds the player hears the
 * area beyond is unavailable, at most every 3 s; inside, in noclip, or with
 * an open edge, nothing is said. */
static const char *closed_map="{\n\"classname\" \"worldspawn\"\n\"_chim_frame\" \"0 0\"\n\"_chim_edge\" \"closed\"\n}\n";
static void edge(void){
    static client_t client;edict_t *player=&edicts[1];vec3_t at;int k;
    for(k=0;k<2;k++){
        reset_engine();Chim_Init();
        begin_map(k?frame_map:closed_map);
        memset(player,0,sizeof(*player));player->v.movetype=MOVETYPE_WALK;
        client.edict=player;svs.clients=&client;svs.maxclients=1;
        frame_at(0,0,40);subtitles=0;subtitle[0]=0;
        VectorSet(at,0,0,40);aw_chim_player(at);assert(!subtitles);
        VectorSet(at,chim_frame.frame.low[0]+8,0,40);
        assert(Chim_EdgeReached(at)==!k);
        aw_chim_player(at);
        if(!k){
            assert(subtitles==1 && !strcmp(subtitle,"Area unavailable"));
            aw_chim_player(at);assert(subtitles==1);		/* not again within 3 s */
            player->v.movetype=MOVETYPE_NOCLIP;fake_clock+=10;aw_chim_player(at);assert(subtitles==1);
            player->v.movetype=MOVETYPE_WALK;aw_chim_player(at);assert(subtitles==2);
            console_used=0;console[0]=0;console_capture=1;chim_command();console_capture=0;
            assert(strstr(console,"frame edge: closed"));
        }else assert(!subtitles);
        svs.clients=NULL;svs.maxclients=0;
        end_map();
    }
    printf("edge ok%c",10);
}

/* The whole-map Hunk rule (CHIM-ZONE-RESERVE-EARLY-33): the zone leaves room
 * for what the frame map says it loads after the zone; after loading, a map
 * that used more is said, and its next load leaves room for what it used. */
static const char *rest_map="{\n\"classname\" \"worldspawn\"\n\"_chim_frame\" \"0 0\"\n\"_chim_hunk_rest\" \"3145728\"\n}\n";
static int zone_of(void){int stated,used,measured;return Chim_HunkRest(&stated,&used,&measured);}
static void rest(void){
    int plain,stated_zone,again,stated,used,measured;vec3_t at;
    /* A zone of 15 MiB asked: what the 16 MiB Hunk has, less the reserve. */
    reset_engine();Chim_Init();set_cvar("chim_zone_kib",15*1024);
    begin_map(frame_map);plain=zone_of();end_map();
    /* Stated: 3 MiB loaded after the zone: the zone is 3 MiB smaller. */
    reset_engine();Chim_Init();
    console_used=0;console[0]=0;console_capture=1;begin_map(rest_map);console_capture=0;
    stated_zone=zone_of();
    assert(plain-stated_zone==3145728 && strstr(console,"stated by the frame map"));
    /* The map loads 4 MiB instead (more than stated): said after loading,
     * and its next load in the session leaves room for 4 MiB. */
    Hunk_AllocName(4*1024*1024,"actors");
    console_used=0;console[0]=0;console_capture=1;
    VectorSet(at,64,64,40);aw_chim_spawn(at);console_capture=0;
    assert(strstr(console,"under chim_reserve_kib") && strstr(console,"used on its next load"));
    Chim_HunkRest(&stated,&used,&measured);
    assert(stated==3145728 && measured>=4*1024*1024);
    console_used=0;console[0]=0;console_capture=1;chim_command();console_capture=0;
    assert(strstr(console,"Hunk: zone") && strstr(console,"stated 3072 KiB"));
    end_map();
    reset_engine();Chim_Init();
    console_used=0;console[0]=0;console_capture=1;begin_map(rest_map);console_capture=0;
    again=zone_of();
    assert(strstr(console,"measured on its last load") && stated_zone-again>=1024*1024-16);
    /* Now the gap holds after loading the same: nothing is said. */
    Hunk_AllocName(4*1024*1024,"actors");
    console_used=0;console[0]=0;console_capture=1;aw_chim_spawn(at);console_capture=0;
    assert(!strstr(console,"under chim_reserve_kib"));
    assert(host_parms.memsize-(low+high)>=(int)(2048*1024));
    end_map();
    /* A lighter load (3.5 MiB) does not let the zone grow back: the most the
     * map has used is kept, so the next 4 MiB load still keeps the gap. */
    reset_engine();Chim_Init();begin_map(rest_map);
    assert(zone_of()==again);
    Hunk_AllocName(7*512*1024,"actors");aw_chim_spawn(at);end_map();
    reset_engine();Chim_Init();begin_map(rest_map);
    assert(zone_of()==again);
    Hunk_AllocName(4*1024*1024,"actors");
    console_used=0;console[0]=0;console_capture=1;aw_chim_spawn(at);console_capture=0;
    assert(!strstr(console,"under chim_reserve_kib"));
    end_map();
    /* A frame map that states no figure keeps its full zone by default
     * (chim_rest_measured 1): the gap is said, not learnt; 2 learns it. */
    {
        int full,learnt;
        reset_engine();Chim_Init();set_cvar("chim_zone_kib",10*1024);
        begin_map(frame_map);full=zone_of();
        Hunk_AllocName(4*1024*1024,"actors");
        console_used=0;console[0]=0;console_capture=1;aw_chim_spawn(at);console_capture=0;
        assert(strstr(console,"under chim_reserve_kib") && strstr(console,"states no figure"));
        end_map();
        reset_engine();Chim_Init();begin_map(frame_map);assert(zone_of()==full);end_map();
        set_cvar("chim_rest_measured",2);
        reset_engine();Chim_Init();begin_map(frame_map);learnt=zone_of();
        {int st,us,me;Chim_HunkRest(&st,&us,&me);assert(learnt<full && st==0 && us==me && me>=4*1024*1024);}
        end_map();
        set_cvar("chim_rest_measured",1);
    }
    set_cvar("chim_zone_kib",6864);
    printf("rest: zone %d, stated %d, after the measured load %d%c",plain,stated_zone,again,10);
    printf("rest ok%c",10);
}

/* Streamed statics (chim_statics.c): a frame map's tagged aw_static and
 * aw_flora are taken by their chunk instead of spawned, their sprite decoded
 * once into the zone, placed and linked while the chunk is active. */
static void write_sprite(const char *path,int w,int h){
    FILE *f;int head[9],frame[5],i;float radius=12,beam=0;
    mkdir("progs",0755);f=fopen(path,"wb");assert(f);
    memcpy(&head[0],"IDSP",4);head[1]=SPRITE_VERSION;head[2]=SPR_VP_PARALLEL_UPRIGHT;memcpy(&head[3],&radius,4);
    head[4]=w;head[5]=h;head[6]=1;memcpy(&head[7],&beam,4);head[8]=ST_SYNC;
    fwrite(head,4,9,f);
    frame[0]=SPR_SINGLE;frame[1]=-w/2;frame[2]=h;frame[3]=w;frame[4]=h;fwrite(frame,4,5,f);
    for(i=0;i<w*h;i++)fputc(i&255,f);
    fclose(f);
}
static char statics_map[2048];
static int capture(const char *text){
    char buffer[512],*data=buffer,*before;int taken;
    strncpy(buffer,text,sizeof(buffer)-1);buffer[sizeof(buffer)-1]=0;
    data=COM_Parse(data);assert(com_token[0]=='{');
    before=data;taken=aw_chim_entity(&data);
    if(!taken)assert(data==before);            /* left for ED_ParseEdict, unmoved */
    else assert(!COM_Parse(data));             /* past its closing brace */
    return taken;
}
static void statics(void){
    char text[512];int near,far,sc,sl,se,sm,sb,i,k,t;vec3_t at;
    entity_t *flora_near,*flora_far,*lamp;void *block;
    write_sprite("progs/f.spr",8,16);
    reset_engine();Chim_Init();
    assert(aw_chim_entity);
    sprintf(statics_map,"{\n\"classname\" \"worldspawn\"\n\"_chim_frame\" \"0 0\"\n\"_chim_streamed_statics\" \"5\"\n\"_chim_hunk_rest\" \"1000\"\n}\n");
    begin_map(statics_map);
    near=entry_at(40,40);far=entry_at(-330,-330);assert(near>=0 && far>=0 && near!=far);
    /* Two flora sharing one sprite in two chunks, a lamp (aw_static: scale 1
     * whatever aw_scale says), a static whose model is missing. */
    sprintf(text,"{\n\"classname\" \"aw_flora\"\n\"model\" \"progs/f.spr\"\n\"origin\" \"40 40 0\"\n\"aw_scale\" \"2\"\n\"_chim_chunk\" \"%d\"\n\"_chim_box\" \"16 16 -24 64 64 24\"\n}\n",near);
    assert(capture(text));
    sprintf(text,"{\n\"classname\" \"aw_flora\"\n\"model\" \"progs/f.spr\"\n\"origin\" \"-330 -330 0\"\n\"angles\" \"0 30 0\"\n\"aw_scale\" \"1\"\n\"_chim_chunk\" \"%d\"\n\"_chim_box\" \"-342 -342 -12 -318 -318 12\"\n}\n",far);
    assert(capture(text));
    sprintf(text,"{\n\"classname\" \"aw_static\"\n\"model\" \"progs/f.spr\"\n\"origin\" \"100 40 0\"\n\"aw_scale\" \"3\"\n\"frame\" \"0\"\n\"_chim_chunk\" \"%d\"\n\"_chim_box\" \"88 28 -12 112 52 12\"\n}\n",entry_at(100,40));
    assert(capture(text));
    sprintf(text,"{\n\"classname\" \"aw_static\"\n\"model\" \"progs/missing.mdl\"\n\"origin\" \"60 90 0\"\n\"_chim_chunk\" \"%d\"\n\"_chim_box\" \"56 86 -4 64 94 4\"\n}\n",entry_at(60,90));
    assert(capture(text));
    /* Untagged: spawned as usual. Tagged but not a plain makestatic class: refused. */
    assert(!capture("{\n\"classname\" \"aw_flora\"\n\"model\" \"progs/f.spr\"\n\"origin\" \"1 2 3\"\n\"aw_scale\" \"1\"\n}\n"));
    assert(!capture("{\n\"classname\" \"func_wall\"\n\"model\" \"*1\"\n\"origin\" \"0 0 0\"\n\"_chim_chunk\" \"0\"\n\"_chim_box\" \"0 0 0 1 1 1\"\n}\n"));
    assert(ChimStatics_Count()==4);
    flora_near=ChimStatics_Entity(0);flora_far=ChimStatics_Entity(1);lamp=ChimStatics_Entity(2);
    /* The ring around (64,64): the near flora and the lamp are placed and
     * linked; the far chunk is not active; one sprite block for both. */
    frame_at(64,64,40);
    for(t=0;t<20 && ChimStatics_Missing(near);t++)frame_at(64,64,40);
    check_once();
    ChimStatics_Counts(&sc,&sl,&se,&sm,&sb);
    assert(sc==4 && sl==2 && sm==2 && sb>8*16);
    assert(flora_near->model && flora_near->model->type==mod_sprite && flora_near->aw_sprite_scale==2 && flora_near->efrag);
    assert(lamp->model==flora_near->model && lamp->aw_sprite_scale==1 && lamp->efrag);
    assert(!flora_far->model && !flora_far->efrag);
    assert(!ChimStatics_Entity(3)->model);
    block=flora_near->model;assert(ChimZone_Locks(block)==1);
    {chim_zone_stats_t s;ChimZone_Stats(&s);assert(s.kind_blocks[CHIM_KIND_STATIC]==2);}   /* the list and one sprite */
    efrags_in_world(flora_near);efrags_in_world(lamp);
    assert(leaf_holds(leaf_at(40,40,10),flora_near));
    /* Walk to the far corner: the near chunks go, the far one comes; the
     * same block, still locked once (now by the far flora). */
    for(k=0;k<6;k++)for(i=0;i<8;i++)frame_at(64-k*80.0f,64-k*80.0f,40);
    for(t=0;t<40 && !flora_far->model;t++)frame_at(-330,-330,40);
    check_once();
    assert(flora_far->model==block && flora_far->efrag && flora_far->aw_sprite_scale==1);
    assert(!flora_near->model && !flora_near->efrag && !lamp->model);
    assert(ChimZone_Locks(block)==1);
    console_used=0;console[0]=0;console_capture=1;chim_command();console_capture=0;
    assert(strstr(console,"streamed statics: 4 of 5 stated") && strstr(console,"1 bad"));
    /* Out of every chunk's ring: the sprite stays as unlocked cache. */
    VectorSet(at,64,64,40);
    end_map();
    {chim_zone_stats_t s;ChimZone_Stats(&s);assert(s.kind_blocks[CHIM_KIND_STATIC]==0);}
    printf("statics: %d streamed, %d linked, %d models, %d sprite bytes%c",sc,sl,sm,sb,10);
    printf("statics ok%c",10);
    (void)at;
}


/* ---------------------------------------------------------------- v0.0.35 crash paths */

/* CHIM-PACK-LRU-STREAM-35: more than CHIM_OPEN_FILES other files opened while
 * a model streams must not close the stream's file. */
static void pin(void){
    long budget;int r,row,i,steps=0,others=0;long before;chim_pack_t *held[CHIM_OPEN_FILES];
    reset_engine();Chim_Init();
    begin_map(frame_map);assert(Chim_Active());
    assert(!ChimModels_Find(2) && (long)chim_world.model[2].bytes>chim_world.buffer_bytes);
    row=chim_world.model[2].file;
    for(i=0;i<chim_world.files;i++)if(i!=row)others++;
    assert(others>CHIM_OPEN_FILES);
    budget=1<<20;r=ChimModels_Step(2,&budget);assert(r==0 && ChimModels_Busy());
    while(r==0){
        for(i=0;i<chim_world.files;i++)if(i!=row)assert(Chim_File(i));
        budget=1<<20;r=ChimModels_Step(2,&budget);steps++;
    }
    assert(r==1 && ChimModels_Find(2) && !ChimModels_Busy() && steps>1);
    /* the model's file was never closed: no reopen */
    before=opens;assert(Chim_File(row) && opens==before);
    /* every file pinned: the next open fails instead of closing a held one */
    for(i=0;i<CHIM_OPEN_FILES;i++){held[i]=Chim_File(i);assert(held[i]);held[i]->pins++;}
    assert(!Chim_File(CHIM_OPEN_FILES));
    for(i=0;i<CHIM_OPEN_FILES;i++)held[i]->pins--;
    assert(Chim_File(CHIM_OPEN_FILES));
    end_map();
    printf("pin: %d steps, %d other files opened between them%c",steps,others,10);
    printf("pin ok%c",10);
}

/* Overwrite 4 bytes of a CHIM file at [offset] (the index's file row). */
static void poke(int row,long offset,int value){
    char path[256];FILE *f;
    snprintf(path,sizeof path,"chim/%s",chim_world.file[row].path);
    f=fopen(path,"r+b");assert(f);assert(!fseek(f,offset,SEEK_SET));
    assert(fwrite(&value,1,4,f)==4);fclose(f);
}
/* The first node's plane of model m, far outside its plane lump. */
static void damage_model(int m){
    chim_pack_t *pack=Chim_File(chim_world.model[m].file);dheader_t h;
    assert(pack && Chim_PackRead(pack,chim_world.model[m].offset,&h,sizeof h));
    poke(chim_world.model[m].file,chim_world.model[m].offset+h.lumps[LUMP_NODES].fileofs,12345678);
    Chim_FilesClose();
}

static void baddata(void){
    int t,said=0;char *at;unsigned long failed;
    reset_engine();Chim_Init();
    begin_map(frame_map);assert(Chim_Active());
    damage_model(1);        /* decoded whole (fits the loading buffer) */
    damage_model(2);        /* streamed */
    /* texture 0: its second mip level starts past its pixels */
    poke(chim_world.texture[0].file,chim_world.texture[0].offset+16+8+4,1<<20);
    console_used=0;console[0]=0;console_capture=1;
    for(t=0;t<300;t++)frame_at(t<150?64:-300,t<150?64:-300,40);
    console_capture=0;
    for(at=console;(at=strstr(at,"chunk unavailable"))!=NULL;at++)said++;
    failed=chim_world.failed_loads;
    printf("baddata: %d bad-data lines, %lu failed loads%c",said,failed,10);
    assert(said>=2 && failed>=2);
    /* bad data is not read again every frame: a failed load waits */
    assert(said<=40);
    assert(!ChimModels_Find(1) && !ChimModels_Find(2) && ChimModels_Find(0));
    /* the ground stays (partial activation) */
    assert(!ground_holes(-300,-300) && active_count()>0);
    end_map();
    printf("baddata ok%c",10);
}

/* CHIM-EFRAG-UNCAPPED-35 */
static void efragcap(void){
    int t,full,linked,efrags,one,most,waiting,k;unsigned long capped,novis;chim_place_t *near;
    reset_engine();Chim_Init();
    begin_map(frame_map);assert(Chim_Active());
    for(t=0;t<20;t++)frame_at(64,64,40);
    full=aw_efrags_used;assert(full>4);
    end_map();
    reset_engine();Chim_Init();
    begin_map(frame_map);assert(Chim_Active());
    chim_efrag_limit=full/2;
    for(t=0;t<40;t++){frame_at(64,64,40);assert(aw_efrags_used<=chim_efrag_limit);}
    ChimChunks_EfragCounts(&waiting,&capped,&novis);
    ChimChunks_Counts(&linked,&efrags,&one,&most);
    near=placement(0);
    printf("efragcap: limit %d of %d, %d in use, %d waiting, %lu waits%c",chim_efrag_limit,full,aw_efrags_used,waiting,capped,10);
    assert(waiting>0 && capped>0 && near && near->leaves>0);
    /* the nearest chunks keep their links: every linked placement is no farther than every waiting one */
    {
        float far_linked=0,near_waiting=1e30f;int i,j;
        for(i=0;i<chim_frame.count;i++){chim_entry_t *e=&chim_frame.entries[i];chim_chunk_t *c=e->chunk.data;
            if(e->state!=CHIM_STATE_ACTIVE)continue;
            for(j=0;j<c->records;j++){chim_place_t *p=&c->places[j];if(!p->linked)continue;
                if(p->leaves && e->distance>far_linked)far_linked=e->distance;
                if(!p->leaves && e->distance<near_waiting)near_waiting=e->distance;}}
        assert(far_linked<=near_waiting);
    }
    /* the limit back: after the calm period every placement links again */
    chim_efrag_limit=AW_EFRAG_LIMIT-CHIM_EFRAG_RESERVE;
    for(k=0;k<300;k++)frame_at(64,64,40);
    ChimChunks_EfragCounts(&waiting,&capped,&novis);
    assert(!waiting && aw_efrags_used==full);
    end_map();
    printf("efragcap ok%c",10);
}

/* CHIM-GRAFT-FAIL-NO-FLOOR-35: the frame world gets no room after the far
 * terrain loaded (the streamed statics' table, taken just before it, is
 * sized to leave too little): the map keeps the far terrain as its floor. */
#define CHIM_FARFAIL_MAX 2048
static char farfail_map[256];
static void farfail(void){
    float lowest,surface;vec3_t p;int stated;
    for(stated=CHIM_FARFAIL_MAX;stated>0;stated-=2){
        reset_engine();Chim_Init();
        set_cvar("chim_zone_kib",256);set_cvar("chim_reserve_kib",0);set_cvar("chim_pool_kib",1);
        snprintf(farfail_map,sizeof farfail_map,"{\n\"classname\" \"worldspawn\"\n\"_chim_frame\" \"0 0\"\n\"_chim_streamed_statics\" \"%d\"\n}\n",stated);
        console_used=0;console[0]=0;console_capture=1;
        begin_map(farfail_map);
        console_capture=0;
        if(Chim_FarOnly())break;
        end_map();
    }
    printf("farfail: %d statics stated leave the frame world no room%c",stated,10);
    assert(stated>0 && !Chim_Active());
    assert(strstr(console,"far terrain stays as the floor") && Chim_FarOnly() && ChimFar_Loaded());
    VectorSet(p,64,64,40);assert(aw_chim_floor && aw_chim_floor(p,&lowest,&surface));
    end_map();assert(!Chim_FarOnly() && !ChimFar_Loaded());
    printf("farfail ok%c",10);
}

int main(int argc,char **argv){
    setvbuf(stdout,NULL,_IONBF,0);
    heap=calloc(1,HEAP_BYTES);assert(heap);
    vid.colormap=(byte *)heap;
    if(argc<2)return 2;
    if(!strcmp(argv[1],"legacy"))legacy();
    else if(!strcmp(argv[1],"inactive"))inactive();
    else if(!strcmp(argv[1],"ring"))ring();
    else if(!strcmp(argv[1],"evict"))evict();
    else if(!strcmp(argv[1],"fullzone"))fullzone();
    else if(!strcmp(argv[1],"cache"))cache();
    else if(!strcmp(argv[1],"spawn"))spawn();
    else if(!strcmp(argv[1],"bigframe"))bigframe();
    else if(!strcmp(argv[1],"seam"))seam();
    else if(!strcmp(argv[1],"slots"))slots();
    else if(!strcmp(argv[1],"still"))still();
    else if(!strcmp(argv[1],"jump"))jump();
    else if(!strcmp(argv[1],"graftmodes"))graftmodes();
    else if(!strcmp(argv[1],"budget"))budget();
    else if(!strcmp(argv[1],"trim"))trim();
    else if(!strcmp(argv[1],"ahead"))ahead();
    else if(!strcmp(argv[1],"formats"))formats();
    else if(!strcmp(argv[1],"edge"))edge();
    else if(!strcmp(argv[1],"rest"))rest();
    else if(!strcmp(argv[1],"story"))story();
    else if(!strcmp(argv[1],"statics"))statics();
    else if(!strcmp(argv[1],"far"))far();
    else if(!strcmp(argv[1],"pin"))pin();
    else if(!strcmp(argv[1],"baddata"))baddata();
    else if(!strcmp(argv[1],"efragcap"))efragcap();
    else if(!strcmp(argv[1],"farfail"))farfail();
    else return 2;
    return 0;
}
