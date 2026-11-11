/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "aw_maps.h"
#include "aw_world.h"
#include <assert.h>
static int opens,missing_map,broken_names,old_names,no_directory;
void Con_Printf(char *fmt,...){}
static void word(FILE *f,unsigned n){int i;for(i=0;i<4;i++)fputc((n>>(8*i))&255,f);}
static void number(FILE *f,float value){unsigned n;memcpy(&n,&value,4);word(f,n);}
int COM_FOpenFile(char *name,FILE **out){
    if(!strcmp(name,"world/regions-sl.awr")){*out=NULL;return -1;}   /* no Solstheim rows on this disk */
    FILE *f=tmpfile();int i,k;float towns[2][7]={{0,0,0,-200,-200,200,200},{4096,0,0,-200,-200,200,200}};
    float rows[2][11]={{1024,0,512,-1024,-1024,1024,1024,-1920,-1920,1920,1920},
                       {3072,0,768,-1024,-1024,1024,1024,-1920,-1920,1920,1920}};
    opens++;assert(f);*out=f;
    if(!strcmp(name,"world/regions.awr") && no_directory){fclose(f);*out=NULL;return -1;}   /* a MiniWind disk */
    if(!strcmp(name,"world/regions.awr")){
        fputs("AWR2",f);word(f,2);
        for(i=0;i<2;i++)for(k=0;k<7;k++)number(f,towns[i][k]);
        for(i=0;i<2;i++){
            char id[8]={0};sprintf(id,"vf%04d",i);fwrite(id,1,8,f);
            for(k=0;k<11;k++)number(f,rows[i][k]);
        }
        rewind(f);return 168;
    }
    if(!strcmp(name,"world/region-names.awn")){
        char labels[128]={0},places[64]={0};
        /* A packed file has a nonzero member offset. Names deliberately differ
         * from any town name; negative cells must use floor, not truncation. */
        for(i=0;i<137;i++)fputc(0,f);
        strcpy(labels,"Western test region");strcpy(labels+64,"Eastern test region");
        if(old_names){
            fputs(broken_names?"BAD!":"ARN1",f);word(f,2);word(f,3);fwrite(labels,1,128,f);
            word(f,(unsigned)-1);word(f,0);word(f,0);
            word(f,0);word(f,0);word(f,1);
            word(f,1);word(f,0);word(f,1);
            fseek(f,137,SEEK_SET);return 176;
        }
        /* ARN2: cell 0 is a named place in the eastern region; cell 3 has a
         * place but no region. */
        strcpy(places,"Test Town");
        fputs(broken_names?"BAD!":"ARN2",f);word(f,2);word(f,1);word(f,4);fwrite(labels,1,128,f);fwrite(places,1,64,f);
        word(f,(unsigned)-1);word(f,0);word(f,0);word(f,(unsigned)-1);
        word(f,0);word(f,0);word(f,1);word(f,0);
        word(f,1);word(f,0);word(f,1);word(f,(unsigned)-1);
        word(f,3);word(f,0);word(f,(unsigned)-1);word(f,0);
        fseek(f,137,SEEK_SET);return 16+128+64+4*16;
    }
    assert(!strncmp(name,"maps/",5));if(missing_map){fclose(f);*out=NULL;return -1;}rewind(f);return 124;
}
/* aw_region.c AW_SceneMapSize: the scene's own map (no CHIM frame maps in this test). */
int AW_SceneMapSize(const char *n,char *p,int s){char b[64];FILE *f=NULL;int k;sprintf(b,"maps/%s.bsp",n);k=COM_FOpenFile(b,&f);if(f)fclose(f);else k=-1;if(p && s>0){strncpy(p,b,s-1);p[s-1]=0;}return k;}
/* CHIM-FRAME-SOURCE-CONVERSION-59: a stand-in for the loaded CHIM frame (chim_world.c FrameSource / FrameLocal /
 * FrameContains): frame map FRAME_NAME, centre (-8000, 12000), chunk grid -512..512; answers for that map only. */
