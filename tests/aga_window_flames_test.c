/* SPDX-License-Identifier: GPL-2.0-or-later
 * FIREPIT-FLAMES-62: the flames of every frame of a CHIM window (aw_guard_torch.c). A region map's own entity text
 * holds only its own frame's aw_flame rows; a frame entered by a streamed crossing is read from its frame map once,
 * when it joins the window, and every slot's rows are drawn at that slot's offset. */
#include "quakedef.h"
#include "r_local.h"
#include "aw_state.h"
#include "aw_torch.h"
#include <assert.h>
server_t sv;server_static_t svs;client_state_t cl;client_static_t cls;
entity_t cl_entities[MAX_EDICTS],*cl_visedicts[MAX_VISEDICTS];int cl_numvisedicts;
int (*aw_view_torch_emitter)(vec3_t out);
int (*aw_flame_depth_limit)(void);
__attribute__((weak)) int r_campfires=1;
dlight_t cl_dlights[MAX_DLIGHTS];viddef_t vid;refdef_t r_refdef;
vec3_t vpn,vup,vright;float aliasxcenter,aliasycenter,aliasxscale,aliasyscale;
short *d_pzbuffer;unsigned int d_zwidth;aw_state_t aw_state;double host_frametime;
cvar_t r_drawentities={"r_drawentities","1",false,false,1};
char *pr_strings="";
char com_token[1024];
/* Quake's COM_Parse (common.c), enough of it: quoted strings and the brace tokens */
char *COM_Parse(char *data)
{
    int len=0,c;
    com_token[0]=0;
    if(!data)return NULL;
    for(;;){
        while((c=*data)<=' '){if(!c)return NULL;data++;}
        break;
    }
    if(c=='"'){data++;while((c=*data++)!='"' && c)com_token[len++]=(char)c;com_token[len]=0;return c?data:data-1;}
    if(c=='{' || c=='}'){com_token[0]=(char)c;com_token[1]=0;return data+1;}
    while(c>' ' && c!='{' && c!='}' && c!='"'){com_token[len++]=(char)c;c=*++data;}
    com_token[len]=0;return data;
}
extern int (*aw_chim_window_slot)(int,int *,int *,float *);
extern int (*aw_chim_map_frame)(const char *,int *,int *);
extern char *(*aw_frame_map_entities)(int,int);
static struct {int used,cx,cy;float offset[2];} slots[4];static int reads,unreadable_cx=99;
static int slot(int i,int *cx,int *cy,float *offset){
    if(!slots[i].used)return 0;
    *cx=slots[i].cx;*cy=slots[i].cy;offset[0]=slots[i].offset[0];offset[1]=slots[i].offset[1];return 1;
}
static int map_frame(const char *entities,int *cx,int *cy){(void)entities;*cx=2;*cy=4;return 1;}
static const char own_text[]="{ \"classname\" \"worldspawn\" \"_chim_frame\" \"2 4\" }"
    "{ \"classname\" \"aw_flame\" \"origin\" \"10 20 30\" \"aw_flame_size\" \"8\" \"aw_flame_shape\" \"6 40 2\" }";
/* frame 3,4: two fire pits; frame 2,3: 70 flames (6 past the slot's 64) */
static char *frame_text(int cx,int cy){
    char *t;int i,n=0;
    reads++;
    if(cx==unreadable_cx)return NULL;
    t=(char *)malloc(16384);
    n+=sprintf(t+n,"{ \"classname\" \"worldspawn\" }");
    for(i=0;i<(cx==3?2:70);i++)
        n+=sprintf(t+n,"{ \"classname\" \"aw_flame\" \"origin\" \"%d 5 7\" \"aw_flame_size\" \"8\" }{ \"classname\" \"light\" }",i);
    return t;
}
int main(void)
{
    static model_t world;int count,i;const aw_static_flame_t *f;unsigned long counts[6];
    static char own[sizeof(own_text)];
    memcpy(own,own_text,sizeof(own_text));world.entities=own;cl.worldmodel=&world;
    /* no CHIM window (hooks not set: a room, a legacy map): the loaded map's flames, as before */
    f=AW_StaticFlamesList(&count);assert(count==1 && f[0].origin[0]==10 && f[0].shape[0]==6);
    aw_chim_window_slot=slot;aw_chim_map_frame=map_frame;aw_frame_map_entities=frame_text;
    /* a window of the map's own frame: its own rows, at its offset, nothing read from disk */
    slots[0].used=1;slots[0].cx=2;slots[0].cy=4;
    f=AW_StaticFlamesList(&count);assert(count==1 && reads==0);
    /* the Ghostgate crossing: frame 3,4 joins at +2048 x: its two fire pits are read once and drawn there */
    slots[1].used=1;slots[1].cx=3;slots[1].cy=4;slots[1].offset[0]=2048;
    f=AW_StaticFlamesList(&count);assert(count==3 && reads==1);
    for(i=0;i<count && f[i].origin[0]!=2048+1;i++);
    assert(i<count && f[i].origin[1]==5 && f[i].scale==8);
    f=AW_StaticFlamesList(&count);assert(count==3 && reads==1);   /* no change: no read, no rebuild */
    /* a recentre: every slot's rows move with its offset */
    slots[0].offset[0]=-2048;slots[1].offset[0]=0;
    f=AW_StaticFlamesList(&count);assert(count==3 && reads==1);
    for(i=0;i<count && f[i].origin[2]!=30;i++);
    assert(i<count && f[i].origin[0]==10-2048);
    /* a busy frame: 64 kept, the rest counted; an unreadable frame: none, counted */
    slots[2].used=1;slots[2].cx=2;slots[2].cy=3;slots[3].used=1;slots[3].cx=99;slots[3].cy=4;
    f=AW_StaticFlamesList(&count);assert(count==3+64 && reads==3);
    AW_StaticFlamesWindowCounts(counts);
    assert(counts[0]==2 && counts[1]==66 && counts[2]==6 && counts[3]==1 && counts[4]==67 && counts[5]==1);
    /* frame 3,4 leaves the window: its rows go */
    slots[1].used=0;f=AW_StaticFlamesList(&count);assert(count==1+64);
    printf("window flames ok\n");
    return 0;
}
