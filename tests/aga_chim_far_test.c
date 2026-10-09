/* SPDX-License-Identifier: GPL-2.0-or-later
 * CHIM far terrain (CHIM-FAR-TERRAIN-33): the grid rasterizer (aw_horizon.c
 * AW_HorizonGrid) against an independent ray/plane oracle, and the sidecar
 * loader (chim/chim_far.c) on files the builder's writer (tools/chim/far.py)
 * made, run in their folder.
 *
 *   grid    planar and valley heightfields: coverage and depth equal the
 *           oracle; block culling draws exactly what no culling draws; the
 *           reach limit; nearer foreground and its depth always win;
 *           invalid grids draw nothing; a view from below draws nothing
 *   load    maps/far-ok.far loads (header, heights, bounds, local origin),
 *           draws through the fog hook, frees at map end; damaged, foreign
 *           frame and missing files are refused and draw nothing
 *   floor   the terrain floor (CHIM-GRAFT-REPACK-EMPTY-33, second layer):
 *           the chunk terrain's triangles through the samples, the lowest
 *           corner less 64 on land, the chunk's (else the frame's) lowest
 *           terrain point less 64 on water; nothing outside the layer, when
 *           off, on a legacy map, with object stamps applied or after the map
 */
#include "quakedef.h"
#include "aw_sky.h"
#include "aw_horizon.h"
#include "chim/chim_local.h"
#include <assert.h>
#include <stdarg.h>

client_state_t cl;server_t sv;quakeparms_t host_parms;
viddef_t vid;refdef_t r_refdef;short *d_pzbuffer;unsigned int d_zwidth;
vec3_t vpn,vright,vup,r_origin;
float xcenter,ycenter,xscale,yscale;
chim_frame_state_t chim_frame;
cvar_t chim_debug={"chim_debug","0"};
void (*aw_chim_far_draw)(byte colour,int distance);
int (*aw_chim_floor)(const vec3_t origin,float *lowest,float *surface);
static int cell_entry=-1;
int ChimChunks_CellEntry(int x,int y){(void)x;(void)y;return cell_entry;}
#define W 96
#define H 72
static byte screen[W*H],saved[W*H];static short depth[W*H],saved_depth[W*H];
static char console[2048];
void Con_Printf(char *fmt,...){va_list ap;size_t n=strlen(console);va_start(ap,fmt);vsnprintf(console+n,sizeof console-n,fmt,ap);va_end(ap);}
void Cvar_RegisterVariable(cvar_t *v){v->value=(float)atof(v->string);}
double Sys_FloatTime(void){return 0;}
static int chim_on=1;
int Chim_Active(void){return chim_on;}
static byte hunk[1<<20];static int hunk_used;
void *Hunk_AllocName(int size,char *name){void *p=hunk+hunk_used;(void)name;hunk_used+=(size+15)&~15;assert(hunk_used<=(int)sizeof hunk);return p;}
int Hunk_LowMark(void){return hunk_used;}
void Hunk_FreeToLowMark(int mark){assert(mark>=0 && mark<=hunk_used);hunk_used=mark;}
int COM_FOpenFile(char *name,FILE **file){
    long size;*file=fopen(name,"rb");if(!*file)return -1;
    fseek(*file,0,SEEK_END);size=ftell(*file);fseek(*file,0,SEEK_SET);return (int)size;
}

static void reset(void){int i;for(i=0;i<W*H;i++){screen[i]=77;depth[i]=AW_SKY_BACKGROUND_DEPTH;}}
static void view(float pitch,float yaw,float roll,float ox,float oy,float oz){
    vec3_t a;a[0]=pitch;a[1]=yaw;a[2]=roll;AngleVectors(a,vpn,vright,vup);
    r_origin[0]=ox;r_origin[1]=oy;r_origin[2]=oz;
}

/* The oracle: a heightfield made of planes z = a x + b y + c over boxes. */
typedef struct {float xmin,xmax,ymin,ymax,a,b,c;} patch_t;
static patch_t patches[2];static int count;
static double reference(int x,int y,double distance,double reach){
    double ray[3],u=(x-xcenter)/xscale,v=(ycenter-y)/yscale,t,denom,best=1e30,wx,wy;int i,j;
    for(j=0;j<3;j++)ray[j]=vpn[j]+u*vright[j]+v*vup[j];
    for(i=0;i<count;i++){
        patch_t *p=&patches[i];denom=ray[2]-p->a*ray[0]-p->b*ray[1];
        if(denom>=-1e-8)continue;           /* the ray meets the plane's top only going down through it */
        t=(p->a*r_origin[0]+p->b*r_origin[1]+p->c-r_origin[2])/denom;
        if(t<distance || (reach>0 && t>reach))continue;
        wx=r_origin[0]+ray[0]*t;wy=r_origin[1]+ray[1]*t;
        if(wx>=p->xmin && wx<p->xmax && wy>=p->ymin && wy<p->ymax && t<best)best=t;
    }
    return best;
}