extern int (*aw_world_chim_source)(const char *,const float *,float *);   /* aw_world.c (chim/chim.h) */
extern int (*aw_world_chim_local)(const char *,const float *,float *);
extern int (*aw_world_chim_contains)(const char *,const float *);
static const char *frame_name="seyda_chim";static int frame_calls;
static int frame_source(const char *n,const float *l,float *w){
    frame_calls++;if(!n || strcmp(n,frame_name))return 0;
    w[0]=l[0]*4-8000;w[1]=l[1]*4+12000;w[2]=l[2]*4;return 1;}
static int frame_local(const char *n,const float *w,float *l){
    frame_calls++;if(!n || strcmp(n,frame_name))return 0;
    l[0]=(w[0]+8000)*.25f;l[1]=(w[1]-12000)*.25f;l[2]=w[2]*.25f;return 1;}
static int frame_contains(const char *n,const float *l){
    frame_calls++;return n && !strcmp(n,frame_name) && fabs(l[0])<488 && fabs(l[1])<488;}
/* Region maps and a town's handoff row answer exactly as with the region table alone, the frame is never asked for
 * them; a frame map converts both ways through the frame; a room map is a room either way. The script host's
 * room-or-outdoor decision at map load (aw_mwhost.c attach_map: AW_SourceToWorld(sv.name, 0 0 0), then
 * AW_WorldContains for every outdoor placement) is checked here with its own calls. */
static void frame_maps(void){
    float l[3]={100,-50,20},w[3],r[3],back[3],zero[3]={0,0,0},at[3],out[3]={600,0,0};
    const char *region[]={"vf0000","vf0001","seyda","balmora","vivec_arena"};int i;
    aw_world_chim_source=NULL;aw_world_chim_local=NULL;aw_world_chim_contains=NULL;
    for(i=0;i<5;i++){
        float w0[3],l0[3];int s0,t0,c0,s1,t1,c1;
        s0=AW_WorldToSource(region[i],l,w0);t0=AW_SourceToWorld(region[i],w0,l0);c0=AW_WorldContains(region[i],l);
        assert(s0==AW_RegionWorldToSource(region[i],l,r) && (!s0 || !memcmp(r,w0,sizeof r)));
        aw_world_chim_source=frame_source;aw_world_chim_local=frame_local;aw_world_chim_contains=frame_contains;
        frame_name=region[i];frame_calls=0;  /* even when the loaded frame map has that name: the region row wins */
        s1=AW_WorldToSource(region[i],l,w);t1=AW_SourceToWorld(region[i],w,back);c1=AW_WorldContains(region[i],l);
        assert(s0 && s1 && t0 && t1 && c0==c1 && !memcmp(w,w0,sizeof w) && !memcmp(back,l0,sizeof back) && !frame_calls);
        aw_world_chim_source=NULL;aw_world_chim_local=NULL;aw_world_chim_contains=NULL;
    }
    frame_name="seyda_chim";
    /* no frame hooks (a legacy disk): a frame map is not known, a room stays a room */
    assert(!AW_WorldToSource("seyda_chim",l,w) && !AW_SourceToWorld("seyda_chim",zero,at) && !AW_WorldContains("seyda_chim",l));
    aw_world_chim_source=frame_source;aw_world_chim_local=frame_local;aw_world_chim_contains=frame_contains;
    assert(AW_WorldToSource("seyda_chim",l,w) && w[0]==400-8000 && w[1]==-200+12000 && w[2]==80);
    assert(AW_SourceToWorld("seyda_chim",w,back) && back[0]==l[0] && back[1]==l[1] && back[2]==l[2]);
    /* the script host: a frame town is outdoors, its placements inside the frame attach, outside it do not */
    assert(AW_SourceToWorld("seyda_chim",zero,at) && at[0]==2000 && at[1]==-3000);
    assert(AW_WorldContains("seyda_chim",l) && !AW_WorldContains("seyda_chim",out));
    /* a room map (no region row, not the loaded frame): still a room */
    assert(!AW_SourceToWorld("census",zero,at) && !AW_WorldToSource("census",l,w) && !AW_WorldContains("census",l));
    /* another frame map than the loaded one: not converted (aw_scene.c teleport targets) */
    assert(!AW_SourceToWorld("balmora_chim",zero,at));
    aw_world_chim_source=NULL;aw_world_chim_local=NULL;aw_world_chim_contains=NULL;
    puts("frame maps: region rows unchanged, the loaded frame both ways, rooms stay rooms");
}
/* DEBUG-TP-MINIWIND-36: a MiniWind disk (no open-world region table) with its town's CHIM frame loaded: the region
 * table answers nothing, a point inside the loaded map resolves to that map at its local X Y, one outside it, another
 * map's name or a name too long for a map does not. */
