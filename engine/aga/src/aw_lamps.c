/* SPDX-License-Identifier: GPL-2.0-or-later
 * Night lamps the Quake way: the original exterior lamps, lanterns, torches and
 * fires (id1/world/lamps.awl, original coordinates sorted by cell, written by
 * tools/light_sources.py lamp-table) give steady dynamic lights at night, the
 * nearest aw_lamp_lights of them, like the guard torches (aw_guard_torch.c).
 * The table is read from disk once per cell change, 3 x 3 cells around the
 * player; nothing per frame touches the disk. Quake light has no colour; the
 * lamps add brightness only. Each lamp gives a torch's worth of light (the
 * torch radius and surface gain, aw_torch.h).
 *
 * Night windows (aw_night_window_lights, default 1; an AmiWind addition): the
 * map's window-glass textures listed in id1/world/night-windows.txt (one line
 * per map: map name, then texture names) glow at night like emissive glass.
 * The list is read once per map; the surface cache is rebuilt only when night
 * starts or ends.
 */
#include "quakedef.h"
#include "aw_world.h"
#include "aw_torch.h"
#include "aw_sky.h"
#include "aw_remote.h"
#include <stdint.h>
#define LAMP_ROW 20
#define LAMP_CACHE 96
#define LAMP_RANGE 512.0f
/* A lamp behind the view counts this many times as far when the few light
 * slots are shared out: it only loses near-ties (3x made turning the head
 * swap lamps on and off, LAMPS-FLICKER-31). */
#define LAMP_BEHIND 1.5f
/* A lit lamp keeps its slot unless a rival is clearly nearer: its squared
 * distance counts at this fraction (about 0.7 of the distance). */
#define LAMP_KEEP .5f
/* Seconds a lamp takes to grow to full radius when chosen, and to shrink
 * away when dropped (on the spare lamp keys); nothing snaps on or off. */
#define LAMP_FADE .4f
typedef struct {float origin[3],radius,lit_since,off_since;int cool,lit,fading;} lamp_t;
static lamp_t lamps[LAMP_CACHE];
static int lamp_count,lamp_cell_valid,lamp_cell[2];
static cvar_t aw_lamp_lights={"aw_lamp_lights","2",true};
static cvar_t aw_night_window_lights={"aw_night_window_lights","1",true};
/* Lamp light radius relative to the torch's (dbg outdoorlantern 1.0): the
 * brightness at the lamp stays a torch's; 0.25..3. The owner chose 1.0 over
 * 1.5 and 2.0 from same-pose captures: pools of light, darker street between. */
static cvar_t aw_lamp_radius={"aw_lamp_radius","1",true};
static model_t *window_world;
/* Lamps burn whenever the sky is dimmed at all (the original's lamps never
 * switch off; in full daylight their light would not show, so the per-frame
 * light is saved only then), or in the guard torches' night when the old
 * whole-frame night look is chosen (daylight stays full). A dusk threshold
 * put them out at 4 AM while it was still dark (owner, dev4). */
