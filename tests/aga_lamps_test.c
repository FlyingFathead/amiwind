/* SPDX-License-Identifier: GPL-2.0-or-later
 * Night lamps: table read per cell from disk, nearest lamps lit at night only,
 * switched off by r_lamps and aw_lamp_lights 0, corrupt tables ignored. */
#include "quakedef.h"
#include "aw_torch.h"
#include "aw_sky.h"
#include <assert.h>
client_static_t cls;client_state_t cl;server_t sv;refdef_t r_refdef;vec3_t vpn={1,0,0};
dlight_t cl_dlights[MAX_DLIGHTS];
int r_lamps=1,r_daylight=256;
unsigned char *r_warm_colormap;
int R_SkyExterior(void){return 1;}
static void (*lamp_status_command)(void);
void Cmd_AddCommand(char *n,void (*f)(void)){assert(!strcmp(n,"aw_lamp_status"));lamp_status_command=f;}
void Con_Printf(char *fmt,...){(void)fmt;}
unsigned char r_dlight_cool[32];
struct texture_s *r_night_windows[R_NIGHT_WINDOWS];int r_night_window_count,r_night_windows_on;
static int night=1,opens,corrupt,overflow,flushes,window_opens;static cvar_t *lamp_cvar,*window_cvar,*warm_cvar;
void D_FlushCaches(void){flushes++;}
cvar_t aw_warm_light={"aw_warm_light","1",true}; /* defined in r_surf.c, registered here */
float AW_TorchLightRadius(void){return 192;}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
void Cvar_RegisterVariable(cvar_t *v){v->value=atof(v->string);
    if(!strcmp(v->name,"aw_lamp_lights"))lamp_cvar=v;else if(!strcmp(v->name,"aw_night_window_lights"))window_cvar=v;
    else if(!strcmp(v->name,"aw_lamp_radius"))assert(v->value==1 && v->archive);
    else{assert(!strcmp(v->name,"aw_warm_light"));warm_cvar=v;}}
int AW_GuardTorchNight(void){return night;}
/* Local frame: original coordinates / 4, region origin (0,0,0). */
int AW_WorldToSource(const char *name,const float *local,float *world){int k;for(k=0;k<3;k++)world[k]=local[k]*4;return 1;}
int AW_SourceToWorld(const char *name,const float *world,float *local){int k;for(k=0;k<3;k++)local[k]=world[k]*.25f;return 1;}
dlight_t *CL_AllocDlight(int key){int i;
    for(i=0;i<MAX_DLIGHTS;i++)if(cl_dlights[i].key==key){memset(&cl_dlights[i],0,sizeof cl_dlights[i]);cl_dlights[i].key=key;return &cl_dlights[i];}
    for(i=0;i<MAX_DLIGHTS;i++)if(!cl_dlights[i].key || cl_dlights[i].die<cl.time){memset(&cl_dlights[i],0,sizeof cl_dlights[i]);cl_dlights[i].key=key;return &cl_dlights[i];}
    assert(0);return NULL;}
static void row(FILE *f,int cx,int cy,float x,float y,float z,int radius){
    short c[2];float p[3];unsigned short r=(unsigned short)radius;unsigned char tail[2]={1,0};
    c[0]=(short)cx;c[1]=(short)cy;p[0]=x;p[1]=y;p[2]=z;
    fwrite(c,2,2,f);fwrite(p,4,3,f);fwrite(&r,2,1,f);fwrite(tail,1,2,f);}
int COM_FOpenFile(char *name,FILE **out){
    FILE *f;unsigned count=5;
    if(!strcmp(name,"world/night-windows.txt")){
        static const char list[]="bm001 surface9\nbm019 surface43 glass_w surface7\r\nsn000 surface43\n";
        window_opens++;f=tmpfile();assert(f);fputs(list,f);rewind(f);*out=f;return (int)strlen(list);
    }
    opens++;assert(!strcmp(name,"world/lamps.awl"));
    f=tmpfile();assert(f);
    if(overflow){ /* 300 lamps in cell (7,7): more than the cache holds */
        int i;count=300;fwrite("AWL1",1,4,f);fwrite(&count,4,1,f);
        for(i=0;i<300;i++)row(f,7,7,57444+(float)i,57444,0,223);
        rewind(f);*out=f;return 8+300*20;}
    fwrite("AWL1",1,4,f);if(corrupt)count=9;fwrite(&count,4,1,f);
    /* Sorted by cell: (-1,0), (0,0) x3, (5,5). Little-endian host assumed. */
    row(f,-1,0,-400,100,0,223);
    row(f,0,0,100,0,0,223);row(f,0,0,400,0,0,64);row(f,0,0,1200,0,0,512);
    row(f,5,5,41000,41000,0,223);
    rewind(f);*out=f;return 8+5*20;}
static int lit(float x){int i;for(i=0;i<MAX_DLIGHTS;i++)
    if(cl_dlights[i].key<=AW_LAMP_LIGHT_KEY && cl_dlights[i].key>AW_LAMP_LIGHT_KEY-AW_LAMP_LIGHT_COUNT &&
       cl_dlights[i].die>=cl.time && fabs(cl_dlights[i].origin[0]-x)<.01f)return 1;
    return 0;}
