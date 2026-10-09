/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
#include <sys/stat.h>
#include <unistd.h>
#include <strings.h>

viddef_t vid; refdef_t r_refdef; keydest_t key_dest; double realtime, host_frametime=.02;
client_static_t cls; server_t sv; server_static_t svs; int scr_copyeverything;
byte pal[768], glyphs[16384], frame[64004]; byte *host_basepal=pal, *draw_chars=glyphs;
static char *directory;
static int paper_opens,warnings,allocation_failure;
void *__real_malloc(size_t size);
void *__wrap_malloc(size_t size) { return allocation_failure?NULL:__real_malloc(size); }
int COM_FOpenFile(char *name,FILE **f) {
    char p[1024]; int n;
    if(!strcmp(name,"gfx/paper12.awf"))paper_opens++;
    assert(snprintf(p,sizeof(p),"%s/%s",directory,name)<(int)sizeof(p));
    *f=fopen(p,"rb"); if(!*f)return -1;
    assert(!fseek(*f,0,SEEK_END)); n=ftell(*f); rewind(*f); return n;
}
void Con_Printf(char *fmt,...) { warnings++; }
void Cvar_RegisterVariable(cvar_t *c) { c->value=atof(c->string); }
void Cvar_SetValue(char *s,float v) {}
void Cvar_Set(char *s,char *v) {}
void Cmd_AddCommand(char *s,void(*f)(void)) {}
char *Cmd_Argv(int i) { return ""; }
int Cmd_Argc(void) { return 0; }
int Q_strcasecmp(char *a,char *b) { return strcasecmp(a,b); }
double AW_SpeechRemaining(void) { return 0; }

static void write_asset(const char *name,const byte *raw,int size) {
    char path[1024]; FILE *f;
    assert(snprintf(path,sizeof(path),"%s/gfx/%s",directory,name)<(int)sizeof(path));
    f=fopen(path,"wb"); assert(f); assert(fwrite(raw,1,size,f)==(size_t)size); assert(!fclose(f));
}
int main(int argc,char **argv) {
    byte raw[26625],before[3],small[3];
    char temporary[]="aw-paper-XXXXXX",path[1024]; int i,valid;
    assert(argc==2); valid=!strcmp(argv[1],"valid"); allocation_failure=!strcmp(argv[1],"allocation");
    assert(mkdtemp(temporary)); directory=temporary;
    sprintf(path,"%s/gfx",directory); assert(!mkdir(path,0700));
    memset(raw,0,sizeof(raw)); memcpy(raw,"AWF1",4); raw[4]=14; raw[5]=16; raw[6]=1;
    raw[8+'A'*8+2]=3; raw[8+'A'*8+3]=1; raw[8+'A'*8+6]=3; raw[2056]=0x6c;
    write_asset("magic14.awf",raw,2057);
    raw[4]=12; raw[5]=14; write_asset("magic12.awf",raw,2057);
    write_asset("book12.awf",raw,2057);
    raw[2056]=0xbc; /* Candidate coverages 2,3,3; ordinary was 1,2,3. */
    if(!strcmp(argv[1],"corrupt"))raw[0]='X';
    if(!strcmp(argv[1],"wrong-size")){raw[4]=14;raw[5]=16;}
    if(strcmp(argv[1],"missing"))write_asset("paper12.awf",raw,!strcmp(argv[1],"oversized")?26625:!strcmp(argv[1],"truncated")?100:2057);
    for(i=0;i<256;i++)pal[i*3]=pal[i*3+1]=pal[i*3+2]=i;
    memset(frame,137,sizeof(frame)); vid.width=320;vid.height=200;vid.rowbytes=320;vid.buffer=frame+2;
    AW_UIInit();AW_UIText(20,20,"A",0);memcpy(before,vid.buffer+20*320+20,3);
    AW_UISmallBegin();assert(AW_UIWidth("AA")==6);AW_UIText(20,20,"A",0);
    memcpy(small,vid.buffer+20*320+20,3);AW_UISmallEnd();assert(!paper_opens);
    assert(AW_UIHeight()==16);
    for(i=0;i<3;i++){
        AW_UIBookBegin();assert(AW_UIHeight()==14);assert(AW_UIWidth("AA")==6);AW_UIText(20,20,"A",0);
        assert(vid.buffer[20*320+20]==(valid?85:170));
        assert(vid.buffer[20*320+21]==(valid?0:85));assert(vid.buffer[20*320+22]==0);
        AW_UIBookEnd();assert(AW_UIHeight()==16);
        AW_UISmallBegin();AW_UIText(20,20,"A",0);
        assert(!memcmp(small,vid.buffer+20*320+20,3));AW_UISmallEnd();
        AW_UIText(20,20,"A",0);assert(!memcmp(before,vid.buffer+20*320+20,3));
    }
    assert(paper_opens==1);
    assert(warnings==((valid || !strcmp(argv[1],"missing"))?0:1));
    assert(frame[0]==137 && frame[1]==137 && frame[64002]==137 && frame[64003]==137);
    sprintf(path,"%s/gfx/magic14.awf",directory);unlink(path);
    sprintf(path,"%s/gfx/magic12.awf",directory);unlink(path);
    sprintf(path,"%s/gfx/book12.awf",directory);unlink(path);
    sprintf(path,"%s/gfx/paper12.awf",directory);unlink(path);
    sprintf(path,"%s/gfx",directory);assert(!rmdir(path));assert(!rmdir(directory));
    return 0;
}
int AW_PhotoModeActive(void){return 0;}
