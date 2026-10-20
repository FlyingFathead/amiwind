/* SPDX-License-Identifier: GPL-2.0-or-later
 * CHIM whole-structure cut groups (CHIM-BRIDGE-POP-PIECES-44): the sidecar
 * loader (chim/chim_cuts.c) on files the builder's writer (tools/chim/cuts.py)
 * made, run in their folder.
 *
 *   load  maps/cuts-ok.cut: every member finds its structure's box, other
 *         placements none; the map end forgets them; damaged, foreign-frame,
 *         short and missing files are refused and give no box
 */
#include "quakedef.h"
#include "chim/chim_local.h"
#include <assert.h>
#include <stdarg.h>

quakeparms_t host_parms;
chim_frame_state_t chim_frame;
cvar_t chim_debug={"chim_debug","0"};
static char console[4096];
void Con_Printf(char *fmt,...){va_list ap;size_t n=strlen(console);va_start(ap,fmt);vsnprintf(console+n,sizeof console-n,fmt,ap);va_end(ap);}
static unsigned char hunk[1<<20];static int hunk_used;
void *Hunk_AllocName(int size,char *name){void *p=hunk+hunk_used;(void)name;hunk_used+=(size+15)&~15;assert(hunk_used<=(int)sizeof hunk);memset(p,0,size);return p;}
int Hunk_LowMark(void){return hunk_used;}
void Hunk_FreeToLowMark(int mark){assert(mark>=0 && mark<=hunk_used);hunk_used=mark;}
int COM_FOpenFile(char *name,FILE **file){
    long size;*file=fopen(name,"rb");if(!*file)return -1;
    fseek(*file,0,SEEK_END);size=ftell(*file);fseek(*file,0,SEEK_SET);return (int)size;
}

/* argv: load CX CY then triples "pid structure x0" (x0: the structure box's
 * mins x) of members, then "-" and pids that are no members. */
int main(int argc,char **argv){
    int i=4,cx,cy,refused=0;const float *box;
    static const char *bad[]={"maps/cuts-crc.bsp","maps/cuts-frame.bsp","maps/cuts-short.bsp","maps/cuts-none.bsp",
        "maps/cuts-order.bsp"};
    assert(argc>=4 && !strcmp(argv[1],"load"));
    cx=atoi(argv[2]);cy=atoi(argv[3]);
    chim_frame.frame.cx=cx;chim_frame.frame.cy=cy;
    ChimCuts_Begin("maps/cuts-ok.bsp",1<<19);
    for(;i+2<argc && strcmp(argv[i],"-");i+=3){
        box=ChimCuts_Box((unsigned)strtoul(argv[i],NULL,10));
        assert(box && box[0]==(float)atof(argv[i+2]));
        assert(box[3]>=box[0] && box[4]>=box[1] && box[5]>=box[2]);
    }
    assert(i<argc && !strcmp(argv[i],"-"));
    for(i++;i<argc;i++)assert(!ChimCuts_Box((unsigned)strtoul(argv[i],NULL,10)));
    ChimCuts_Report();assert(strstr(console,"structures"));
    ChimCuts_End();assert(!ChimCuts_Box((unsigned)strtoul(argv[4],NULL,10)));
    for(i=0;i<(int)(sizeof bad/sizeof bad[0]);i++){
        int mark=Hunk_LowMark();
        ChimCuts_Begin(bad[i],1<<19);
        assert(!ChimCuts_Box((unsigned)strtoul(argv[4],NULL,10)));
        refused++;
        (void)mark;
    }
    /* no room in the Hunk: refused, nothing kept */
    ChimCuts_Begin("maps/cuts-ok.bsp",16);assert(!ChimCuts_Box((unsigned)strtoul(argv[4],NULL,10)));
    printf("cut groups load; %d refused files give no box\n",refused);
    return 0;
}