#define NX 33
#define NY 25
static short heights[NX*NY];
static aw_horizon_grid_t g;
static void plane_grid(float a,float b,float c,int valley){
    int i,j;float x,y;
    g.heights=heights;g.bounds=NULL;g.nx=NX;g.ny=NY;g.block=4;g.x0=-512;g.y0=-384;g.step=64;g.reach=0;
    for(j=0;j<NY;j++)for(i=0;i<NX;i++){
        x=g.x0+i*g.step;y=g.y0+j*g.step;
        heights[j*NX+i]=(short)(valley?a*fabs(x-64)+c:a*x+b*y+c);
    }
    if(valley){
        patch_t l={-512,64,-384,1152,-a,0,c+64*a},r={64,1536,-384,1152,a,0,c-64*a};
        patches[0]=l;patches[1]=r;count=2;
    }else{patch_t p={-512,1536,-384,1152,a,b,c};patches[0]=p;count=1;}
}
static int compare(int distance){
    int x,y,i,seen=0,expected;double t;
    reset();AW_HorizonGrid(&g,201,distance,1);
    for(y=0;y<H;y++)for(x=0;x<W;x++){
        i=y*W+x;
        t=(x>=4&&x<84&&y>=6&&y<66)?reference(x,y,distance,g.reach):1e30;
        expected=t<1e29;
        if((screen[i]==201)!=expected){fprintf(stderr,"coverage %d,%d expected %d got %d t %g\n",x,y,expected,screen[i],t);abort();}
        if(expected){seen++;if(abs(depth[i]-(int)(32768.0/t))>1){fprintf(stderr,"depth %d,%d %d vs %g\n",x,y,depth[i],32768.0/t);abort();}}
        else assert(depth[i]==AW_SKY_BACKGROUND_DEPTH);
    }
    /* Culling only skips work: no culling draws the same pixels and depths. */
    memcpy(saved,screen,sizeof screen);memcpy(saved_depth,depth,sizeof depth);
    reset();AW_HorizonGrid(&g,201,distance,0);
    assert(!memcmp(saved,screen,sizeof screen) && !memcmp(saved_depth,depth,sizeof depth));
    return seen;
}