static int loaded_map_without_directory(void){
    float source[3]={-8000+400,12000-200,0},arrival[3]={1,1,1};char target[16]={0};
    no_directory=1;frame_name="seyda";
    aw_world_chim_source=frame_source;aw_world_chim_local=frame_local;aw_world_chim_contains=frame_contains;
    assert(!AW_WorldHasDirectory() && !AW_WorldMapTarget(source,target,arrival));
    assert(AW_WorldLoadedTarget("seyda",source,target,arrival) && !strcmp(target,"seyda") &&
           arrival[0]==100 && arrival[1]==-50 && arrival[2]==0);
    source[0]=-8000+3600;assert(!AW_WorldLoadedTarget("seyda",source,target,arrival));   /* outside the frame */
    source[0]=-8000+400;assert(!AW_WorldLoadedTarget("balmora",source,target,arrival));  /* not the loaded frame */
    assert(!AW_WorldLoadedTarget("a_map_name_too_long",source,target,arrival) && !AW_WorldLoadedTarget(NULL,source,target,arrival));
    source[1]=NAN;assert(!AW_WorldLoadedTarget("seyda",source,target,arrival));
    source[1]=12000-200;missing_map=1;assert(!AW_WorldLoadedTarget("seyda",source,target,arrival));missing_map=0;
    puts("no region table: dbg tp resolves inside the loaded map only");
    return 0;
}
int main(int argc,char **argv){
    float a[3]={240,0,40},b[3],c[3],source[3];char target[16];int before;
    if(argc>1 && !strcmp(argv[1],"no-directory"))return loaded_map_without_directory();
    frame_maps();
    /* with the region table on the disk the loaded map is never asked: the table answers (or refuses) as before */
    source[0]=-8000+400;source[1]=12000-200;source[2]=0;frame_name="seyda";
    aw_world_chim_source=frame_source;aw_world_chim_local=frame_local;aw_world_chim_contains=frame_contains;
    assert(AW_WorldHasDirectory() && !AW_WorldLoadedTarget("seyda",source,target,b));
    aw_world_chim_source=NULL;aw_world_chim_local=NULL;aw_world_chim_contains=NULL;frame_name="seyda_chim";
    assert(AW_MapId("vf0000")==AW_MAP_COUNT);
    /* Outdoor save IDs stay fixed when interior sections are appended. */
    /* Vvardenfell's region maps take the terrain IDs 0..4095, Solstheim's frame maps slNNNN 4096..8191
     * (WORLD-REGION-NAMES-VF-ONLY-64): the last outdoor ID and the interior base stay where they were. */
    assert(AW_MapId("vf4095")==4155 && AW_MapId("sl4095")==8251 && AW_INTERIOR_MAP_BASE==8252);
    assert(!strcmp(AW_MapName(4155),"vf4095") && !strcmp(AW_MapName(8251),"sl4095"));
    assert(AW_MapId("vf4096")==-1 && AW_MapId("sl4096")==-1 && AW_MapId("vf8191")==-1);
    assert(AW_MapId("vf12")==-1 && AW_MapId("vf001x")==-1);
    assert(!strcmp(AW_MapName(AW_MAP_COUNT+1),"vf0001"));
    assert(AW_WorldDestination("seyda",a,target,b));
    assert(!strcmp(target,"vf0000") && b[0]==-784 && b[2]==-472);
    assert(AW_WorldToSource(target,b,source));
    assert(source[0]==960 && source[2]==160);
    before=opens;assert(!AW_WorldDestination(target,b,target,c));assert(opens==before);
    b[0]=1100;assert(AW_WorldDestination("vf0000",b,target,c));
    assert(!strcmp(target,"vf0001") && c[0]==-948 && c[2]==-728);
    assert(AW_WorldToSource(target,c,source) && source[0]==8496 && source[2]==160);
    c[0]=-1100;assert(AW_WorldDestination("vf0001",c,target,b));
    assert(!strcmp(target,"vf0000") && b[0]==948 && b[2]==-472);
    b[0]=-850;assert(AW_WorldDestination("vf0000",b,target,c));
    assert(!strcmp(target,"seyda") && c[0]==174 && c[2]==40);
    a[0]=-240;assert(AW_WorldDestination("balmora",a,target,b));
    assert(!strcmp(target,"vf0001") && b[0]==784 && b[2]==-728);
    b[0]=850;assert(AW_WorldDestination("vf0001",b,target,c));
    assert(!strcmp(target,"balmora") && c[0]==-174 && c[2]==40);
    assert(!AW_WorldDestination("census",a,target,b));
    assert(AW_WorldContains("vf0000",a));a[0]=1900;assert(!AW_WorldContains("vf0000",a));
    a[0]=NAN;assert(!AW_WorldDestination("vf0000",a,target,b));
    source[0]=4000;source[1]=0;source[2]=NAN;
    assert(AW_WorldMapTarget(source,target,b) && !strcmp(target,"vf0000") && b[0]==-24 && b[2]==0);
    source[0]=0;assert(AW_WorldMapTarget(source,target,b) && !strcmp(target,"seyda"));
    source[0]=16384;assert(AW_WorldMapTarget(source,target,b) && !strcmp(target,"balmora"));
    source[0]=200000;assert(!AW_WorldMapTarget(source,target,b));
    source[0]=0;missing_map=1;assert(!AW_WorldMapTarget(source,target,b));missing_map=0;
    source[0]=NAN;assert(!AW_WorldMapTarget(source,target,b));
    source[0]=-0.01f;assert(!strcmp(AW_RegionNameAt(source),"Western test region"));
    before=opens;source[0]=-8192;assert(AW_RegionNameAt(source) && before==opens);
    source[0]=0;assert(!strcmp(AW_RegionNameAt(source),"Eastern test region / Test Town"));
    before=opens;source[0]=8191;assert(AW_RegionNameAt(source) && opens==before);
    source[0]=8192;assert(AW_RegionNameAt(source) && opens==before+1);
    source[0]=16384;assert(!AW_RegionNameAt(source));
    source[0]=3*8192;assert(!strcmp(AW_RegionNameAt(source),"Test Town"));
    source[0]=4*8192;assert(!AW_RegionNameAt(source));
    old_names=1;source[0]=0;assert(!strcmp(AW_RegionNameAt(source),"Eastern test region"));
    source[0]=3*8192;assert(!AW_RegionNameAt(source));old_names=0;
    broken_names=1;source[0]=-1;assert(!AW_RegionNameAt(source));
    source[0]=NAN;assert(!AW_RegionNameAt(source));
    /* A table town without a world directory slot (the Arena) hands off by
     * its own frame once its alias map is installed. */
    source[0]=36352;source[1]=-87040;source[2]=0;
    assert(AW_WorldMapTarget(source,target,b) && !strcmp(target,"vivec_arena") && b[0]==0 && b[1]==0);
    a[0]=1000;a[1]=-500;a[2]=40;assert(AW_WorldToSource("vivec_arena",a,source));
    assert(source[0]==40352 && source[1]==-89040 && source[2]==160);
    a[0]=1400;assert(!AW_WorldDestination("vivec_arena",a,target,b));
    /* Neighbouring canton frames: leaving the Arena's core lands in the
     * Telvanni frame directly; from Redoran, the Arena's core comes first
     * (earlier in table order). Arrivals keep the shared world position. */
    a[0]=1500;assert(AW_WorldDestination("vivec_arena",a,target,b));
    assert(!strcmp(target,"vivec_telvanni") && b[0]==-676 && b[1]==-1140 && b[2]==40);
    a[0]=1100;a[1]=0;assert(AW_WorldDestination("vivec_redoran",a,target,b));
    assert(!strcmp(target,"vivec_arena") && b[0]==-820 && b[1]==256 && b[2]==40);
    /* Outside every canton core: the whole-city frame (vivec_city, wide coordinates) holds it when its map is
     * installed (every map is in this test); the arrival keeps the shared world position. */
    a[0]=1500;a[1]=-1500;assert(AW_WorldDestination("vivec_arena",a,target,b));
    assert(!strcmp(target,"vivec_city") && b[0]==2396 && b[1]==-220 && b[2]==40);
    return 0;
}
