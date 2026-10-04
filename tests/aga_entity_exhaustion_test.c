/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
#include <setjmp.h>
#include <stdarg.h>
server_t sv; server_static_t svs; keydest_t key_dest;
extern cvar_t aw_ent_count_exceed_soft_fail;
static jmp_buf recovery;
static int soft, fatal, warning;
static char message[512];
void Con_Printf(char *fmt,...) {va_list a;va_start(a,fmt);vsprintf(message,fmt,a);va_end(a);warning++;}
void Host_Error(char *fmt,...) {soft++;longjmp(recovery,1);}
void Sys_Error(char *fmt,...) {fatal++;longjmp(recovery,2);}
int main(void) {
    int result; dprograms_t program; edict_t *pool;
    memset(&program,0,sizeof(program));program.entityfields=sizeof(entvars_t)/4;
    progs=&program;pr_edict_size=sizeof(edict_t);
    pool=calloc(MAX_EDICTS,sizeof(edict_t));assert(pool);
    sv.edicts=pool;sv.max_edicts=MAX_EDICTS;sv.num_edicts=MAX_EDICTS;svs.maxclients=1;
    strcpy(sv.name,"bm028");
    assert(!strcmp(aw_ent_count_exceed_soft_fail.string,"1"));
    aw_ent_count_exceed_soft_fail.value=1;key_dest=key_game;
    result=setjmp(recovery);if(!result){ED_Alloc();assert(0);}
    assert(result==1 && soft==1 && fatal==0 && warning==1 && key_dest==key_console);
    assert(strstr(message,"bm028") && strstr(message,"600/600"));
    assert(sv.num_edicts==MAX_EDICTS);
    aw_ent_count_exceed_soft_fail.value=0;
    result=setjmp(recovery);if(!result){ED_Alloc();assert(0);}
    assert(result==2 && fatal==1 && warning==1);
    pool[2].free=true;pool[2].freetime=0;
    assert(ED_Alloc()==&pool[2] && !pool[2].free && sv.num_edicts==MAX_EDICTS);
    free(pool);return 0;
}