static void grid_mode(void){
    int i,k,seen=0,cases=0;long n[9];
    vid.width=W;vid.height=H;vid.rowbytes=W;vid.buffer=screen;d_pzbuffer=depth;d_zwidth=W;
    r_refdef.vrect.x=4;r_refdef.vrect.y=6;r_refdef.vrect.width=80;r_refdef.vrect.height=60;
    xcenter=43.5f;ycenter=35.5f;xscale=yscale=40;
    for(k=0;k<3;k++)for(i=0;i<6;i++){
        view((float)(4+i*3),(float)(i*61%360)-180,(float)((i%3)-1)*3,(float)(-200+i*37),(float)(-60+i*13),(float)(90+i*11));
        xscale=40+i*2;yscale=38+i;
        if(k==0)plane_grid(0,0,-20,0);
        else if(k==1)plane_grid(.125f,-.0625f,-40,0);
        else plane_grid(.25f,0,-60,1);
        seen+=compare(128);seen+=compare(300);cases+=2;
    }
    assert(seen>2000);
    /* Looking down the grid from its west edge: blocks culled for each reason. */
    view(12,0,0,-500,0,120);xscale=yscale=40;plane_grid(0,0,-20,0);
    seen=compare(300);assert(seen>0);reset();AW_HorizonGrid(&g,201,300,1);AW_HorizonGridCounts(n);
    assert(n[0]==8*6 && n[1]>0 && n[3]>0 && n[4]>0 && n[4]<n[0] && n[5]>0);
    /* The reach: nothing beyond it, and it equals the oracle with the same limit. */
    g.reach=700;seen=compare(300);assert(seen>0);reset();AW_HorizonGrid(&g,201,300,1);AW_HorizonGridCounts(n);assert(n[2]>0);
    for(i=0;i<W*H;i++)if(screen[i]==201)assert(depth[i]>=(int)(32768.0/700)-1);
    g.reach=0;
    /* Nearer foreground (a resident chunk, water, scenery) and its depth win. */
    compare(300);for(i=0;i<W*H;i++)if(screen[i]==201){screen[i]=33;depth[i]=200;}
    memcpy(saved,screen,sizeof screen);memcpy(saved_depth,depth,sizeof depth);
    AW_HorizonGrid(&g,202,300,1);
    for(i=0;i<W*H;i++)assert(screen[i]==saved[i] && depth[i]==saved_depth[i]);
    /* Precomputed bounds equal the computed ones. */
    {
        static short b[2*8*6];ChimFar_Bounds(heights,NX,NY,4,b);
        reset();AW_HorizonGrid(&g,201,300,1);memcpy(saved,screen,sizeof screen);
        g.bounds=b;reset();AW_HorizonGrid(&g,201,300,1);assert(!memcmp(saved,screen,sizeof screen));g.bounds=NULL;
    }
    /* A view from below the ground: every triangle faces away. */
    view(-20,0,0,-500,0,-200);reset();AW_HorizonGrid(&g,201,128,1);
    for(i=0;i<W*H;i++)assert(screen[i]==77);
    /* Invalid grids and views draw nothing. */
    view(12,0,0,-500,0,120);
    g.block=0;reset();AW_HorizonGrid(&g,201,300,1);for(i=0;i<W*H;i++)assert(screen[i]==77);g.block=4;
    g.block=17;reset();AW_HorizonGrid(&g,201,300,1);for(i=0;i<W*H;i++)assert(screen[i]==77);g.block=4;
    g.nx=1;reset();AW_HorizonGrid(&g,201,300,1);for(i=0;i<W*H;i++)assert(screen[i]==77);g.nx=NX;
    g.x0=NAN;reset();AW_HorizonGrid(&g,201,300,1);for(i=0;i<W*H;i++)assert(screen[i]==77);g.x0=-512;
    g.step=0;reset();AW_HorizonGrid(&g,201,300,1);for(i=0;i<W*H;i++)assert(screen[i]==77);g.step=64;
    g.reach=-1;reset();AW_HorizonGrid(&g,201,300,1);for(i=0;i<W*H;i++)assert(screen[i]==77);g.reach=0;
    reset();AW_HorizonGrid(&g,201,100,1);for(i=0;i<W*H;i++)assert(screen[i]==77);
    reset();AW_HorizonGrid(NULL,201,300,1);for(i=0;i<W*H;i++)assert(screen[i]==77);
    printf("far grid: %d camera cases equal the ray oracle; culling exact; reach, foreground, bounds, back faces, invalid grids\n",cases);
}

