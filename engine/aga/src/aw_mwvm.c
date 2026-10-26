/* SPDX-License-Identifier: GPL-2.0-or-later
 * The interpreter of the compiled game scripts: a switch on opcodes over a stack of 32-bit cells
 * (docs/MWSCRIPT_BYTECODE.md; the compiler is tools/mwscript/, the opcodes aw_mwcode.h).
 *
 * As the roadmap asks: a script runs only while its object is active (attached to the loaded map and within the
 * activation range, or in the loaded room), and a script that reads nothing outside the game state (no time,
 * distance, chance, sound state or engine query: not VOLATILE) runs again only when the state it can read has
 * changed since its last run changed nothing. A per-frame opcode budget shares the frame round robin; no
 * allocation while running; every script's code is checked once at load (operands, jump targets, stack depth),
 * so the loop itself does no bounds checks. Functions the engine cannot carry out yet are NOTYET: logged once,
 * never a crash. */
#include <stdlib.h>
#include <string.h>
#include "aw_mwvm.h"
#include "aw_mwcode.h"
#include "aw_tryalloc.h"

#define MAX_SCRIPTS 2048
#define MAX_GLOBALS 512
#define MAX_CODE 8192           /* longest single script the load check accepts */

typedef struct {uint32_t reference;uint16_t script,count,at;} parked_t;

/* The interpreter's tables (about 75 KB) exist only once the scripts are switched on and loaded: one block taken
 * at load (AW_MwvmLoad), kept for the session; a game that never switches them on spends nothing. */
typedef struct {
    const unsigned char *base;unsigned long bytes;const aw_mwvm_host_t *host;
    const unsigned char *glob,*jrnl,*snds,*voic,*musi,*objs,*scrp,*strt,*code;
    int nglob,njrnl,nsnds,nvoic,nmusi,nobjs,nscrp,nstrt;unsigned long ncode;
    uint32_t range;int ops_frame,ops_run;
    unsigned char runnable[MAX_SCRIPTS];      /* passed the load check and not hand-written/broken */
    int16_t global_instance[MAX_SCRIPTS];
    aw_mwcell_t globals[MAX_GLOBALS];
    aw_mwvm_instance_t inst[AW_MWVM_INSTANCES];int ninst,cursor;
    aw_mwcell_t cells[AW_MWVM_CELLS];int low,high;        /* objects from below, global scripts from above */
    parked_t parked[AW_MWVM_PARKED];int nparked;
    aw_mwcell_t park[AW_MWVM_PARK_CELLS];int park_used;
    unsigned char logged[AW_MWVM_STRINGS/8];
    uint32_t generation;float now,dt;uint32_t rng;
    int loaded;aw_mwvm_stats_t stats;
    unsigned char warned_park,warned_cells,warned_inst;
    unsigned char marks[MAX_CODE];
} vm_t;
static vm_t *vmp;
#define vm (*vmp)
#define marks (vm.marks)

