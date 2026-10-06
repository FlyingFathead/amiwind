/* SPDX-License-Identifier: GPL-2.0-or-later
 * One BSP entity string passes through the real QC and native range readers. */
#include "quakedef.h"
#include <assert.h>
#include <stddef.h>
#include <setjmp.h>
#include <stdarg.h>
#define AW_RENDER_RANGES_TEST
#include "aw_render_ranges.c"

server_t sv;
client_state_t cl;
static jmp_buf failed;
static int expect_error,warnings;
static char last_error[256];
static void *allocated[16];
static int allocated_count;
static model_t world,pool,original;
static msurface_t surface;
static edict_t edicts[2];
static dprograms_t program;
static ddef_t fields[5];
static char names[]="\0classname\0model\0health\0angles\0";

void Sys_Error(char *fmt,...){
    va_list ap;va_start(ap,fmt);vsnprintf(last_error,sizeof(last_error),fmt,ap);va_end(ap);
    if(expect_error)longjmp(failed,1);fprintf(stderr,"%s\n",last_error);abort();
}
void Host_Error(char *fmt,...){Sys_Error("Unexpected field parse failure");}
void Con_Printf(char *fmt,...){if(strstr(fmt,"not a field"))warnings++;}
void *Hunk_AllocName(int size,char *name){
    void *p=calloc(1,size);assert(p && allocated_count<16);allocated[allocated_count++]=p;return p;
}
void *Hunk_Alloc(int size){return Hunk_AllocName(size,"test");}

static void parse_qc(char *text){
    char *p=text;int count=0;
    while((p=COM_Parse(p))!=NULL){
        assert(!strcmp(com_token,"{") && count<2);
        p=ED_ParseEdict(p,&edicts[count++]);
    }
    assert(count==2);
}
static void must_fail(char *text,int native){
    expect_error=1;
    if(!setjmp(failed)){
        if(native){world.entities=text;AW_RenderRangesNewMap();}
        else ED_ParseEdict(text,&edicts[1]);
        assert(!"Malformed metadata was accepted");
    }
    expect_error=0;
}
int main(void){
    char text[18000],saved[18000],large[16500];int i;entity_t ent;model_t view;
    pr_strings=names;progs=&program;pr_fielddefs=fields;pr_edict_size=sizeof(edict_t);
    program.numfielddefs=5;program.entityfields=sizeof(entvars_t)/4;sv.edicts=edicts;
    fields[1].s_name=1;fields[2].s_name=11;fields[3].s_name=17;fields[4].s_name=24;
    fields[3].type=ev_float;fields[3].ofs=offsetof(entvars_t,health)/4;
    fields[4].type=ev_vector;fields[4].ofs=offsetof(entvars_t,angles)/4;
    strcpy(pool.name,"*2");strcpy(original.name,"*1");
    pool.type=original.type=mod_brush;pool.surfaces=original.surfaces=&surface;
    pool.numsurfaces=original.numsurfaces=4000;pool.firstmodelsurface=20;pool.nummodelsurfaces=3000;
    cl.worldmodel=&world;cl.model_precache[1]=&original;cl.model_precache[2]=&pool;
    strcpy(text,"{\"classname\" \"worldspawn\" \"aw_render_pool\" \"*2\"}\n"
        "{\"classname\" \"func_wall\" \"model\" \"*1\" \"aw_render_ranges\" \"");
    /* 3999 bytes is larger than COM_Parse's 1024-byte shared token. */
    for(i=0;i<1000;i++)strcat(text,i?",0:1":"0:1");
    strcat(text,"\" \"health\" \"37\" \"angle\" \"90\"}");strcpy(saved,text);
    parse_qc(text);assert(!warnings && edicts[1].v.health==37 && edicts[1].v.angles[1]==90);
    assert(!memcmp(text,saved,strlen(text)+1));
    world.entities=text;AW_RenderRangesNewMap();memset(&ent,0,sizeof(ent));ent.model=&original;ent.angles[1]=90;
    assert(AW_RenderRangeView(&ent,999,&view) && view.firstmodelsurface==20 && view.nummodelsurfaces==1);
    assert(!AW_RenderRangeView(&ent,1000,&view));
    /* Ordinary unknown fields still warn; comments and unquoted pool values work. */
    ED_ParseEdict("\"aw_render_pool\" // native\n *2 \"aw_unknown\" \"1\" \"health\" \"9\" }",&edicts[1]);
    assert(warnings==1 && edicts[1].v.health==9);
    must_fail("\"aw_render_ranges\" }",0);
    must_fail("\"aw_render_ranges\" \"unclosed",0);
    strcpy(large,"\"aw_render_ranges\" \"");i=strlen(large);memset(large+i,'1',16384);strcpy(large+i+16384,"\" }");
    must_fail(large,0);
    /* Consumed native fields are still validated by the renderer, not hidden. */
    must_fail("{\"aw_render_pool\" \"*2\"}{\"classname\" \"func_wall\" \"model\" \"*1\" \"aw_render_ranges\" \"2999:2\"}",1);
    assert(strstr(last_error,"Invalid render pool ranges"));
    for(i=0;i<allocated_count;i++)free(allocated[i]);
    puts("QC/native metadata handoff passed; long lists bounded; unknown fields still warn");return 0;
}