/* argv: expected nx ny x0 y0 step (local) and a height probe i j z */
static void load_mode(char **argv){
    int nx=atoi(argv[2]),ny=atoi(argv[3]),i,drawn=0;float x0=(float)atof(argv[4]),y0=(float)atof(argv[5]),step=(float)atof(argv[6]);
    char line[256];
    vid.width=W;vid.height=H;vid.rowbytes=W;vid.buffer=screen;d_pzbuffer=depth;d_zwidth=W;
    r_refdef.vrect.x=4;r_refdef.vrect.y=6;r_refdef.vrect.width=80;r_refdef.vrect.height=60;
    xcenter=43.5f;ycenter=35.5f;xscale=yscale=40;
    chim_frame.frame.cx=-3;chim_frame.frame.cy=-2;chim_frame.frame.centre[0]=-20480;chim_frame.frame.centre[1]=-12288;
    ChimFar_Init();ChimFar_Hook();assert(aw_chim_far_draw);
    ChimFar_Begin("maps/far-ok.bsp",1<<20);
    assert(ChimFar_Loaded());
    {
        const aw_horizon_grid_t *l=ChimFar_Layer();int pi=atoi(argv[7]),pj=atoi(argv[8]);
        assert(l && l->nx==nx && l->ny==ny && l->bounds && l->block>=1);
        assert(fabs(l->x0-x0)<.01 && fabs(l->y0-y0)<.01 && fabs(l->step-step)<.001);
        assert(l->heights[pj*nx+pi]==atoi(argv[9]));
    }
    ChimFar_Report();assert(strstr(console,"maps/far-ok.far"));
    snprintf(line,sizeof line,"%ld x %ld samples",(long)nx,(long)ny);assert(strstr(console,line));
    /* draw through the fog hook from above the layer's middle, looking along +x */
    view(10,0,0,x0+step*nx/4,y0+step*ny/2,(float)atof(argv[10])+150);
    reset();aw_chim_far_draw(201,300);
    for(i=0;i<W*H;i++)if(screen[i]==201)drawn++;
    assert(drawn>0);
    assert(ChimFar_RCount(line,sizeof line) && strstr(line," far "));
    /* chim_far 0: the first CHIM method, no far land */
    chim_far.value=0;reset();aw_chim_far_draw(201,300);for(i=0;i<W*H;i++)assert(screen[i]==77);chim_far.value=1;
    /* not a CHIM map: nothing */
    chim_on=0;reset();aw_chim_far_draw(201,300);for(i=0;i<W*H;i++)assert(screen[i]==77);chim_on=1;
    ChimFar_End();assert(!ChimFar_Loaded());reset();aw_chim_far_draw(201,300);for(i=0;i<W*H;i++)assert(screen[i]==77);
    /* refused files draw nothing */
    ChimFar_Begin("maps/far-crc.bsp",1<<20);assert(!ChimFar_Loaded());
    ChimFar_Begin("maps/far-frame.bsp",1<<20);assert(!ChimFar_Loaded());
    ChimFar_Begin("maps/far-short.bsp",1<<20);assert(!ChimFar_Loaded());
    ChimFar_Begin("maps/none.bsp",1<<20);assert(!ChimFar_Loaded());
    ChimFar_Begin("maps/far-ok.bsp",100);assert(!ChimFar_Loaded());     /* no Hunk room above the reserve */
    console[0]=0;ChimFar_Report();assert(strstr(console,"Hunk"));
    /* object stamps: raised into the grid when chim_far_objects is 1 at map start, ground only at 0 */
    {
        int si=atoi(argv[11]),sj=atoi(argv[12]),sz=atoi(argv[13]),ground=atoi(argv[14]);const aw_horizon_grid_t *l;
        int before=hunk_used;chim_far_objects.value=1;ChimFar_Begin("maps/far-obj.bsp",1<<20);l=ChimFar_Layer();assert(hunk_used-before<=((2*nx*ny+3)&~3)+4*6+16);assert(l && l->heights[sj*nx+si]==sz && l->heights[sj*nx+si+1]==sz+1);
        chim_far_objects.value=0;ChimFar_Begin("maps/far-obj.bsp",1<<20);l=ChimFar_Layer();assert(l && l->heights[sj*nx+si]==ground);
        chim_far_objects.value=0;ChimFar_End();
    }
    printf("far load: header, heights and local origin; hook draws; chim_far 0, map end and refused files draw nothing\n");
}