static int count_lit(void){int i,n=0;for(i=0;i<MAX_DLIGHTS;i++)
    if(cl_dlights[i].key<=AW_LAMP_LIGHT_KEY && cl_dlights[i].key>AW_LAMP_LIGHT_KEY-AW_LAMP_LIGHT_COUNT && cl_dlights[i].die>=cl.time)n++;
    return n;}
static void frame(void){cl.time+=1;AW_LampUpdate();}
void AW_RemoteInit(void){}
void AW_FogLocationInit(void){}
int main(void){
    AW_LampInit();assert(lamp_cvar && lamp_cvar->value==2 && lamp_cvar->archive);
    assert(window_cvar && !strcmp(window_cvar->name,"aw_night_window_lights") && window_cvar->value==1 && window_cvar->archive);
    assert(warm_cvar && warm_cvar->value==1 && warm_cvar->archive);
    sv.active=1;cls.state=ca_connected;strcpy(sv.name,"balmora");
    r_refdef.vieworg[0]=10;r_refdef.vieworg[1]=0;r_refdef.vieworg[2]=0;
    frame();assert(opens==1 && count_lit()==2);
    /* Nearest two: local x 25 (distance 15) and 100 (90); -100 in cell -1 is at 113. */
    assert(lit(25) && lit(100) && !lit(-100) && !lit(300));
    frame();assert(opens==1); /* same cell: no disk access */
    lamp_cvar->value=1;frame();assert(lit(25) && lit(100)); /* 100 fades out */
    frame();assert(count_lit()==1 && lit(25));
    night=0;frame();assert(count_lit()==0);night=1;
    r_lamps=0;frame();assert(count_lit()==0);r_lamps=1;
    lamp_cvar->value=0;frame();assert(count_lit()==0);lamp_cvar->value=2;
    /* Lamps lit again fade in: the first frame at 5% of the radius, then full. */
    frame();{int i;for(i=0;i<MAX_DLIGHTS;i++)if(cl_dlights[i].key<=AW_LAMP_LIGHT_KEY && cl_dlights[i].die>=cl.time)assert(cl_dlights[i].radius<10);}
    /* A torch's worth of light, aw_lamp_radius 1: every lit lamp has the torch radius 192. */
    frame();{int i;for(i=0;i<MAX_DLIGHTS;i++)if(cl_dlights[i].key<=AW_LAMP_LIGHT_KEY && cl_dlights[i].die>=cl.time)assert(cl_dlights[i].radius==192);}
    /* Turning round does not swap the lit lamps (LAMPS-FLICKER-31). */
    vpn[0]=-1;frame();assert(count_lit()==2 && lit(25) && lit(100) && !lit(-100));
    /* A clearly nearer lamp takes a slot; the dropped one fades out, then goes. */
    r_refdef.vieworg[0]=260;frame();assert(lit(300) && lit(100) && lit(25));
    frame();assert(count_lit()==2 && lit(300) && lit(100) && !lit(25));
    vpn[0]=1;r_refdef.vieworg[0]=10;
    /* Far cell: only that cell's neighbourhood is read; lamps out of range give none. */
    r_refdef.vieworg[0]=10250;r_refdef.vieworg[1]=10250;frame();assert(opens==2 && count_lit()==1 && lit(10250));
    corrupt=1;r_refdef.vieworg[0]=10;r_refdef.vieworg[1]=0;frame();assert(opens==3 && count_lit()==0);corrupt=0;
    /* More lamps than the cache: 256 kept, the rest counted as dropped (LAMPS-CACHE-31). */
    overflow=1;r_refdef.vieworg[0]=14361;r_refdef.vieworg[1]=14361;frame();
    assert(opens==4 && AW_LampCachedCount()==256 && AW_LampDroppedCount()==44 && count_lit()==2);overflow=0;
    /* Night windows: this map's listed textures only (other maps' lines and
     * names missing from the map ignored), on at night, one cache rebuild per switch. */
    {
        static texture_t t[3];static texture_t *list[3]={&t[0],&t[1],&t[2]};static model_t world;int before;
        strcpy(t[0].name,"surface43");strcpy(t[1].name,"surface7");strcpy(t[2].name,"surface9");
        strcpy(world.name,"maps/bm019.bsp");world.textures=list;world.numtextures=3;cl.worldmodel=&world;
        night=1;before=flushes;frame();
        assert(window_opens==1 && r_night_window_count==2 && r_night_windows[0]==&t[0] && r_night_windows[1]==&t[1]);
        assert(r_night_windows_on && flushes==before+1);
        frame();assert(window_opens==1 && flushes==before+1);
        night=0;frame();assert(!r_night_windows_on && flushes==before+2);
        night=1;window_cvar->value=0;frame();assert(!r_night_windows_on && flushes==before+2);window_cvar->value=1;
        frame();assert(r_night_windows_on && flushes==before+3);
        strcpy(world.name,"maps/vf0001.bsp");cl.worldmodel=NULL;frame();cl.worldmodel=&world;frame();
        assert(window_opens==2 && r_night_window_count==0 && !r_night_windows_on);
    }
    puts("night lamps: per-cell table, nearest lit at night, torch radius, switches, corrupt table, cache overflow, night windows");
    return 0;
}
