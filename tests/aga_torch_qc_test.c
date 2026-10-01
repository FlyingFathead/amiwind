/* SPDX-License-Identifier: GPL-2.0-or-later
 * Run the real compiled hand rules through the engine's QuakeC interpreter. */
#include "quakedef.h"
#include <assert.h>
#include <stddef.h>
server_t sv;
dprograms_t *progs;dfunction_t *pr_functions;char *pr_strings;
ddef_t *pr_globaldefs,*pr_fielddefs;dstatement_t *pr_statements;
globalvars_t *pr_global_struct;float *pr_globals;int pr_edict_size;
static builtin_t builtins[37];builtin_t *pr_builtins=builtins;int pr_numbuiltins=37;
void Con_Printf(char *fmt,...){}
void Host_Error(char *fmt,...){assert(0);abort();}
void Sys_Error(char *fmt,...){assert(0);abort();}
void ED_Print(edict_t *e){assert(0);}
char *PR_GlobalString(int offset){return "test";}
char *PR_GlobalStringNoContents(int offset){return "test";}
static void floor_builtin(void){G_FLOAT(OFS_RETURN)=floor(G_FLOAT(OFS_PARM0));}
static float *field(edict_t *e,const char *name)
{
    int i;
    for(i=0;i<progs->numfielddefs;i++)if(!strcmp(pr_strings+pr_fielddefs[i].s_name,name))
        return (float *)&e->v+pr_fielddefs[i].ofs;
    assert(0);return NULL;
}
int main(int argc,char **argv)
{
    FILE *f;byte *raw;long size;int fn,i;edict_t *p,*world;
    assert(argc==2);f=fopen(argv[1],"rb");assert(f);fseek(f,0,SEEK_END);size=ftell(f);rewind(f);
    assert(size>sizeof(dprograms_t) && size<1048576);raw=malloc(size);assert(raw);
    assert(fread(raw,1,size,f)==size);fclose(f);progs=(dprograms_t *)raw;
    assert(progs->version==6); /* Fixture runs on the little-endian host. */
    pr_functions=(dfunction_t *)(raw+progs->ofs_functions);pr_strings=(char *)(raw+progs->ofs_strings);
    pr_fielddefs=(ddef_t *)(raw+progs->ofs_fielddefs);pr_statements=(dstatement_t *)(raw+progs->ofs_statements);
    pr_globals=(float *)(raw+progs->ofs_globals);pr_global_struct=(globalvars_t *)pr_globals;
    pr_edict_size=(offsetof(edict_t,v)+progs->entityfields*4+7)&~7;
    sv.edicts=calloc(2,pr_edict_size);assert(sv.edicts);world=sv.edicts;p=NEXT_EDICT(world);
    pr_global_struct->self=EDICT_TO_PROG(p);builtins[36]=floor_builtin;
    fn=0;for(i=1;i<progs->numfunctions;i++)if(!strcmp(pr_strings+pr_functions[i].s_name,"aw_hands_update"))fn=i;
    assert(fn);p->v.health=100;
    *field(world,"aw_hand_draw")=.4;*field(world,"aw_hand_idle")=2;
    *field(world,"aw_hand_lower")=.3;*field(world,"aw_hand_punch")=.5;
    p->v.impulse=202;PR_ExecuteProgram(fn);
    assert(*field(p,"aw_hand_goal")==1 && *field(p,"aw_hand_state")==1);
    pr_global_struct->time=.6;PR_ExecuteProgram(fn);assert(*field(p,"aw_hand_state")==2);
    *field(p,"aw_torch")=1;p->v.button0=1;PR_ExecuteProgram(fn);
    assert(*field(p,"aw_hand_state")==2 && *field(p,"aw_torch")==1); /* no torch punch */
    p->v.impulse=202;PR_ExecuteProgram(fn);
    assert(!*field(p,"aw_hand_goal") && !*field(p,"aw_torch") && *field(p,"aw_hand_state")==4);
    pr_global_struct->time=1;PR_ExecuteProgram(fn);
    assert(!*field(p,"aw_hand_state") && !pr_strings[p->v.weaponmodel]);
    p->v.button0=0;p->v.impulse=202;PR_ExecuteProgram(fn);pr_global_struct->time=2;PR_ExecuteProgram(fn);
    p->v.button0=1;PR_ExecuteProgram(fn);assert(*field(p,"aw_hand_state")==3); /* fists still punch */
    *field(p,"aw_torch")=1;p->v.health=0;PR_ExecuteProgram(fn);assert(!*field(p,"aw_torch"));
    free(sv.edicts);free(raw);return 0;
}