/* argv: nx ny of maps/far-floor.far (its water samples are 0); maps/far-obj.far has stamps */
static float tri(const aw_horizon_grid_t *l,int i,int j,double fx,double fy){
    double h00=l->heights[j*l->nx+i],h10=l->heights[j*l->nx+i+1],h01=l->heights[(j+1)*l->nx+i],h11=l->heights[(j+1)*l->nx+i+1];
    /* the plane of the tile triangle that holds the point (diagonal (0,0)-(1,1)) */
    return (float)(fx>=fy?h00+(h10-h00)*fx+(h11-h10)*fy:h00+(h01-h00)*fy+(h11-h01)*fx);
}
static void floor_mode(char **argv){
    int nx=atoi(argv[2]),ny=atoi(argv[3]),i,j,k,dry=0,wet=0,m;float lowest,surface,lo2,su2;vec3_t o;
    const aw_horizon_grid_t *l;static chim_entry_t entries[3];
    chim_frame.frame.cx=-3;chim_frame.frame.cy=-2;chim_frame.frame.centre[0]=-20480;chim_frame.frame.centre[1]=-12288;
    chim_frame.frame.low[0]=chim_frame.frame.low[1]=-4096;chim_frame.frame.grain=512;
    entries[0].disk.zmin=-50;entries[1].disk.zmin=-120;entries[2].disk.zmin=-30;chim_frame.entries=entries;chim_frame.count=3;
    ChimFar_Init();ChimFar_Hook();assert(aw_chim_floor && chim_terrain_floor.value==1);
    o[0]=o[1]=o[2]=0;assert(!aw_chim_floor(o,&lowest,&surface));          /* no layer */
    ChimFar_Begin("maps/far-floor.bsp",1<<20);assert(ChimFar_Loaded());l=ChimFar_Layer();assert(l->nx==nx && l->ny==ny);
    for(k=0;k<997;k++){
        double fx=((k*37)%101)/101.0,fy=((k*53)%97)/97.0;
        i=k%(nx-1);j=(k/(nx-1))%(ny-1);
        o[0]=(float)(l->x0+(i+fx)*l->step);o[1]=(float)(l->y0+(j+fy)*l->step);o[2]=12345;
        assert(aw_chim_floor(o,&lowest,&surface));
        assert(ChimFar_Floor(o,&lo2,&su2) && lo2==lowest && su2==surface);
        assert(fabs(surface-tri(l,i,j,fx,fy))<.01);
        m=l->heights[j*nx+i];
        if(l->heights[j*nx+i+1]<m)m=l->heights[j*nx+i+1];
        if(l->heights[(j+1)*nx+i]<m)m=l->heights[(j+1)*nx+i];
        if(l->heights[(j+1)*nx+i+1]<m)m=l->heights[(j+1)*nx+i+1];
        if(m>0){assert(lowest==m-64);dry++;}
        else{assert(lowest==-120-64);wet++;}       /* no chunk record: the frame's lowest */
    }
    assert(dry>500 && wet>10);
    /* at a sample the surface is its height */
    o[0]=l->x0+5*l->step;o[1]=l->y0+7*l->step;assert(aw_chim_floor(o,&lowest,&surface) && surface==l->heights[7*nx+5]);
    /* water (every corner at the water level): the chunk's own lowest terrain point */
    for(j=0;j<ny-1;j++){
        for(i=0;i<nx-1;i++)
            if(!l->heights[j*nx+i] && !l->heights[j*nx+i+1] && !l->heights[(j+1)*nx+i] && !l->heights[(j+1)*nx+i+1])break;
        if(i<nx-1)break;
    }
    assert(j<ny-1);
    o[0]=l->x0+(i+.5f)*l->step;o[1]=l->y0+(j+.5f)*l->step;
    cell_entry=2;assert(aw_chim_floor(o,&lowest,&surface) && lowest==-30-64 && surface==0);
    cell_entry=1;assert(aw_chim_floor(o,&lowest,&surface) && lowest==-120-64);
    cell_entry=-1;
    /* outside the layer: none */
    o[0]=l->x0-1;assert(!aw_chim_floor(o,&lowest,&surface));
    o[0]=l->x0+(nx-1)*l->step;o[1]=l->y0+l->step;assert(!aw_chim_floor(o,&lowest,&surface));
    o[0]=l->x0+l->step;o[1]=l->y0+(ny-1)*l->step+.5f;assert(!aw_chim_floor(o,&lowest,&surface));
    /* off, and not a CHIM map */
    o[0]=l->x0+2.5f*l->step;o[1]=l->y0+12.5f*l->step;assert(aw_chim_floor(o,&lowest,&surface));
    chim_terrain_floor.value=0;assert(!aw_chim_floor(o,&lowest,&surface));
    console[0]=0;ChimFar_Report();assert(strstr(console,"terrain floor (chim_terrain_floor 0): off"));chim_terrain_floor.value=1;
    console[0]=0;ChimFar_Report();assert(strstr(console,"terrain floor (chim_terrain_floor 1): on, 64 units below the layer's ground\n"));
    chim_on=0;assert(!aw_chim_floor(o,&lowest,&surface));chim_on=1;
    /* water without a chunk record or a frame table: none */
    chim_frame.count=0;ChimFar_Begin("maps/far-floor.bsp",1<<20);assert(ChimFar_Loaded());l=ChimFar_Layer();
    o[0]=l->x0+(i+.5f)*l->step;o[1]=l->y0+(j+.5f)*l->step;assert(!aw_chim_floor(o,&lowest,&surface));
    o[0]=l->x0+2.5f*l->step;o[1]=l->y0+12.5f*l->step;assert(aw_chim_floor(o,&lowest,&surface));
    /* object stamps applied (chim_far_objects 1): the heights hold object tops, no floor */
    chim_far_objects.value=1;ChimFar_Begin("maps/far-obj.bsp",1<<20);assert(ChimFar_Loaded());
    assert(!aw_chim_floor(o,&lowest,&surface));
    console[0]=0;ChimFar_Report();assert(strstr(console,"off (object stamps applied)"));
    chim_far_objects.value=0;ChimFar_Begin("maps/far-obj.bsp",1<<20);assert(aw_chim_floor(o,&lowest,&surface));
    /* the map ends: none */
    ChimFar_End();assert(!aw_chim_floor(o,&lowest,&surface));
    printf("terrain floor: %d land and %d water points; samples, chunk and frame lowest; outside, off, legacy, stamps and map end give none\n",dry,wet);
}

int main(int argc,char **argv){
    if(argc>1 && !strcmp(argv[1],"grid"))grid_mode();
    else if(argc>14 && !strcmp(argv[1],"load"))load_mode(argv);
    else if(argc>3 && !strcmp(argv[1],"floor"))floor_mode(argv);
    else return 2;
    return 0;
}