#define U16(p) ((unsigned)(((p)[0]<<8)|(p)[1]))
#define S16(p) ((int)(int16_t)U16(p))
static uint32_t u32(const unsigned char *p){return ((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|p[3];}
static float f32(const unsigned char *p){uint32_t u=u32(p);float f;memcpy(&f,&u,4);return f;}
static int32_t short16(int32_t v){return (int32_t)(int16_t)(uint16_t)(v&0xFFFF);}

/* --- loading --- */
static const unsigned char *section(const char *tag,int *rows,unsigned long *bytes){
    unsigned n=U16(vm.base+6),i;
    for(i=0;i<n;i++){
        const unsigned char *d=vm.base+16+16*i;
        if(!memcmp(d,tag,4)){
            uint32_t off=u32(d+4),len=u32(d+12);
            if(off+len>vm.bytes || off+len<off)return NULL;
            if(rows)*rows=(int)u32(d+8);
            if(bytes)*bytes=len;
            return vm.base+off;
        }
    }
    return NULL;
}
int AW_MwvmSection(const char tag[4],uint32_t *offset,uint32_t *rows,uint32_t *bytes){
    unsigned n,i;
    if(!vmp || !vm.base)return 0;
    n=U16(vm.base+6);
    for(i=0;i<n;i++){const unsigned char *d=vm.base+16+16*i;
        if(!memcmp(d,tag,4)){*offset=u32(d+4);*rows=u32(d+8);*bytes=u32(d+12);return 1;}}
    return 0;
}
static int operand_bytes(const unsigned char *p,unsigned long left){
    switch(p[0]){
    case AWM_END:case AWM_RET:case AWM_I2F:case AWM_F2I:case AWM_ADDI:case AWM_SUBI:case AWM_MULI:case AWM_DIVI:
    case AWM_NEGI:case AWM_ADDF:case AWM_SUBF:case AWM_MULF:case AWM_DIVF:case AWM_NEGF:case AWM_EQI:case AWM_NEI:
    case AWM_LTI:case AWM_LEI:case AWM_GTI:case AWM_GEI:case AWM_EQF:case AWM_NEF:case AWM_LTF:case AWM_LEF:
    case AWM_GTF:case AWM_GEF:case AWM_POP:case AWM_SAYDONE:case AWM_SECONDS:case AWM_RANDOM:case AWM_MENUMODE:
    case AWM_CELLCHANGED:case AWM_SQRT:case AWM_ENABLE:case AWM_DISABLE:case AWM_GETDISABLED:case AWM_LOCK:
    case AWM_UNLOCK:case AWM_GETLOCKED:case AWM_ONACTIVATE:case AWM_ACTIVATE:case AWM_GETBUTTONPRESSED:return 0;
    case AWM_PUSHB:case AWM_GETL:case AWM_SETL:case AWM_SETLS:return 1;
    case AWM_JMP:case AWM_JZ:case AWM_PUSHW:case AWM_GETG:case AWM_SETG:case AWM_SETGS:case AWM_GETJ:case AWM_SETJ:
    case AWM_JOURNAL:case AWM_REF:case AWM_PLAYSOUND:case AWM_PLAYSOUNDVP:case AWM_PLAYSOUND3D:case AWM_PLAYSOUND3DVP:
    case AWM_PLAYLOOP3D:case AWM_PLAYLOOP3DVP:case AWM_STOPSOUND:case AWM_SOUNDPLAYING:case AWM_STREAMMUSIC:
    case AWM_STARTSCRIPT:case AWM_STOPSCRIPT:case AWM_SCRIPTRUNNING:case AWM_DISTANCE:return 2;
    case AWM_GETM:case AWM_SETM:case AWM_SETMS:case AWM_QUERY:return 3;
    case AWM_PUSHL:case AWM_PUSHF:case AWM_SAY:return 4;
    case AWM_NOTYET:case AWM_MESSAGEBOX:return left>=5?4+2*p[4]:-1;
    }
    return -1;
}
/* Walk one script's code once: every opcode known, operands inside the code, indexes inside their tables,
 * jumps onto an opcode of the same script, the stack within bounds. */
static int check_code(const unsigned char *code,unsigned long n,int nlocals){
    unsigned long i=0;unsigned last=AWM_END;
    if(n==0 || n>MAX_CODE)return 0;
    memset(marks,0,n);
    while(i<n){
        int k=operand_bytes(code+i,n-i);const unsigned char *o=code+i+1;
        if(k<0 || i+1+k>n)return 0;
        marks[i]=1;last=code[i];
        switch(code[i]){
        case AWM_GETL:case AWM_SETL:case AWM_SETLS:if(o[0]>=nlocals)return 0;break;
        case AWM_GETG:case AWM_SETG:case AWM_SETGS:if((int)U16(o)>=vm.nglob)return 0;break;
        case AWM_GETJ:case AWM_SETJ:case AWM_JOURNAL:if((int)U16(o)>=vm.njrnl)return 0;break;
        case AWM_GETM:case AWM_SETM:case AWM_SETMS:if((int)U16(o)>=vm.nobjs)return 0;break;
        case AWM_REF:case AWM_DISTANCE:if(U16(o)!=AWM_NONE && (int)U16(o)>=vm.nobjs)return 0;break;
        case AWM_PLAYSOUND:case AWM_PLAYSOUNDVP:case AWM_PLAYSOUND3D:case AWM_PLAYSOUND3DVP:case AWM_PLAYLOOP3D:
        case AWM_PLAYLOOP3DVP:case AWM_STOPSOUND:case AWM_SOUNDPLAYING:if((int)U16(o)>=vm.nsnds)return 0;break;
        case AWM_SAY:if((int)U16(o)>=vm.nvoic)return 0;break;
        case AWM_STREAMMUSIC:if((int)U16(o)>=vm.nmusi)return 0;break;
        case AWM_STARTSCRIPT:case AWM_STOPSCRIPT:case AWM_SCRIPTRUNNING:if((int)U16(o)>=vm.nscrp)return 0;break;
        case AWM_QUERY:if(o[0]==0 || o[0]>=AWQ_COUNT)return 0;break;
        case AWM_NOTYET:if((o[2]&0x1F)>AW_MWVM_STACK)return 0;break;
        case AWM_MESSAGEBOX:if(o[2]>0x1F)return 0;break;
        }
        i+=1+k;
    }
    if(last!=AWM_END && last!=AWM_RET && last!=AWM_JMP)return 0;    /* the code cannot run off its end */
    for(i=0;i<n;i+=1+operand_bytes(code+i,n-i)){
        if(code[i]==AWM_JMP || code[i]==AWM_JZ){
            long t=(long)i+3+S16(code+i+1);
            if(t<0 || t>=(long)n || !marks[t])return 0;
        }
    }
    return 1;
}
void AW_MwvmReset(void){if(vmp)memset(vmp,0,sizeof(*vmp));}
int AW_MwvmLoaded(void){return vmp && vm.loaded;}
int AW_MwvmLoad(const unsigned char *data,unsigned long bytes,const aw_mwvm_host_t *host){
    const unsigned char *conf;int rows,i;unsigned long len;
    if(!vmp && !(vmp=(vm_t *)AW_TryMalloc(sizeof(vm_t))))return 0;   /* once, at load; never while running */
    AW_MwvmReset();
    if(!data || bytes<16 || memcmp(data,"AWMS",4) || U16(data+4)!=1)return 0;
    if(u32(data+12)>bytes || bytes<16+16*(unsigned long)U16(data+6))return 0;
    vm.base=data;vm.bytes=bytes;vm.host=host;
    conf=section("CONF",&rows,&len);
    vm.glob=section("GLOB",&vm.nglob,&len);vm.jrnl=section("JRNL",&vm.njrnl,&len);
    vm.snds=section("SNDS",&vm.nsnds,&len);vm.voic=section("VOIC",&vm.nvoic,&len);
    vm.musi=section("MUSI",&vm.nmusi,&len);vm.objs=section("OBJS",&vm.nobjs,&len);
    vm.scrp=section("SCRP",&vm.nscrp,&len);vm.strt=section("STRT",&vm.nstrt,&len);
    vm.code=section("CODE",&rows,&vm.ncode);
    if(!conf || !vm.glob || !vm.jrnl || !vm.snds || !vm.voic || !vm.musi || !vm.objs || !vm.scrp || !vm.strt ||
       !vm.code || vm.nscrp>MAX_SCRIPTS || vm.nglob>MAX_GLOBALS){AW_MwvmReset();return 0;}
    vm.range=u32(conf);vm.ops_frame=(int)U16(conf+4);vm.ops_run=(int)U16(conf+6);
    if(vm.ops_frame<1)vm.ops_frame=1;
    if(vm.ops_run<1)vm.ops_run=1;
    for(i=0;i<vm.nglob;i++)vm.globals[i].i=(int32_t)u32(vm.glob+8*i+4);
    for(i=0;i<vm.nscrp;i++){
        const unsigned char *s=vm.scrp+16*i;uint32_t off=u32(s+8),n=u32(s+12);int flags=(int)U16(s+4);
        vm.global_instance[i]=-1;
        if(off+n>vm.ncode || s[3]>AW_MWVM_STACK || (flags&(AWS_BROKEN|AWS_HANDWRITTEN|AWS_INERT)))continue;
        vm.runnable[i]=(unsigned char)check_code(vm.code+off,n,s[2]);
    }
    vm.low=0;vm.high=AW_MWVM_CELLS;vm.rng=0x2545F491u;vm.loaded=1;
    for(i=0;i<vm.nstrt;i++)AW_MwvmStartScript((int)U16(vm.strt+2*i));
    return 1;
}
#define ON (vmp && vm.loaded)
static const aw_mwvm_stats_t no_stats;
int AW_MwvmScriptCount(void){return ON?vm.nscrp:0;}
int AW_MwvmScriptFlags(int s){return ON && s>=0 && s<vm.nscrp?(int)U16(vm.scrp+16*s+4)|(vm.runnable[s]?0:AWS_BROKEN):0;}
int AW_MwvmScriptName(int s){return ON && s>=0 && s<vm.nscrp?(int)U16(vm.scrp+16*s):-1;}
int AW_MwvmSound(int k,unsigned char hash[8],int *centis,int *volume,int *near_units,int *far_units){
    const unsigned char *r;if(!ON || k<0 || k>=vm.nsnds)return 0;
    r=vm.snds+18*k;memcpy(hash,r,8);*centis=(int)U16(r+8);*volume=r[10];
    *near_units=(int)U16(r+12);*far_units=(int)U16(r+14);return r[11]&1;
}
int AW_MwvmVoice(int k,unsigned char hash[8],int *centis){
    const unsigned char *r;if(!ON || k<0 || k>=vm.nvoic)return 0;
    r=vm.voic+12*k;memcpy(hash,r,8);*centis=(int)U16(r+8);
    return r[0]|r[1]|r[2]|r[3]|r[4]|r[5]|r[6]|r[7]?1:0;
}
int AW_MwvmMusic(int k){return ON && k>=0 && k<vm.nmusi && (vm.musi[4*k+1]&1)?vm.musi[4*k]:-1;}
uint32_t AW_MwvmObjectReference(int k){return ON && k>=0 && k<vm.nobjs?u32(vm.objs+12*k):0;}
int AW_MwvmTopicName(int k){return ON && k>=0 && k<vm.njrnl?(int)U16(vm.jrnl+2*k):-1;}
int AW_MwvmTopicCount(void){return ON?vm.njrnl:0;}
void AW_MwvmConfig(uint32_t *range,int *ops_frame,int *ops_run){
    *range=ON?vm.range:0;*ops_frame=ON?vm.ops_frame:0;*ops_run=ON?vm.ops_run:0;
}
int32_t AW_MwvmGlobalInt(int g){return ON && g>=0 && g<vm.nglob?vm.globals[g].i:0;}
float AW_MwvmGlobalFloat(int g){return ON && g>=0 && g<vm.nglob?vm.globals[g].f:0;}
int AW_MwvmGlobalCount(void){return ON?vm.nglob:0;}
const aw_mwvm_stats_t *AW_MwvmStats(void){return ON?&vm.stats:&no_stats;}
aw_mwvm_instance_t *AW_MwvmInstance(int k){return ON && k>=0 && k<vm.ninst?&vm.inst[k]:NULL;}
int AW_MwvmInstanceCount(void){return ON?vm.ninst:0;}
static int nlocals(int script){return vm.scrp[16*script+2];}
aw_mwcell_t AW_MwvmLocal(int k,int slot){
    aw_mwcell_t zero;zero.i=0;
    if(!ON || k<0 || k>=vm.ninst || !(vm.inst[k].flags&AWI_USED) || slot<0 || slot>=nlocals(vm.inst[k].script))return zero;
    return vm.cells[vm.inst[k].locals+slot];
}

/* --- instances, parking --- */
static int new_instance(void){
    int k;
    for(k=0;k<vm.ninst;k++)if(!(vm.inst[k].flags&AWI_USED))break;
    if(k==AW_MWVM_INSTANCES){
        if(!vm.warned_inst && vm.host && vm.host->warn){vm.warned_inst=1;vm.host->warn("instance table full",-1);}
        return -1;
    }
    if(k==vm.ninst)vm.ninst++;
    memset(&vm.inst[k],0,sizeof(vm.inst[k]));vm.inst[k].entity=-1;
    return k;
}
static parked_t *find_parked(uint32_t ref){
    int i;for(i=0;i<vm.nparked;i++)if(vm.parked[i].reference==ref)return &vm.parked[i];
    return NULL;
}
static parked_t *park_slot(uint32_t ref,int script){
    parked_t *p=find_parked(ref);int n=nlocals(script);
    if(p)return p->script==script?p:NULL;
    if(vm.nparked>=AW_MWVM_PARKED || vm.park_used+n>AW_MWVM_PARK_CELLS){
        if(!vm.warned_park && vm.host && vm.host->warn){vm.warned_park=1;vm.host->warn("parking store full",-1);}
        return NULL;
    }
    p=&vm.parked[vm.nparked++];p->reference=ref;p->script=(uint16_t)script;p->count=(uint16_t)n;
    p->at=(uint16_t)vm.park_used;vm.park_used+=n;
    memset(&vm.park[p->at],0,n*sizeof(aw_mwcell_t));
    return p;
}
void AW_MwvmBeginMap(void){
    int k;
    if(!ON)return;
    for(k=0;k<vm.ninst;k++){
        aw_mwvm_instance_t *in=&vm.inst[k];
        if(!(in->flags&AWI_USED))continue;
        if(in->flags&AWI_GLOBAL){in->flags|=AWI_CELLCHANGED;in->flags&=~AWI_QUIET;continue;}
        {parked_t *p=park_slot(in->reference,in->script);
         if(p)memcpy(&vm.park[p->at],&vm.cells[in->locals],p->count*sizeof(aw_mwcell_t));}
        in->flags=0;
    }
    while(vm.ninst>0 && !(vm.inst[vm.ninst-1].flags&AWI_USED))vm.ninst--;
    vm.low=0;vm.cursor=0;
}
int AW_MwvmAttach(uint32_t reference,int script,int bind_flags,int entity,const float origin[3]){
    int k,n;parked_t *p;aw_mwvm_instance_t *in;
    if(!ON || script<0 || script>=vm.nscrp || !vm.runnable[script])return -1;
    for(k=0;k<vm.ninst;k++)if((vm.inst[k].flags&AWI_USED) && !(vm.inst[k].flags&AWI_GLOBAL) &&
                               vm.inst[k].reference==reference)return k;   /* attached once */
    n=nlocals(script);
    if(vm.low+n>vm.high){
        if(!vm.warned_cells && vm.host && vm.host->warn){vm.warned_cells=1;vm.host->warn("local value pool full",-1);}
        return -1;
    }
    k=new_instance();if(k<0)return -1;
    in=&vm.inst[k];in->script=(uint16_t)script;in->reference=reference;in->entity=entity;
    in->flags=AWI_USED|AWI_CELLCHANGED|((bind_flags&AWB_INTERIOR)?AWI_INTERIOR:0);
    if(origin){in->origin[0]=origin[0];in->origin[1]=origin[1];in->origin[2]=origin[2];}
    in->locals=vm.low;vm.low+=n;in->last_run=vm.now;
    p=find_parked(reference);
    if(p && p->script==script)memcpy(&vm.cells[in->locals],&vm.park[p->at],n*sizeof(aw_mwcell_t));
    else memset(&vm.cells[in->locals],0,n*sizeof(aw_mwcell_t));
    return k;
}
void AW_MwvmSetOrigin(int k,const float o[3]){
    if(ON && k>=0 && k<vm.ninst){vm.inst[k].origin[0]=o[0];vm.inst[k].origin[1]=o[1];vm.inst[k].origin[2]=o[2];}
}
static int global_instance(int script,int create){
    int k=vm.global_instance[script],n;
    if(k>=0 || !create)return k;
    n=nlocals(script);
    if(vm.high-n<vm.low){
        if(!vm.warned_cells && vm.host && vm.host->warn){vm.warned_cells=1;vm.host->warn("local value pool full",-1);}
        return -1;
    }
    k=new_instance();if(k<0)return -1;
    vm.high-=n;
    vm.inst[k].script=(uint16_t)script;vm.inst[k].flags=AWI_USED|AWI_GLOBAL|AWI_CELLCHANGED;
    vm.inst[k].locals=vm.high;vm.inst[k].last_run=vm.now;
    memset(&vm.cells[vm.high],0,n*sizeof(aw_mwcell_t));
    vm.global_instance[script]=(int16_t)k;
    return k;
}
void AW_MwvmStartScript(int script){
    int k;
    if(!ON || script<0 || script>=vm.nscrp || !vm.runnable[script])return;
    k=global_instance(script,1);
    if(k>=0)vm.inst[k].flags|=AWI_RUNNING;
}
/* The cells of object OBJECT's locals (an attached object, a parked one, or a script's global instance). */
static aw_mwcell_t *member(int object,int slot,int create){
    const unsigned char *r=vm.objs+12*object;uint32_t ref=u32(r);int script=(int)U16(r+4),k;parked_t *p;
    if(script==AWM_NONE || script>=vm.nscrp || slot>=nlocals(script))return NULL;
    if(U16(r+10)&1){
        k=global_instance(script,create);
        return k>=0?&vm.cells[vm.inst[k].locals+slot]:NULL;
    }
    if(!ref)return NULL;
    for(k=0;k<vm.ninst;k++)
        if((vm.inst[k].flags&(AWI_USED|AWI_GLOBAL))==AWI_USED && vm.inst[k].reference==ref)
            return vm.inst[k].script==script?&vm.cells[vm.inst[k].locals+slot]:NULL;
    p=create?park_slot(ref,script):find_parked(ref);
    return p && p->script==script?&vm.park[p->at+slot]:NULL;
}

/* --- the interpreter --- */
static void log_notyet(int name,int script){
    if(name<0 || name>=AW_MWVM_STRINGS || (vm.logged[name>>3]&(1<<(name&7))))return;
    vm.logged[name>>3]|=(unsigned char)(1<<(name&7));
    if(vm.host && vm.host->notyet)vm.host->notyet(name,AW_MwvmScriptName(script));
}
static int run(int k){
    aw_mwvm_instance_t *in=&vm.inst[k];
    const unsigned char *s=vm.scrp+16*in->script,*pc=vm.code+u32(s+8);
    const aw_mwvm_host_t *h=vm.host;
    aw_mwcell_t stack[AW_MWVM_STACK+1],*sp=stack,*locals=&vm.cells[in->locals];
    int target=AW_MWVM_SELF,ops=0,changed=0,acted=0,limit=vm.ops_run;
    float elapsed=vm.now-in->last_run;
    if(elapsed<=0)elapsed=vm.dt;     /* the first run after attaching: this frame's time */
    for(;;){
        unsigned op=*pc++;
        if(++ops>limit){
            vm.stats.aborted++;
            if(h && h->warn)h->warn("a run reached the opcode limit",AW_MwvmScriptName(in->script));
            break;
        }
        switch(op){
        case AWM_END:case AWM_RET:goto done;
        case AWM_JMP:pc+=2+S16(pc);break;
        case AWM_JZ:--sp;pc+=sp->i?2:2+S16(pc);break;
        case AWM_PUSHB:sp->i=(int8_t)*pc++;sp++;break;
        case AWM_PUSHW:sp->i=S16(pc);pc+=2;sp++;break;
        case AWM_PUSHL:sp->i=(int32_t)u32(pc);pc+=4;sp++;break;
        case AWM_PUSHF:sp->f=f32(pc);pc+=4;sp++;break;
        case AWM_GETL:*sp++=locals[*pc++];break;
        case AWM_SETL:--sp;if(locals[*pc].i!=sp->i){locals[*pc].i=sp->i;changed=1;}pc++;break;
        case AWM_SETLS:--sp;{int32_t v=short16(sp->i);if(locals[*pc].i!=v){locals[*pc].i=v;changed=1;}}pc++;break;
        case AWM_GETG:*sp++=vm.globals[U16(pc)];pc+=2;break;
        case AWM_SETG:case AWM_SETGS:{
            int32_t v=op==AWM_SETGS?short16(sp[-1].i):sp[-1].i;aw_mwcell_t *g=&vm.globals[U16(pc)];--sp;pc+=2;
            if(g->i!=v){g->i=v;changed=1;vm.generation++;}
            break;}
        case AWM_GETM:{aw_mwcell_t *c=member(U16(pc),pc[2],0);sp->i=c?c->i:0;sp++;pc+=3;break;}
        case AWM_SETM:case AWM_SETMS:{
            aw_mwcell_t *c=member(U16(pc),pc[2],1);int32_t v=op==AWM_SETMS?short16(sp[-1].i):sp[-1].i;--sp;pc+=3;
            if(c && c->i!=v){c->i=v;changed=1;vm.generation++;}
            break;}
        case AWM_GETJ:sp->i=h && h->journal_get?h->journal_get(U16(pc)):0;sp++;pc+=2;break;
        case AWM_SETJ:case AWM_JOURNAL:{
            int topic=U16(pc);int32_t before=h && h->journal_get?h->journal_get(topic):0;--sp;pc+=2;
            if(h && h->journal_set)h->journal_set(topic,sp->i,op==AWM_JOURNAL);
            acted=1;
            if(!h || !h->journal_get || h->journal_get(topic)!=before){changed=1;vm.generation++;}
            break;}
        case AWM_I2F:sp[-1].f=(float)sp[-1].i;break;
        case AWM_F2I:{float f=sp[-1].f;sp[-1].i=!(f==f)?0:f>=2147483520.0f?2147483647:f<=-2147483648.0f?
                      (int32_t)0x80000000u:(int32_t)f;break;}
        case AWM_ADDI:--sp;sp[-1].i=(int32_t)((uint32_t)sp[-1].i+(uint32_t)sp->i);break;
        case AWM_SUBI:--sp;sp[-1].i=(int32_t)((uint32_t)sp[-1].i-(uint32_t)sp->i);break;
        case AWM_MULI:--sp;sp[-1].i=(int32_t)((uint32_t)sp[-1].i*(uint32_t)sp->i);break;
        case AWM_DIVI:--sp;sp[-1].i=sp->i==0 || (sp->i==-1 && sp[-1].i==(int32_t)0x80000000u)?0:sp[-1].i/sp->i;break;
        case AWM_NEGI:sp[-1].i=(int32_t)(0u-(uint32_t)sp[-1].i);break;
        case AWM_ADDF:--sp;sp[-1].f+=sp->f;break;
        case AWM_SUBF:--sp;sp[-1].f-=sp->f;break;
        case AWM_MULF:--sp;sp[-1].f*=sp->f;break;
        case AWM_DIVF:--sp;sp[-1].f=sp->f==0?0:sp[-1].f/sp->f;break;
        case AWM_NEGF:sp[-1].f=-sp[-1].f;break;
        case AWM_EQI:--sp;sp[-1].i=sp[-1].i==sp->i;break;
        case AWM_NEI:--sp;sp[-1].i=sp[-1].i!=sp->i;break;
        case AWM_LTI:--sp;sp[-1].i=sp[-1].i<sp->i;break;
        case AWM_LEI:--sp;sp[-1].i=sp[-1].i<=sp->i;break;
        case AWM_GTI:--sp;sp[-1].i=sp[-1].i>sp->i;break;
        case AWM_GEI:--sp;sp[-1].i=sp[-1].i>=sp->i;break;
        case AWM_EQF:--sp;sp[-1].i=sp[-1].f==sp->f;break;
        case AWM_NEF:--sp;sp[-1].i=sp[-1].f!=sp->f;break;
        case AWM_LTF:--sp;sp[-1].i=sp[-1].f<sp->f;break;
        case AWM_LEF:--sp;sp[-1].i=sp[-1].f<=sp->f;break;
        case AWM_GTF:--sp;sp[-1].i=sp[-1].f>sp->f;break;
        case AWM_GEF:--sp;sp[-1].i=sp[-1].f>=sp->f;break;
        case AWM_POP:--sp;break;
        case AWM_REF:target=U16(pc)==AWM_NONE?AW_MWVM_PLAYER:(int)U16(pc);pc+=2;break;
        case AWM_QUERY:sp->i=h && h->query?h->query(k,pc[0],(int)U16(pc+1)):0;sp++;pc+=3;target=AW_MWVM_SELF;break;
        case AWM_NOTYET:{
            int flags=pc[2];
            sp-=flags&0x1F;vm.stats.notyet_calls++;log_notyet((int)U16(pc),in->script);
            if(flags&0x80){if(flags&0x40)sp->f=0;else sp->i=0;sp++;}
            pc+=4+2*pc[3];target=AW_MWVM_SELF;   /* it did nothing: not an action for the quiet rule */
            break;}
        case AWM_PLAYSOUND:case AWM_PLAYSOUND3D:case AWM_PLAYLOOP3D:case AWM_STOPSOUND:
            if(h && h->sound)h->sound(k,target,(int)U16(pc),op==AWM_PLAYSOUND?AW_MWSND_2D:op==AWM_PLAYSOUND3D?
                                      AW_MWSND_3D:op==AWM_PLAYLOOP3D?AW_MWSND_LOOP:AW_MWSND_STOP,1.0f,1.0f);
            pc+=2;acted=1;target=AW_MWVM_SELF;break;
        case AWM_PLAYSOUNDVP:case AWM_PLAYSOUND3DVP:case AWM_PLAYLOOP3DVP:
            sp-=2;
            if(h && h->sound)h->sound(k,target,(int)U16(pc),op==AWM_PLAYSOUNDVP?AW_MWSND_2D:op==AWM_PLAYSOUND3DVP?
                                      AW_MWSND_3D:AW_MWSND_LOOP,sp[0].f,sp[1].f);
            pc+=2;acted=1;target=AW_MWVM_SELF;break;
        case AWM_SOUNDPLAYING:
            sp->i=h && h->sound_playing?h->sound_playing(k,target,(int)U16(pc)):0;sp++;pc+=2;target=AW_MWVM_SELF;break;
        case AWM_SAY:
            if(h && h->say)h->say(k,target,(int)U16(pc),(int)U16(pc+2));
            pc+=4;acted=1;target=AW_MWVM_SELF;break;
        case AWM_SAYDONE:sp->i=h && h->say_done?h->say_done(k,target):1;sp++;target=AW_MWVM_SELF;break;
        case AWM_STREAMMUSIC:if(h && h->music)h->music((int)U16(pc));pc+=2;acted=1;target=AW_MWVM_SELF;break;
        case AWM_SECONDS:sp->f=elapsed;sp++;break;
        case AWM_RANDOM:{
            int32_t n=sp[-1].i;
            vm.rng=vm.rng*1664525u+1013904223u;
            sp[-1].f=n>0?(float)(int32_t)((vm.rng>>8)%(uint32_t)n):0.0f;
            break;}
        case AWM_MENUMODE:sp->i=h && h->menu_mode?h->menu_mode():0;sp++;break;
        case AWM_CELLCHANGED:sp->i=(in->flags&AWI_CELLCHANGED)?1:0;sp++;break;
        case AWM_STARTSCRIPT:{
            int sk=(int)U16(pc),gk=vm.runnable[sk]?global_instance(sk,1):-1;pc+=2;
            in=&vm.inst[k];
            if(gk>=0 && !(vm.inst[gk].flags&AWI_RUNNING)){vm.inst[gk].flags|=AWI_RUNNING;changed=1;vm.generation++;}
            acted=1;break;}
        case AWM_STOPSCRIPT:{
            int gk=global_instance((int)U16(pc),0);pc+=2;
            if(gk>=0 && (vm.inst[gk].flags&AWI_RUNNING)){vm.inst[gk].flags&=~AWI_RUNNING;changed=1;vm.generation++;}
            acted=1;break;}
        case AWM_SCRIPTRUNNING:{
            int gk=global_instance((int)U16(pc),0);pc+=2;
            sp->i=gk>=0 && (vm.inst[gk].flags&AWI_RUNNING)?1:0;sp++;break;}
        case AWM_DISTANCE:{
            int t=U16(pc)==AWM_NONE?AW_MWVM_PLAYER:(int)U16(pc);pc+=2;
            sp->f=h && h->distance?h->distance(k,t):0.0f;sp++;target=AW_MWVM_SELF;break;}
        case AWM_SQRT:{
            /* Newton's method: no libm in the hot path; GetSquareRoot of a negative number is 0 */
            float x=sp[-1].f,r=x;int i;
            if(!(x>0)){sp[-1].f=0;break;}
            if(r<1)r=1;
            for(i=0;i<20;i++){float n=0.5f*(r+x/r);if(n==r)break;r=n;}
            sp[-1].f=r;break;}
        /* object state: carried out by the host (aw_mwhost.c), kept by reference in saved games */
        case AWM_ENABLE:case AWM_DISABLE:case AWM_UNLOCK:
            if(h && h->object)h->object(k,target,(int)op,0);
            acted=1;target=AW_MWVM_SELF;break;
        case AWM_LOCK:
            --sp;if(h && h->object)h->object(k,target,(int)op,sp->i);
            acted=1;target=AW_MWVM_SELF;break;
        case AWM_GETDISABLED:case AWM_GETLOCKED:
            sp->i=h && h->object?h->object(k,target,(int)op,0):0;sp++;target=AW_MWVM_SELF;break;
        /* activation: OnActivate is 1 once after the player's use (the instance's AWI_ACTIVATED, set by the host
         * when it took the use); Activate hands the use back to the object */
        case AWM_ONACTIVATE:
            sp->i=0;
            if(vm.inst[k].flags&AWI_ACTIVATED){vm.inst[k].flags&=~AWI_ACTIVATED;sp->i=1;}
            sp++;target=AW_MWVM_SELF;break;
        case AWM_ACTIVATE:
            if(h && h->object)h->object(k,target,(int)op,0);
            acted=1;target=AW_MWVM_SELF;break;
        /* messages: the numbers leave the stack in the order they were pushed */
        case AWM_MESSAGEBOX:{
            int number=pc[2],i;float numbers[0x1F];
            sp-=number;
            for(i=0;i<number;i++)numbers[i]=sp[i].f;
            if(h && h->message)h->message(k,(int)U16(pc),numbers,number,pc+4,pc[3]);
            pc+=4+2*pc[3];acted=1;target=AW_MWVM_SELF;break;}
        case AWM_GETBUTTONPRESSED:sp->i=h && h->button?h->button(k):-1;sp++;target=AW_MWVM_SELF;break;
        default:goto done;   /* unreachable: every opcode was checked at load */
        }
    }
done:
    in=&vm.inst[k];
    in->last_run=vm.now;
    if(changed || acted)in->flags&=~AWI_QUIET;else in->flags|=AWI_QUIET;
    in->flags&=~AWI_CELLCHANGED;
    in->generation=vm.generation;
    return ops;
}

static int active(const aw_mwvm_instance_t *in,const float player[3]){
    float d[3],r;
    if(in->flags&AWI_GLOBAL)return (in->flags&AWI_RUNNING)!=0;
    if(in->flags&AWI_INTERIOR)return 1;
    if(!player)return 1;
    d[0]=in->origin[0]-player[0];d[1]=in->origin[1]-player[1];d[2]=in->origin[2]-player[2];
    r=(float)vm.range*0.25f;   /* game units to engine units */
    return d[0]*d[0]+d[1]*d[1]+d[2]*d[2]<=r*r;
}
void AW_MwvmTick(float dt,const float player[3]){
    int i,n,used=0,start,next=-1;
    if(!ON)return;
    vm.dt=dt>0 && dt<10?dt:0;
    vm.now+=vm.dt;
    vm.stats.frames++;
    n=vm.ninst;start=n?vm.cursor%n:0;
    for(i=0;i<n;i++){
        int k=(start+i)%n;aw_mwvm_instance_t *in=&vm.inst[k];int flags;
        if(!(in->flags&AWI_USED))continue;
        if(!active(in,player)){in->flags&=~AWI_ACTIVE;vm.stats.skipped_far++;continue;}
        if(!(in->flags&AWI_ACTIVE)){in->flags|=AWI_ACTIVE|AWI_CELLCHANGED;in->flags&=~AWI_QUIET;}
        flags=(int)U16(vm.scrp+16*in->script+4);
        if(!(flags&AWS_VOLATILE) && (in->flags&AWI_QUIET) && in->generation==vm.generation &&
           !(in->flags&AWI_CELLCHANGED)){vm.stats.skipped_quiet++;continue;}
        /* out of budget: the first one left waits at the head of next frame's round */
        if(used>=vm.ops_frame){vm.stats.deferred++;if(next<0)next=k;continue;}
        used+=run(k);vm.stats.runs++;
    }
    vm.cursor=next>=0?next:start+1;
    vm.stats.ops+=used;
    if((unsigned long)used>vm.stats.max_ops_frame)vm.stats.max_ops_frame=used;
}