#define LAMP_DUSK_DAYLIGHT 256
static int lamp_night(void){return R_SkyExterior() && (r_daylight<LAMP_DUSK_DAYLIGHT || AW_GuardTorchNight());}
/* Last frame's choice, for dbg lamps. */
static int last_found,last_index[AW_LAMP_LIGHT_COUNT];static float last_distance[AW_LAMP_LIGHT_COUNT];
static uint32_t u32(const byte *p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static int s16(const byte *p){return (int)(int16_t)(uint16_t)(p[0]|(p[1]<<8));}
static float f32(const byte *p){uint32_t n=u32(p);float f;memcpy(&f,&n,4);return f;}
/* Read every row of one cell into the cache; the table is sorted by cell. */
static void load_cell(FILE *f,long base,unsigned count,int cx,int cy)
{
    byte row[LAMP_ROW];int lo=0,hi=(int)count,mid,rx,ry;
    while(lo<hi){
        mid=lo+(hi-lo)/2;
        if(fseek(f,base+8+(long)mid*LAMP_ROW,SEEK_SET) || fread(row,1,LAMP_ROW,f)!=LAMP_ROW)return;
        rx=s16(row);ry=s16(row+2);
        if(rx<cx || (rx==cx && ry<cy))lo=mid+1;else hi=mid;
    }
    if(fseek(f,base+8+(long)lo*LAMP_ROW,SEEK_SET))return;
    for(;lo<(int)count && lamp_count<LAMP_CACHE;lo++){
        lamp_t *l=&lamps[lamp_count];int k;
        if(fread(row,1,LAMP_ROW,f)!=LAMP_ROW || s16(row)!=cx || s16(row+2)!=cy)return;
        for(k=0;k<3;k++)l->origin[k]=f32(row+4+k*4);
        l->radius=(float)(row[16]|(row[17]<<8));l->cool=row[19]==2;l->lit=l->fading=0;l->lit_since=l->off_since=0;
        if(isfinite(l->origin[0]) && isfinite(l->origin[1]) && isfinite(l->origin[2]) && l->radius>0)lamp_count++;
    }
}
static void load_cells(int cx,int cy)
{
    FILE *f=NULL;byte header[8];long base;int size,dx,dy;unsigned count;
    lamp_count=0;lamp_cell_valid=1;lamp_cell[0]=cx;lamp_cell[1]=cy;
    size=COM_FOpenFile("world/lamps.awl",&f);if(!f)return;
    base=ftell(f);
    if(base>=0 && size>=8 && fread(header,1,8,f)==8 && !memcmp(header,"AWL1",4)){
        count=u32(header+4);
        if(count<=65536 && (long)size==8+(long)count*LAMP_ROW)
            for(dx=-1;dx<=1;dx++)for(dy=-1;dy<=1;dy++)load_cell(f,base,count,cx+dx,cy+dy);
    }
    fclose(f);
}
/* One whitespace-separated token from the list; returns its length (0 at end
 * of line or file) and sets *eol when the line ended after it. */
static int window_token(FILE *f,char *out,int size,int *eol)
{
    int c,n=0;
    *eol=0;
    while((c=getc(f))==' ' || c=='\t' || c=='\r'){}
    if(c==EOF){*eol=1;return 0;}
    if(c=='\n'){*eol=1;return 0;}
    while(c!=EOF && c!=' ' && c!='\t' && c!='\r' && c!='\n'){if(n<size-1)out[n++]=(char)c;c=getc(f);}
    out[n]=0;if(c=='\n' || c==EOF)*eol=1;
    return n;
}
/* This map's window textures: the line whose first token is the map's name. */
static void load_windows(void)
{
    FILE *f=NULL;char map[MAX_QPATH],token[32];const char *name,*dot;int eol,i,n,mine;
    r_night_window_count=0;
    if(!cl.worldmodel || !cl.worldmodel->textures)return;
    name=strrchr(cl.worldmodel->name,'/');name=name?name+1:cl.worldmodel->name;
    snprintf(map,sizeof map,"%s",name);dot=strrchr(map,'.');if(dot)map[dot-map]=0;
    if(COM_FOpenFile("world/night-windows.txt",&f)<0 || !f)return;
    for(;;){
        n=window_token(f,token,sizeof token,&eol);
        if(!n){if(feof(f))break;continue;}
        mine=!Q_strcasecmp(token,map);
        while(!eol && window_token(f,token,sizeof token,&eol)){
            if(!mine || r_night_window_count>=R_NIGHT_WINDOWS)continue;
            for(i=0;i<cl.worldmodel->numtextures;i++)
                if(cl.worldmodel->textures[i] && !Q_strcasecmp(cl.worldmodel->textures[i]->name,token)){
                    r_night_windows[r_night_window_count++]=cl.worldmodel->textures[i];break;
                }
        }
        if(mine)break;
    }
    fclose(f);
}
static void night_windows(void)
{
    int on;
    if(cl.worldmodel!=window_world){window_world=cl.worldmodel;r_night_windows_on=0;load_windows();}
    on=aw_night_window_lights.value>0 && r_night_window_count>0 && lamp_night();
    if(on!=r_night_windows_on){r_night_windows_on=on;D_FlushCaches();}
}
extern cvar_t aw_warm_light;
/* dbg lamps: what the night lamps see here, to find where a crossing loses them. */
static void lamp_status(void)
{
    int j;lamp_t *l;
    Con_Printf("Lamps: map %s, %s, night lights %s, lamp lights %ld, radius %g, warm %s.\n",
        cl.worldmodel?cl.worldmodel->name:"none",lamp_night()?"dark exterior (lamps on)":"not a dark exterior (lamps off)",
        r_lamps?"on":"off",(long)aw_lamp_lights.value,AW_TorchLightRadius()*aw_lamp_radius.value,r_warm_colormap?"on":"off");
    /* Why lamps are on or off: each part of lamp_night separately. */
    Con_Printf("Night test: exterior %d, daylight %d (lamps below %d), guard night %d.\n",R_SkyExterior(),r_daylight,LAMP_DUSK_DAYLIGHT,AW_GuardTorchNight());
    if(!lamp_cell_valid)Con_Printf("Lamp table not read yet (it is read at night).\n");
    else Con_Printf("Cached %ld lamps around cell %ld, %ld.\n",(long)lamp_count,(long)lamp_cell[0],(long)lamp_cell[1]);
    for(j=0;j<last_found;j++){
        l=&lamps[last_index[j]];
        Con_Printf("Lit: original %ld %ld %ld, %ld units away%s.\n",(long)l->origin[0],(long)l->origin[1],(long)l->origin[2],
            (long)last_distance[j],l->cool?" (blue)":"");
    }
    Con_Printf("Night windows: %ld textures, %s.\n",(long)r_night_window_count,r_night_windows_on?"glowing":"off");
}
int AW_LampLitCount(void){return last_found;}
void AW_LampInit(void)
{
    Cvar_RegisterVariable(&aw_lamp_lights);Cvar_RegisterVariable(&aw_night_window_lights);
    Cvar_RegisterVariable(&aw_warm_light);Cvar_RegisterVariable(&aw_lamp_radius);Cmd_AddCommand("aw_lamp_status",lamp_status);AW_RemoteInit();AW_FogLocationInit();
}
/* Each frame at night: the nearest lamps within range get a steady light that
 * dies unless refreshed, so lamps fade out as soon as they are not chosen. */
void AW_LampUpdate(void)
{
    float view[3],global[3],local[3],best_d[AW_LAMP_LIGHT_COUNT],d,dx,dy,dz;
    int best[AW_LAMP_LIGHT_COUNT],wanted,found=0,i,j,cx,cy;dlight_t *light;
    memset(r_dlight_cool,0,sizeof r_dlight_cool);
    if(sv.active && cls.state==ca_connected)night_windows();
    wanted=aw_lamp_lights.value<0?0:aw_lamp_lights.value>AW_LAMP_LIGHT_COUNT?AW_LAMP_LIGHT_COUNT:(int)aw_lamp_lights.value;
    if(!wanted || !r_lamps || !sv.active || cls.state!=ca_connected || !lamp_night()){
        for(i=0;i<lamp_count;i++)lamps[i].lit=lamps[i].fading=0; /* fade in again when they return */
        return;
    }
    VectorCopy(r_refdef.vieworg,view);
    if(!AW_WorldToSource(sv.name,view,global))return;
    cx=(int)floor(global[0]/8192.0);cy=(int)floor(global[1]/8192.0);
    if(!lamp_cell_valid || cx!=lamp_cell[0] || cy!=lamp_cell[1])load_cells(cx,cy);
    for(i=0;i<lamp_count;i++){
        dx=lamps[i].origin[0]-global[0];dy=lamps[i].origin[1]-global[1];dz=lamps[i].origin[2]-global[2];
        d=(dx*dx+dy*dy+dz*dz)*(1.0f/16);
        if(!(d<LAMP_RANGE*LAMP_RANGE))continue;
        /* Local and source axes are the same (scale and offset only). */
        if(dx*vpn[0]+dy*vpn[1]+dz*vpn[2]<0)d*=LAMP_BEHIND*LAMP_BEHIND;
        if(lamps[i].lit)d*=LAMP_KEEP;
        for(j=found<wanted?found++:wanted;j>0 && best_d[j-1]>d;j--){
            if(j<wanted){best_d[j]=best_d[j-1];best[j]=best[j-1];}
        }
        if(j<wanted){best_d[j]=d;best[j]=i;}
    }
    last_found=found;
    for(j=0;j<found;j++){last_index[j]=best[j];last_distance[j]=(float)sqrt(best_d[j]);}
    /* Fade: a lamp lit last frame keeps its start time; a new one starts now
     * (from where its fade-out had got to); a dropped one starts fading out. */
    for(i=0;i<lamp_count;i++){
        int chosen=0;float t;
        for(j=0;j<found;j++)if(best[j]==i)chosen=1;
        if(chosen && !lamps[i].lit){
            t=lamps[i].fading?1-((float)cl.time-lamps[i].off_since)/LAMP_FADE:0;
            lamps[i].lit_since=(float)cl.time-LAMP_FADE*(t>0?t:0);lamps[i].fading=0;
        }else if(!chosen && lamps[i].lit){lamps[i].fading=1;lamps[i].off_since=(float)cl.time;}
        lamps[i].lit=chosen;
    }
    for(j=0;j<found;j++){
        if(!AW_SourceToWorld(sv.name,lamps[best[j]].origin,local))continue;
        light=CL_AllocDlight(AW_LAMP_LIGHT_KEY-j);
        if(light-cl_dlights>=0 && light-cl_dlights<32)r_dlight_cool[light-cl_dlights]=(unsigned char)lamps[best[j]].cool;
        VectorCopy(local,light->origin);
        /* A torch's worth of light: the torch radius, and the torch surface
         * gain for the lamp keys (aw_torch.h). */
        light->radius=AW_TorchLightRadius()*(aw_lamp_radius.value>=.25f?(aw_lamp_radius.value>3?3:aw_lamp_radius.value):.25f);
        {float fade=((float)cl.time-lamps[best[j]].lit_since)/LAMP_FADE;
         if(fade<1)light->radius*=fade>.05f?fade:.05f;}
        light->minlight=16;light->die=cl.time+.1;light->decay=0;
    }
    /* Dropped lamps shrink away on the keys the chosen ones left free. */
    for(i=0,j=found;i<lamp_count && j<AW_LAMP_LIGHT_COUNT;i++){
        float t;
        if(!lamps[i].fading)continue;
        t=((float)cl.time-lamps[i].off_since)/LAMP_FADE;
        if(!(t<1) || !AW_SourceToWorld(sv.name,lamps[i].origin,local)){lamps[i].fading=t<1;continue;}
        light=CL_AllocDlight(AW_LAMP_LIGHT_KEY-j);j++;
        if(light-cl_dlights>=0 && light-cl_dlights<32)r_dlight_cool[light-cl_dlights]=(unsigned char)lamps[i].cool;
        VectorCopy(local,light->origin);
        light->radius=AW_TorchLightRadius()*(aw_lamp_radius.value>=.25f?(aw_lamp_radius.value>3?3:aw_lamp_radius.value):.25f)*(1-t>.05f?1-t:.05f);
        light->minlight=16;light->die=cl.time+.1;light->decay=0;
    }
}
