/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "amiwind_version.h"
#include "aw_world.h"
#include "aw_clock.h"
#include "aw_npc_lod.h"
int sb_lines;
/* Set by Chim_Init: original coordinates on an active CHIM frame. */
int (*aw_chim_source)(const float *local,float *world);
/* GLOBAL position for the debug readouts: the world directory's transform,
 * else the active CHIM frame's (a disk without the world directory). */
static int view_source(const float *local,float *world) {
    if(sv.active && AW_WorldToSource(sv.name,local,world))return 1;
    return sv.active && aw_chim_source && aw_chim_source(local,world);
}
static cvar_t coords = {"_aw_debug_coords", "0", true};
static cvar_t overlays = {"_aw_debug_all", "0", true};
static cvar_t fps = {"_aw_debug_fps", "0", true};
static cvar_t show_compass = {"aw_compass", "0", true};
static cvar_t hud_type = {"_aw_debug_hud_type", "2", true};
extern int AW_FpsTenths(void);
/* Exterior water at source Z=0; visibility only, not water physics. */
static cvar_t sealevel = {"_aw_debug_sealevel", "1", true};
extern cvar_t scr_showram;
extern int scr_copyeverything;
int AW_DebugOverlaysEnabled(void) {return overlays.value != 0;}
int AW_DebugCoordsEnabled(void) {return overlays.value != 0 && coords.value != 0;}
int AW_SeaLevelEnabled(void) {return sealevel.value != 0;}
static int debug_toggle(cvar_t *setting,char *name) {
    char *value;
    if(Cmd_Argc()==1) {
        Con_Printf("%s %s\n", name,setting->value?"on":"off");return 0;
    }
    value=Cmd_Argv(1);
    if(Cmd_Argc()!=2 || (Q_strcasecmp(value,"true") && Q_strcasecmp(value,"false") &&
       Q_strcasecmp(value,"on") && Q_strcasecmp(value,"off") && strcmp(value,"1") && strcmp(value,"0"))) {
        Con_Printf("Usage: %s on/off, true/false, or 1/0\n",name);return 0;
    }
    Cvar_SetValue(setting->name, !Q_strcasecmp(value,"true") || !Q_strcasecmp(value,"on") || !strcmp(value,"1"));
    vid.recalc_refdef=true;
    return 1;
}
static void debug_coords(void) {debug_toggle(&coords,"amiwind_debug_coords");}
static void debug_all(void) {
    if(debug_toggle(&overlays,"amiwind_show_debug"))
        Cvar_SetValue(coords.name,overlays.value!=0);
}
static void debug_compass(void) {
    if(debug_toggle(&show_compass,"dbg compass"))scr_copyeverything=1;
}
static void debug_fps(void) {debug_toggle(&fps,"amiwind_debug_fps");}
static void debug_showfps(void) {if(Cmd_Argc()==1)Cvar_SetValue(fps.name,1);else debug_fps();}
static void debug_ram(void) {debug_toggle(&scr_showram,"amiwind_debug_showram");}
static void debug_sea(void) {debug_toggle(&sealevel,"amiwind_debug_sealevel");}
static void debug_hud_type(void) {
    if(Cmd_Argc()==1){Con_Printf("Debug HUD type %ld\n",(long)hud_type.value);return;}
    if(Cmd_Argc()!=2 || (strcmp(Cmd_Argv(1),"1") && strcmp(Cmd_Argv(1),"2"))){
        Con_Printf("Usage: dbg hud type 1/2\n");return;
    }
    Cvar_SetValue(hud_type.name,atoi(Cmd_Argv(1)));scr_copyeverything=1;
}
/* Original Morrowind cell for the debug HUD. Exteriors: the grid
 * cell of the GLOBAL position (8192 original units per cell, floor). Interiors:
 * the builder's stable number and the full cell ID from worldspawn keys
 * _aw_cell_int / _aw_cell_id, read once per loaded map. */
