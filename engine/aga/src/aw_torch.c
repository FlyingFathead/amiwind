/* SPDX-License-Identifier: GPL-2.0-or-later
 * Temporary carried torch: one bounded, monochrome software dynamic light and
 * original palette art. No inventory item, fuel, shadows or additional assets.
 */
#include "quakedef.h"
#define AW_TORCH_LIGHT (-0x415754)
extern cvar_t r_drawviewmodel, chase_active;
extern qboolean r_fov_greater_than_90;

static edict_t *torch_player(void)
{
    if(cls.state!=ca_connected || !sv.active || svs.maxclients!=1 ||
       !svs.clients || !svs.clients[0].edict || cl.intermission || AW_GalleryActive())return NULL;
    if(svs.clients[0].edict->v.health<=0)return NULL;
    return svs.clients[0].edict;
}
static int hand_state(edict_t *p)
{
    eval_t *v=GetEdictFieldValue(p,"aw_hand_goal");
    if(!v || v->_float!=1)return 0;
    v=GetEdictFieldValue(p,"aw_hand_state");
    return v && (v->_float==1 || v->_float==2)?(int)v->_float:0;
}
static int active(void)
{
    edict_t *p=torch_player();eval_t *v;
    if(!p || hand_state(p)!=2)return 0;
    v=GetEdictFieldValue(p,"aw_torch");
    return v && v->_float==1;
}
static void extinguish(void)
{
    int i;
    for(i=0;i<MAX_DLIGHTS;i++)if(cl_dlights[i].key==AW_TORCH_LIGHT){
        cl_dlights[i].radius=0;cl_dlights[i].die=-1;
    }
}
static void toggle(void)
{
    edict_t *p=torch_player();eval_t *v;
    if(!p || sv.paused || cl.paused || AW_IntroImpulse(202)!=202 ||
       (key_dest!=key_game && key_dest!=key_console))return;
    if(!hand_state(p)){
        Con_Printf("Raise hands with F before equipping the torch.\n");return;
    }
    v=GetEdictFieldValue(p,"aw_torch");
    if(!v){Con_Printf("Torch requires matching AmiWind game rules.\n");return;}
    v->_float=v->_float==1?0:1;
    if(!v->_float)extinguish();
    Con_Printf("Torch %s.\n",v->_float?"on":"off");
}
void AW_TorchInit(void){Cmd_AddCommand("aw_torch",toggle);}
static int phase(void)
{
    if(!isfinite(cl.time) || cl.time<0)return 0;
    return (int)floor(fmod(cl.time,1.0)*8);
}
void AW_TorchUpdate(void)
{
    static const float radius[8]={144,147,142,146,143,148,144,141};
    dlight_t *light;
    if(!active()){extinguish();return;}
    light=CL_AllocDlight(AW_TORCH_LIGHT);
    /* Eye position stays inside the player's clear view volume. Offsetting a
     * point light toward a drawn hand could put it through a nearby wall. */
    VectorCopy(r_refdef.vieworg,light->origin);
    light->radius=radius[phase()];light->minlight=16;
    light->die=cl.time+.1;light->decay=0;
}
static void pixel(int x,int y,int scale,byte color)
{
    int xx,yy;
    for(yy=y;yy<y+scale;yy++){
        if(yy<0 || yy>=vid.height || yy<r_refdef.vrect.y ||
           yy>=r_refdef.vrect.y+r_refdef.vrect.height)continue;
        for(xx=x;xx<x+scale;xx++){
            if(xx<0 || xx>=vid.width || xx<r_refdef.vrect.x ||
               xx>=r_refdef.vrect.x+r_refdef.vrect.width)continue;
            vid.buffer[yy*vid.rowbytes+xx]=color;
        }
    }
}
void AW_TorchDraw(void)
{
    static byte colors[8],*palette;
    static const unsigned char rgb[8][3]={
        {48,27,13},{103,57,24},{159,103,47},{180,41,6},
        {240,97,10},{255,191,37},{255,235,156},{117,88,47}};
    static const char *flame[]={
        "         4", "        44", "        45", "       445",
        "       454", "      4554", "   4  4564", "   44 45654",
        "   45445654", "   45456654", "  345456654", "  3454566554",
        "  3445566554", "  3455666654", " 345556666654", " 345566666654",
        " 3456666666554", " 3456666666554", " 3455666666554", " 344566666554",
        "  34556666554", "  34456665554", "   345555554", "    3444443",
        "     33333", "      333"};
    int i,j,d,best,score,dr,dg,db,scale,left,top,x,y,base,sway;
    if(!active() || !vid.buffer || !host_basepal || !r_drawviewmodel.value ||
       chase_active.value || r_fov_greater_than_90 || (cl.items&IT_INVISIBILITY))return;
    if(palette!=host_basepal){
        palette=host_basepal;
        for(i=0;i<8;i++){
            best=0;score=0x7fffffff;
            for(j=0;j<255;j++){
                dr=palette[j*3]-rgb[i][0];dg=palette[j*3+1]-rgb[i][1];db=palette[j*3+2]-rgb[i][2];
                d=dr*dr+dg*dg+db*db;if(d<score){score=d;best=j;}
            }
            colors[i]=best;
        }
    }
    scale=r_refdef.vrect.width>=640?2:1;
    left=r_refdef.vrect.x+r_refdef.vrect.width*3/4-8*scale;
    top=r_refdef.vrect.y+r_refdef.vrect.height-85*scale;
    /* A tapered wooden shaft and wrapped head sit in front of the raised hand. */
    for(y=25;y<96;y++){
        base=5+(y-25)/14;
        for(x=0;x<7;x++)pixel(left+(base+x)*scale,top+y*scale,scale,
            colors[x==0 || x==6?0:y<35?(y%4==0?0:7):x<3?2:1]);
    }
    sway=(phase()%3)-1;
    for(y=0;y<26;y++)for(x=0;flame[y][x];x++){
        i=flame[y][x]-'0';if(i<3 || i>6)continue;
        pixel(left+(x+(y<14?sway:0))*scale,top+y*scale,scale,colors[i]);
    }
}
