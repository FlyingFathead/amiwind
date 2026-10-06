/* SPDX-License-Identifier: GPL-2.0-or-later
 * Real distant-LAND rasterizer versus an independent ray/plane oracle. */
#include "quakedef.h"
#include "aw_sky.h"
#include "aw_horizon.h"
#include <assert.h>
#include <stdarg.h>
client_state_t cl;
viddef_t vid;refdef_t r_refdef;short *d_pzbuffer;unsigned int d_zwidth;
vec3_t vpn,vright,vup,r_origin;
float xcenter,ycenter,xscale,yscale;
static byte screen[80*60];static short depth[80*60];
static model_t world;static msurface_t surfaces[2];static mplane_t planes[2];
static mvertex_t vertices[8];static medge_t edges[8];static int surfedges[8];
static texture_t texture;static mtexinfo_t texinfo;
static char report[512];
void Con_Printf(char *fmt,...){va_list ap;va_start(ap,fmt);vsnprintf(report,sizeof report,fmt,ap);va_end(ap);}
#ifdef HORIZON_FOG_TEST
server_t sv;
cvar_t aw_drawdistance={"aw_drawdistance","540",0,0,540};
static cvar_t *horizon_switch,*fog_switch;
static byte fog_colours[4096];static int inside;
int AW_Interior(void){return inside;}
void Cvar_RegisterVariable(cvar_t *v){v->value=atof(v->string);if(!strcmp(v->name,"aw_terrain_horizon"))horizon_switch=v;if(!strcmp(v->name,"aw_fog"))fog_switch=v;}
void Cvar_SetValue(char *name,float value){aw_drawdistance.value=value;}
void Cmd_AddCommand(char *name,void (*fn)(void)){}
int Cmd_Argc(void){return 1;}char *Cmd_Argv(int n){return "";}
byte *COM_LoadHunkFile(char *name){return fog_colours;}
const byte *R_DayNightFogColours(void){return NULL;}
byte R_DayNightSkyPixel(byte c,float x,float y,float z,int fog){return c;}
#endif
typedef struct {float xmin,xmax,ymin,ymax,a,b,c;} patch_t;
static patch_t patches[2];static int count;
static void scene(const patch_t *p,int n) {
    int i,j;float len;memset(&world,0,sizeof world);memset(surfaces,0,sizeof surfaces);
    memset(&texture,0,sizeof texture);strcpy(texture.name,"g94");texinfo.texture=&texture;
    for(i=0;i<n;i++){
        patches[i]=p[i];planes[i].normal[0]=-p[i].a;planes[i].normal[1]=-p[i].b;planes[i].normal[2]=1;
        len=(float)sqrt(p[i].a*p[i].a+p[i].b*p[i].b+1);
        for(j=0;j<3;j++)planes[i].normal[j]/=len;planes[i].dist=p[i].c/len;
        surfaces[i].plane=&planes[i];surfaces[i].texinfo=&texinfo;
        surfaces[i].firstedge=i*4;surfaces[i].numedges=4;
        for(j=0;j<4;j++){
            float *v=vertices[i*4+j].position;v[0]=(j==0||j==3)?p[i].xmin:p[i].xmax;
            v[1]=j<2?p[i].ymin:p[i].ymax;v[2]=p[i].a*v[0]+p[i].b*v[1]+p[i].c;
            edges[i*4+j].v[0]=i*4+j;edges[i*4+j].v[1]=i*4+(j+1)%4;surfedges[i*4+j]=i*4+j;
        }
    }
    world.type=mod_brush;world.surfaces=surfaces;world.vertexes=vertices;world.edges=edges;world.surfedges=surfedges;
    world.nummodelsurfaces=world.numsurfaces=n;world.numvertexes=world.numedges=world.numsurfedges=n*4;
    cl.worldmodel=&world;count=n;
}
static void reset(void){int i;for(i=0;i<80*60;i++){screen[i]=77;depth[i]=AW_SKY_BACKGROUND_DEPTH;}}
static double reference(int x,int y,int distance) {
    double ray[3],u=(x-xcenter)/xscale,v=(ycenter-y)/yscale,t,denom,best=1e30,wx,wy;int i,j;
    for(j=0;j<3;j++)ray[j]=vpn[j]+u*vright[j]+v*vup[j];
    for(i=0;i<count;i++){
        patch_t *p=&patches[i];denom=ray[2]-p->a*ray[0]-p->b*ray[1];
        if(denom>=-1e-8)continue;
        t=(p->a*r_origin[0]+p->b*r_origin[1]+p->c-r_origin[2])/denom;
        if(t<distance)continue;
        wx=r_origin[0]+ray[0]*t;wy=r_origin[1]+ray[1]*t;
        if(wx>=p->xmin && wx<p->xmax && wy>=p->ymin && wy<p->ymax && t<best)best=t;
    }
    return best;
}
static int compare(int distance) {
    int x,y,index,seen=0,expected;double t;
    reset();AW_HorizonDraw(201,distance);
    for(y=0;y<60;y++)for(x=0;x<80;x++){
        index=y*80+x;
        t=(x>=3&&x<67&&y>=5&&y<53)?reference(x,y,distance):1e30;
        expected=t<1e29;
        if((screen[index]==201)!=expected){fprintf(stderr,"coverage mismatch %d,%d expected%d got%d t%g\n",x,y,expected,screen[index],t);abort();}
        if(expected){seen++;assert(abs(depth[index]-(int)(32768.0/t))<=1);}
        else assert(depth[index]==AW_SKY_BACKGROUND_DEPTH);
    }
    return seen;
}
int main(void) {
    patch_t plane={210,1200,-780,810,0,0,-81};
    patch_t valley[2]={{210,1200,-810,-73,0,0,-81},{210,1200,93,810,0,0,-81}};
    vec3_t angles={0,0,0};int i,j,n,index,seen;double t;
    vid.width=80;vid.height=60;vid.rowbytes=80;vid.buffer=screen;d_pzbuffer=depth;d_zwidth=80;
    r_refdef.vrect.x=3;r_refdef.vrect.y=5;r_refdef.vrect.width=64;r_refdef.vrect.height=48;
    xcenter=34.5f;ycenter=28.5f;xscale=yscale=32;
    for(i=0;i<5;i++){
        angles[0]=(i-2)*9;angles[1]=(i-2)*7;angles[2]=(i-2)*5;AngleVectors(angles,vpn,vright,vup);
        xscale=32+i*3;yscale=30+i*2;r_origin[0]=19;r_origin[1]=-11;r_origin[2]=7;
        scene(&plane,1);compare(128);compare(540);
        plane.a=.12f;plane.b=-.035f;scene(&plane,1);compare(128);compare(540);plane.a=plane.b=0;
        scene(valley,2);compare(128);compare(540);
    }
    angles[0]=angles[1]=angles[2]=0;AngleVectors(angles,vpn,vright,vup);xscale=yscale=32;
    scene(&plane,1);seen=compare(540);assert(seen>0);
    /* Existing foreground, including water and opaque scenery, must win. */
    for(i=0;i<80*60;i++)if(screen[i]==201){screen[i]=33;depth[i]=300;}
    AW_HorizonDraw(202,540);for(i=0;i<80*60;i++)assert(screen[i]!=202);
    /* Nearer horizon polygons win regardless of submission order. */
    valley[0]=plane;valley[1]=plane;valley[1].c=-89;scene(valley,2);compare(540);
    /* A shared-edge triangle pair must match the unsplit convex polygon. */
    scene(&plane,1);compare(540);
    surfaces[1]=surfaces[0];surfaces[0].numedges=surfaces[1].numedges=3;
    surfaces[1].firstedge=3;world.nummodelsurfaces=world.numsurfaces=2;
    world.numedges=world.numsurfedges=6;
    {const int ids[6]={0,1,2,0,2,3};for(i=0;i<6;i++){
        edges[i].v[0]=ids[i];edges[i].v[1]=ids[(i/3)*3+(i+1)%3];surfedges[i]=i;
    }}
    compare(540);
    /* Material, closure, budget and malformed-geometry gates fail closed. */
    scene(&plane,1);strcpy(texture.name,"*water");reset();AW_HorizonDraw(201,540);
    for(i=0;i<80*60;i++)assert(screen[i]==77);
    strcpy(texture.name,"g94roof");AW_HorizonDraw(201,540);for(i=0;i<80*60;i++)assert(screen[i]==77);
    strcpy(texture.name,"g94");planes[0].normal[2]=-1;AW_HorizonDraw(201,540);for(i=0;i<80*60;i++)assert(screen[i]==77);
    scene(&plane,1);surfaces[0].numedges=65;AW_HorizonDraw(201,540);AW_HorizonReport();assert(strstr(report,"rejected 1"));
    scene(&plane,1);surfedges[0]=-2147483647-1;AW_HorizonDraw(201,540);for(i=0;i<80*60;i++)assert(screen[i]==77);
    scene(&plane,1);vertices[0].position[0]=NAN;AW_HorizonDraw(201,540);for(i=0;i<80*60;i++)assert(screen[i]==77);
    scene(&plane,1);world.numedges=-2147483647-1;AW_HorizonDraw(201,540);for(i=0;i<80*60;i++)assert(screen[i]==77);
    scene(&plane,1);world.numsurfedges=-2147483647-1;AW_HorizonDraw(201,540);for(i=0;i<80*60;i++)assert(screen[i]==77);
    scene(&plane,1);world.numsurfaces=-2147483647-1;AW_HorizonDraw(201,540);for(i=0;i<80*60;i++)assert(screen[i]==77);
    scene(&plane,1);world.nummodelsurfaces=world.numsurfaces=8193;AW_HorizonDraw(201,540);AW_HorizonReport();assert(strstr(report,"limit 1"));
#ifdef HORIZON_FOG_TEST
    scene(&plane,1);memset(fog_colours,173,sizeof fog_colours);AW_FogInit();assert(horizon_switch && horizon_switch->value==0);
    reset();AW_FogDraw();for(i=0;i<80*60;i++)assert(screen[i]==77 && depth[i]==AW_SKY_BACKGROUND_DEPTH);
    horizon_switch->value=1;AW_FogDraw();seen=0;for(i=0;i<80*60;i++)if(screen[i]==173)seen++;assert(seen>0);
    reset();inside=1;AW_FogDraw();for(i=0;i<80*60;i++)assert(screen[i]==77 && depth[i]==AW_SKY_BACKGROUND_DEPTH);inside=0;
    fog_switch->value=0;AW_FogDraw();for(i=0;i<80*60;i++)assert(screen[i]==77 && depth[i]==AW_SKY_BACKGROUND_DEPTH);
    fog_switch->value=1;horizon_switch->value=0;AW_FogDraw();for(i=0;i<80*60;i++)assert(screen[i]==77 && depth[i]==AW_SKY_BACKGROUND_DEPTH);
    puts("fog integration: opt-in paints ground; default/rollback, interiors and disabled fog preserve original pixels and depth");
#endif
    puts("resident LAND: 30 independent ray/plane camera cases; valleys, depth, water/material, closure and bounds gates passed");
    return 0;
}