static const model_t *cell_model;
static char cell_map[64];
static long cell_number;
static char cell_id[64];
static char *cell_token(char *data,char *token,int capacity) {
    int n=0;
    if(!data)return NULL;
    while(*data && (unsigned char)*data<=32)data++;
    if(!*data)return NULL;
    if(*data=='{' || *data=='}'){token[0]=*data++;token[1]=0;return data;}
    if(*data!='"')return NULL;
    data++;
    while(*data && *data!='"'){if(n>=capacity-1)return NULL;token[n++]=*data++;}
    if(*data!='"')return NULL;
    token[n]=0;return data+1;
}
static void cell_load(void) {
    char *data,key[64],value[128];int pairs=0;long n;
    /* Model slots are reused across maps: the name decides, not the pointer. */
    if(cell_model==cl.worldmodel && (!cl.worldmodel || !strncmp(cell_map,cl.worldmodel->name,sizeof(cell_map)-1)))return;
    cell_model=cl.worldmodel;cell_number=0;cell_id[0]=0;cell_map[0]=0;
    if(!cl.worldmodel || !(data=cl.worldmodel->entities))return;
    strncpy(cell_map,cl.worldmodel->name,sizeof(cell_map)-1);cell_map[sizeof(cell_map)-1]=0;
    data=cell_token(data,key,sizeof key);if(!data || strcmp(key,"{"))return;
    while((data=cell_token(data,key,sizeof key))!=NULL && strcmp(key,"}") && ++pairs<=256){
        if(!(data=cell_token(data,value,sizeof value)))break;
        if(!strcmp(key,"_aw_cell_int")){n=atol(value);cell_number=n>0 && n<100000?n:0;}
        else if(!strcmp(key,"_aw_cell_id")){strncpy(cell_id,value,sizeof(cell_id)-1);cell_id[sizeof(cell_id)-1]=0;}
    }
    if(!cell_number)cell_id[0]=0;
}
/* Exterior grid cell of a local position on this map; 0 when there is none. */
static int exterior_cell(const float *p,long *x,long *y,float *global) {
    if(!view_source(p,global))return 0;
    if(fabs(global[0])>2000000 || fabs(global[1])>2000000)return 0;
    *x=(long)floor(global[0]/8192.0);*y=(long)floor(global[1]/8192.0);return 1;
}
/* "CELL -3,-2" / "INT 412" (compact: "C -3,-2" / "I 412"); empty if unknown. */
static void cell_text(const float *p,int compact,char *out,int size) {
    long x,y;vec3_t global;
    out[0]=0;
    if(exterior_cell(p,&x,&y,global))snprintf(out,size,compact?"C %ld,%ld":"CELL %ld,%ld",x,y);
    else {cell_load();if(cell_number)snprintf(out,size,compact?"I %ld":"INT %ld",cell_number);}
}
/* Append the cell to the shorter row that still fits; full prefix first, then
 * the compact one, then the other row. Never adds a row or cuts a coordinate. */
static void place_cell(char *a,char *b,int size,const float *p,int limit) {
    char text[24];char *rows[2];int compact,i;
    rows[0]=strlen(a)<=strlen(b)?a:b;rows[1]=rows[0]==a?b:a;
    for(compact=0;compact<2;compact++){
        cell_text(p,compact,text,sizeof text);if(!text[0])return;
        for(i=0;i<2;i++)if((int)(strlen(rows[i])+1+strlen(text))<=limit &&
                           (int)(strlen(rows[i])+1+strlen(text))<size){
            strcat(rows[i]," ");strcat(rows[i],text);return;
        }
    }
}
/* "NOCLIP: ON" / "FLY: ON" and "GOD: ON" while the local player has that cheat
 * (compact: "NOCLIP" / "FLY" / "GOD"); empty otherwise. */
static void cheat_text(int compact,char *out,int size) {
    edict_t *e;const char *move=NULL;
    out[0]=0;
    if(!sv.active || svs.maxclients!=1 || !svs.clients || !svs.clients[0].edict)return;
    e=svs.clients[0].edict;
    if(e->v.movetype==MOVETYPE_NOCLIP)move="NOCLIP";
    else if(e->v.movetype==MOVETYPE_FLY)move="FLY";
    if(move)snprintf(out,size,compact?"%s":"%s: ON",move);
    if((int)e->v.flags & FL_GODMODE)
        snprintf(out+strlen(out),size-(int)strlen(out),compact?"%sGOD":"%sGOD: ON",out[0]?" ":"");
}
/* Same rule as the cell: the shorter row that still fits, full text first. */
static void place_cheats(char *a,char *b,int size,int limit) {
    char text[32];char *rows[2];int compact,i;
    rows[0]=strlen(a)<=strlen(b)?a:b;rows[1]=rows[0]==a?b:a;
    for(compact=0;compact<2;compact++){
        cheat_text(compact,text,sizeof text);if(!text[0])return;
        for(i=0;i<2;i++)if((int)(strlen(rows[i])+1+strlen(text))<=limit &&
                           (int)(strlen(rows[i])+1+strlen(text))<size){
            strcat(rows[i]," ");strcat(rows[i],text);return;
        }
    }
}
static void debug_cell(void) {
    long x,y;vec3_t global;vec_t *p;
    if(cls.state!=ca_connected){Con_Printf("Cell: no scene loaded.\n");return;}
    p=cl_entities[cl.viewentity].origin;
    if(sv.active && svs.maxclients==1 && svs.clients && svs.clients[0].edict)p=svs.clients[0].edict->v.origin;
    if(exterior_cell(p,&x,&y,global)){
        const char *region=AW_RegionNameAt(global);
        Con_Printf("Cell: CELL %ld,%ld (exterior grid; global %ld %ld) / %s / scene %s\n",x,y,
                   (long)global[0],(long)global[1],region?region:"region unavailable",sv.active?sv.name:"?");
        return;
    }
    cell_load();
    if(cell_number)Con_Printf("Cell: INT %ld = \"%s\" / map %s\n",cell_number,cell_id,sv.active?sv.name:"?");
    else Con_Printf("Cell: unknown for map %s (no exterior transform, no cell number).\n",sv.active?sv.name:"?");
}
void Sbar_Init(void) {
    Cvar_RegisterVariable(&coords);Cvar_RegisterVariable(&overlays);
    Cvar_RegisterVariable(&sealevel);
    Cvar_RegisterVariable(&fps);
    Cvar_RegisterVariable(&hud_type);
    Cvar_RegisterVariable(&show_compass);
    Cmd_AddCommand("amiwind_debug_compass",debug_compass);
    Cmd_AddCommand("aw_debug_hud_type",debug_hud_type);
    Cmd_AddCommand("amiwind_debug_coords",debug_coords);Cmd_AddCommand("amiwind_debug_all",debug_all);
    Cmd_AddCommand("amiwind_show_debug",debug_all);
    Cmd_AddCommand("amiwind_debug_showram",debug_ram);
    Cmd_AddCommand("amiwind_debug_sealevel",debug_sea);
    Cmd_AddCommand("amiwind_debug_fps",debug_fps);Cmd_AddCommand("amiwind_debug_showfps",debug_showfps);
    Cmd_AddCommand("aw_cell",debug_cell);
}
void Sbar_Changed(void) {}
static int current_region(const char **region) {
    vec3_t source;*region=NULL;
    if(cls.state!=ca_connected || !sv.active || svs.maxclients!=1 ||
       !svs.clients || !svs.clients[0].edict ||
       !AW_WorldToSource(sv.name,svs.clients[0].edict->v.origin,source))return 0;
    *region=AW_RegionNameAt(source);return 1;
}
static const char *directions[]={"N","NE","E","SE","S","SW","W","NW"};
static int compass_heading(void) {
    /* Runtime +Y is source north; engine yaw zero points east. */
    return (int)anglemod(90-cl.viewangles[YAW]+360);
}
static void coordinate_line(char *line,int y) {
    int limit=(vid.width-96)/4;
    if(limit<=0)return;
    if((int)strlen(line)>limit){line[limit]=0;if(limit>=3)memcpy(line+limit-3,"...",3);}
    AW_SmallString(vid.width-8-(int)strlen(line)*4,y,line);
}
static void compass(void) {
    char line[96];int heading,limit;const char *region=NULL;
    if(!show_compass.value || cls.state!=ca_connected || key_dest!=key_game || AW_GalleryActive())return;
    heading=compass_heading();
    current_region(&region);
    snprintf(line,sizeof(line),"%s %03ld / REGION: %s",directions[((heading+22)/45)&7],
             (long)heading,region?region:"unavailable");
    limit=(vid.width-96)/4;if(limit<0)limit=0;if(limit>95)limit=95;
    if((int)strlen(line)>limit){line[limit]=0;if(limit>=3)memcpy(line+limit-3,"...",3);}
    AW_SmallString(vid.width-8-(int)strlen(line)*4,vid.height-26,line);
    scr_copyeverything=1;
}
void Sbar_Draw(void) {
    char title[128];const char *region;int limit,width=hud_type.value==1?8:4;
    if(key_dest==key_console)return;
    AW_UIHud();
    compass();
    AW_NpcLodDrawLabels();
    /* Its strip replaces the bottom HUD. Photo mode hides it like everything
     * else over the view; Ctrl+H (dbg hud) brings it back with the debug HUD.
     * Its keys keep working while hidden (AW_WaitKey). */
    if((!AW_PhotoModeActive() || AW_DebugOverlaysEnabled()) && AW_LightGalleryDraw())return;
    if(!AW_DebugOverlaysEnabled())return;
    if(current_region(&region))
        snprintf(title,sizeof(title),"AmiWind v" AMIWIND_VERSION " Vvardenfell / %s",region?region:"Region unavailable");
    else
        snprintf(title,sizeof(title),"AmiWind v" AMIWIND_VERSION " / %s",cl.levelname[0]?cl.levelname:"Location unavailable");
    limit=(vid.width-16)/width;if(limit<0)limit=0;if(limit>127)limit=127;
    if((int)strlen(title)>limit){title[limit]=0;if(limit>=3)memcpy(title+limit-3,"...",3);}
    if(width==8)Draw_String(8,8,title);else AW_SmallString(8,8,title);
    if(fps.value){
        char line[32];int n=AW_FpsTenths(),x=8;
        sprintf(line,"FPS:%ld.%ld",(long)(n/10),(long)(n%10));
        Draw_Fill(x,19,80,10,255);Draw_String(x+4,20,line);
    }
    if(AW_DebugCoordsEnabled() && cls.state==ca_connected && cl.viewentity>0 && cl.viewentity<MAX_EDICTS) {
        char line[80],second[80],clock[16];vec_t *p=cl_entities[cl.viewentity].origin;vec3_t global;
        int year,month,day,hour,minute,heading;
        /* Report the simulated player in local play, before view interpolation. */
        if(sv.active && svs.maxclients==1 && svs.clients && svs.clients[0].edict)
            p=svs.clients[0].edict->v.origin;
        /* Two compact console-font rows beside the health/magicka/fatigue bars.
         * Photo mode has no bars and a full-screen view: the strip spans the
         * whole width (PHOTO-DEBUG-STRIP-33). */
        if(AW_PhotoModeActive())Draw_Fill(0,vid.height-18,vid.width,18,255);
        else Draw_Fill(88,vid.height-18,vid.width-88,18,255);
        if(view_source(p,global))
            snprintf(line,sizeof(line),"GLOBAL XYZ: %ld %ld %ld",(long)global[0],(long)global[1],(long)global[2]);
        else strcpy(line,"GLOBAL XYZ: unavailable (interior)");
        if(hud_type.value!=1){
            strcpy(clock," TIME --:--");
            if(AW_ClockEnsure()){
                AW_ClockDate(&year,&month,&day,&hour,&minute);
                snprintf(clock,sizeof(clock)," TIME %02d:%02d",hour,minute);
            }
            strncat(line,clock,sizeof(line)-strlen(line)-1);
        }
        if(hud_type.value==1)
            snprintf(second,sizeof(second),"LOCAL XYZ: %ld %ld %ld DEG:%ld P:%ld",(long)p[0],(long)p[1],(long)p[2],
                (long)anglemod(cl.viewangles[YAW]),(long)cl.viewangles[PITCH]);
        else {
            heading=compass_heading();
            snprintf(second,sizeof(second),"LOCAL XYZ: %ld %ld %ld %s %03ld P:%ld",(long)p[0],(long)p[1],(long)p[2],
                directions[((heading+22)/45)&7],(long)heading,(long)cl.viewangles[PITCH]);
        }
        /* The original cell goes on the end of the shorter row: same two rows. */
        place_cell(line,second,sizeof(line),p,(vid.width-96)/4);
        /* Noclip, fly and god mode while active (owner request). */
        place_cheats(line,second,sizeof(line),(vid.width-96)/4);
        coordinate_line(line,vid.height-16);
        coordinate_line(second,vid.height-8);
        /* This strip is outside scr_vrect; the normal viewport-only update
         * would leave its old pixels on the Amiga screen. */
        scr_copyeverything=1;
    } else if(!AW_PhotoModeActive())AW_SmallString(92,vid.height-8,"WASD / F10 console");
}
void Sbar_IntermissionOverlay(void) {}
void Sbar_FinaleOverlay(void) {}
void Sbar_DeathmatchOverlay(void) {}
