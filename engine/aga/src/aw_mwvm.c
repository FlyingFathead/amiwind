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

/* MWSCRIPT-REFUSED-SCRIPT-COUNT-58: the dialogue result scripts (_dlg_N, one per distinct result text) are scripts of
 * the file too: 8,618 in v0.0.58-dev5, so the old 2,048 refused every file since they came in. 16,384 slots cost
 * 3 bytes each here (about 48 KB, taken once at load); tools/mwscript/awms.py ENGINE_MAX_SCRIPTS refuses a bigger
 * file at build time. */
#define MAX_SCRIPTS 16384
#define MAX_GLOBALS 512
#define MAX_CODE 8192           /* longest single script the load check accepts */

typedef struct {uint32_t reference;uint16_t script,count,at;} parked_t;

/* The interpreter's tables (about 160 KB) exist only once the scripts are switched on and loaded: one block taken
 * at load (AW_MwvmLoad), kept for the session; a game that never switches them on spends nothing. */
typedef struct {
    const unsigned char *base;unsigned long bytes;const aw_mwvm_host_t *host;
    const unsigned char *glob,*jrnl,*snds,*voic,*musi,*objs,*scrp,*strt,*code,*oact,*pcel,*pmov,*newg,*held;
    int nglob,njrnl,nsnds,nvoic,nmusi,nobjs,nscrp,nstrt,noact,npcel,npmov,nnewg,nheld;unsigned long ncode;
    uint32_t fcalls[AWM_FUNCTIONS];uint16_t fname[AWM_FUNCTIONS];   /* the import route's counters; name+1 */
    uint32_t nactb,naitm,naspt;       /* the actor table's rows (on disk: only their counts, for the load check) */
    uint32_t range;int ops_frame,ops_run;
    unsigned char runnable[MAX_SCRIPTS];      /* passed the load check and not hand-written/broken */
    int16_t story_held[AW_MWVM_HELD_SCRIPTS];int nheld_scripts;   /* held by the host now (AW_MwvmScriptHold) */
    const unsigned char *padd;int npadd;      /* the carried items' script rows (PADD; older file: none) */
    const unsigned char *lact;int nlact;      /* the levelled lists' scripted actors (LACT; older file: none) */
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
    case AWM_PUSHB:case AWM_GETL:case AWM_SETL:case AWM_SETLS:case AWM_AIWANDER:case AWM_GETPOS:
    case AWM_AIPACKAGE:return 1;
    case AWM_JMP:case AWM_JZ:case AWM_PUSHW:case AWM_GETG:case AWM_SETG:case AWM_SETGS:case AWM_GETJ:case AWM_SETJ:
    case AWM_JOURNAL:case AWM_REF:case AWM_PLAYSOUND:case AWM_PLAYSOUNDVP:case AWM_PLAYSOUND3D:case AWM_PLAYSOUND3DVP:
    case AWM_PLAYLOOP3D:case AWM_PLAYLOOP3DVP:case AWM_STOPSOUND:case AWM_SOUNDPLAYING:case AWM_STREAMMUSIC:
    case AWM_STARTSCRIPT:case AWM_STOPSCRIPT:case AWM_SCRIPTRUNNING:case AWM_DISTANCE:case AWM_ACTOR:
    case AWM_DEADCOUNT:case AWM_GETPCCELL:case AWM_PLAYERMOVE:return 2;
    case AWM_GETM:case AWM_SETM:case AWM_SETMS:case AWM_QUERY:case AWM_ITEM:case AWM_SPELL:case AWM_COMBAT:
    case AWM_JNEB:return 3;
    case AWM_JCMPB:return 4;
    case AWM_PUSHL:case AWM_PUSHF:case AWM_SAY:return 4;
    case AWM_MESSAGEBOX:return left>=5?4+2*p[4]:-1;
    case AWM_NOTYET:return left>=7?6+2*p[6]:-1;
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
        case AWM_NOTYET:
            if(U16(o)>=AWM_FUNCTIONS || (o[4]&0x1F)>AW_MWVM_STACK)return 0;
            if(!vm.fname[U16(o)])vm.fname[U16(o)]=(uint16_t)(U16(o+2)+1);
            break;
        case AWM_GETPCCELL:if((int)U16(o)>=vm.npcel)return 0;break;
        case AWM_GETPOS:if(o[0]>2)return 0;break;
        case AWM_AIPACKAGE:if(o[0]>1)return 0;break;
        case AWM_PLAYERMOVE:if((int)U16(o)>=vm.npmov)return 0;break;
        case AWM_MESSAGEBOX:if(o[2]>0x1F)return 0;break;
        case AWM_ACTOR:if(o[0]>AWM_VERB_RATIO || o[1]>=46)return 0;break;   /* 46: aw_actorstate.h AWA_STATS */
        case AWM_ITEM:if(o[0]>2 || U16(o+1)>=vm.naitm)return 0;break;
        case AWM_SPELL:if(o[0]>AWM_SPELL_BLIGHT_DISEASE || (o[0]<AWM_SPELL_COMMON_DISEASE && U16(o+1)>=vm.naspt))return 0;
            break;
        case AWM_COMBAT:if(o[0]>1 || (U16(o+1)!=AWM_NONE && (int)U16(o+1)>=vm.nobjs))return 0;break;
        case AWM_DEADCOUNT:if(U16(o)!=AWM_NONE && U16(o)>=vm.nactb)return 0;break;
        case AWM_AIWANDER:if(o[0]>10)return 0;break;
        case AWM_JCMPB:if(o[0]>5)return 0;break;
        }
        i+=1+k;
    }
    if(last!=AWM_END && last!=AWM_RET && last!=AWM_JMP)return 0;    /* the code cannot run off its end */
    for(i=0;i<n;i+=1+operand_bytes(code+i,n-i)){
        if(code[i]==AWM_JMP || code[i]==AWM_JZ || code[i]==AWM_JNEB || code[i]==AWM_JCMPB){
            /* the offset is the operand's last two bytes, counted from the instruction's end */
            int k=operand_bytes(code+i,n-i);
            long t=(long)i+1+k+S16(code+i+k-1);
            if(t<0 || t>=(long)n || !marks[t])return 0;
        }
    }
    return 1;
}
static aw_drsc_index_t drsc_index;static int drsc_index_state;   /* the DRSC index: 0 not tried, 1 built, -1 failed */
void AW_MwvmReset(void){if(vmp)memset(vmp,0,sizeof(*vmp));drsc_index_state=0;drsc_index.count=0;}
int AW_MwvmLoaded(void){return vmp && vm.loaded;}
/* GAME-RECORDER-FIGHT-SEED-61: Random's generator set from the gameplay recorder's seed at its frame 0 */
void AW_MwvmSeed(unsigned long seed){if(vmp)vm.rng=seed?(uint32_t)seed:0x2545F491u;}
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
    /* the actor table (v0.0.54): OACT is resident; ACTB, AITM and ASPT stay on disk, only their row counts here (a
     * file without them: no actor calls pass the load check) */
    vm.oact=section("OACT",&vm.noact,&len);
    {uint32_t off,n,b;
     vm.nactb=AW_MwvmSection("ACTB",&off,&n,&b)?n:0;vm.naitm=AW_MwvmSection("AITM",&off,&n,&b)?n:0;
     vm.naspt=AW_MwvmSection("ASPT",&off,&n,&b)?n:0;}
    if(!conf || !vm.glob || !vm.jrnl || !vm.snds || !vm.voic || !vm.musi || !vm.objs || !vm.scrp || !vm.strt ||
       !vm.code || vm.nscrp>MAX_SCRIPTS || vm.nglob>MAX_GLOBALS){AW_MwvmReset();return 0;}
    /* the GetPCCell rows (v0.0.54; a file without them: no GETPCCELL passes the load check): every row inside */
    vm.pcel=section("PCEL",&vm.npcel,&len);
    if(!vm.pcel || vm.npcel<0 || 4ul*(unsigned long)vm.npcel>len)vm.npcel=0;
    for(i=0;i<vm.npcel;i++){
        unsigned long off=u32(vm.pcel+4*i);
        if(off+4>len || off+4+2ul*U16(vm.pcel+off)+2ul*(U16(vm.pcel+off+2)&0x7FFF)>len){vm.npcel=0;break;}
    }
    /* the player's moves (v0.0.54; a file without them: no PLAYERMOVE passes the load check) */
    vm.pmov=section("PMOV",&vm.npmov,&len);
    if(!vm.pmov || vm.npmov<0 || 20ul*(unsigned long)vm.npmov>len)vm.npmov=0;
    /* the scripts a new game starts once (v0.0.62, NPC-STORY-DISABLED-AT-START-42; a file without them: none) */
    vm.newg=section("NEWG",&vm.nnewg,&len);
    if(!vm.newg || vm.nnewg<0 || 2ul*(unsigned long)vm.nnewg>len)vm.nnewg=0;
    /* the actors held on an object a script removes (v0.0.62, SCRIPTED-EVENT-FALLING-MAGE-61; older file: none) */
    vm.held=section("HELD",&vm.nheld,&len);
    if(!vm.held || vm.nheld<0 || 20ul*(unsigned long)vm.nheld>len)vm.nheld=0;
    /* the carried items whose script reads OnPCAdd (v0.0.62, CENSUS-INTRO-SCRIPTS-62; a file without them: none) */
    vm.padd=section("PADD",&vm.npadd,&len);
    if(!vm.padd || vm.npadd<0 || 8ul*(unsigned long)vm.npadd>len)vm.npadd=0;
    /* the scripted actors a levelled list can give (v0.0.62, MWSCRIPT-UNPLACED-ATTACH-62; a file without them: none) */
    vm.lact=section("LACT",&vm.nlact,&len);
    if(!vm.lact || vm.nlact<0 || 8ul*(unsigned long)vm.nlact>len)vm.nlact=0;
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
/* SCRIPTED-EVENT-PAST-DRAW-DISTANCE-62: the script's far-event trigger (game units, 0 none; awms.py SCRP) */
int AW_MwvmScriptFarTrigger(int s){return ON && s>=0 && s<vm.nscrp?(int)U16(vm.scrp+16*s+6):0;}
int AW_MwvmScriptName(int s){return ON && s>=0 && s<vm.nscrp?(int)U16(vm.scrp+16*s):-1;}
int AW_MwvmSound(int k,unsigned char hash[8],int *centis,int *volume,int *near_units,int *far_units){
    const unsigned char *r;if(!ON || k<0 || k>=vm.nsnds)return 0;
    r=vm.snds+18*k;memcpy(hash,r,8);*centis=(int)U16(r+8);*volume=r[10];
    *near_units=(int)U16(r+12);*far_units=(int)U16(r+14);return r[11]&1;
}
/* TOMB-MUSIC-OVER-AMBIENT-60: the sound is a dungeon ambience (flag 2, tools/mwscript/awms.py AMBIENCE_SOUNDS) */
int AW_MwvmSoundAmbience(int k){return ON && k>=0 && k<vm.nsnds && (vm.snds[18*k+11]&3)==3;}
int AW_MwvmVoice(int k,unsigned char hash[8],int *centis){
    const unsigned char *r;if(!ON || k<0 || k>=vm.nvoic)return 0;
    r=vm.voic+12*k;memcpy(hash,r,8);*centis=(int)U16(r+8);
    return r[0]|r[1]|r[2]|r[3]|r[4]|r[5]|r[6]|r[7]?1:0;
}
int AW_MwvmMusic(int k){return ON && k>=0 && k<vm.nmusi && (vm.musi[4*k+1]&1)?vm.musi[4*k]:-1;}
uint32_t AW_MwvmObjectReference(int k){return ON && k>=0 && k<vm.nobjs?u32(vm.objs+12*k):0;}
int AW_MwvmTopicName(int k){return ON && k>=0 && k<vm.njrnl?(int)U16(vm.jrnl+2*k):-1;}
int AW_MwvmTopicCount(void){return ON?vm.njrnl:0;}
int AW_MwvmObjectActor(int k){return ON && vm.oact && k>=0 && k<vm.noact?(int)U16(vm.oact+2*k):AWM_NONE;}
void AW_MwvmStateChanged(void){if(ON)vm.generation++;}
void AW_MwvmWake(int k){if(ON && k>=0 && k<vm.ninst)vm.inst[k].flags&=~AWI_QUIET;}
void AW_MwvmConfig(uint32_t *range,int *ops_frame,int *ops_run){
    *range=ON?vm.range:0;*ops_frame=ON?vm.ops_frame:0;*ops_run=ON?vm.ops_run:0;
}
int32_t AW_MwvmGlobalInt(int g){return ON && g>=0 && g<vm.nglob?vm.globals[g].i:0;}
float AW_MwvmGlobalFloat(int g){return ON && g>=0 && g<vm.nglob?vm.globals[g].f:0;}
int AW_MwvmGlobalCount(void){return ON?vm.nglob:0;}
uint32_t AW_MwvmGlobalBits(int g){return ON && g>=0 && g<vm.nglob?(uint32_t)vm.globals[g].i:0;}
uint32_t AW_MwvmGlobalStart(int g){return ON && g>=0 && g<vm.nglob?u32(vm.glob+8*g+4):0;}
void AW_MwvmGlobalSetBits(int g,uint32_t bits){if(ON && g>=0 && g<vm.nglob){vm.globals[g].i=(int32_t)bits;vm.generation++;}}
/* GLOB row: u8 type (0 short, 1 long, 2 float), u8 0, u16 name string, u32 initial value (tools/mwscript/awms.py) */
int AW_MwvmGlobalName(int g,int *type){
    if(!ON || g<0 || g>=vm.nglob)return -1;
    if(type)*type=vm.glob[8*g];
    return (int)U16(vm.glob+8*g+2);
}
const aw_mwvm_stats_t *AW_MwvmStats(void){return ON?&vm.stats:&no_stats;}
unsigned long AW_MwvmFunctionCalls(int f){return ON && f>=0 && f<AWM_FUNCTIONS?vm.fcalls[f]:0;}
int AW_MwvmFunctionName(int f){return ON && f>=0 && f<AWM_FUNCTIONS?(int)vm.fname[f]-1:-1;}
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
        /* MWSCRIPT-INVENTORY-HITONME-62: a held item's values are not parked (each visit starts them again; the
         * parking store stays for the placed objects) */
        if(AWB_HELD_KEY(in->reference)){in->flags=0;continue;}
        {parked_t *p=park_slot(in->reference,in->script);
         if(p)memcpy(&vm.park[p->at],&vm.cells[in->locals],p->count*sizeof(aw_mwcell_t));}
        in->flags=0;
    }
    while(vm.ninst>0 && !(vm.inst[vm.ninst-1].flags&AWI_USED))vm.ninst--;
    vm.low=0;vm.cursor=0;
}
/* CENSUS-INTRO-SCRIPTS-62: a script the host holds is not attached or started while held (the census office's
 * scripts while the old hand-written opening path is chosen, aw_census_legacy); the hold changes nothing
 * already attached, so the host sets it before a map's objects are attached. 1 kept (0: the list is full). */
int AW_MwvmScriptHeld(int script){
    int i;
    if(!ON)return 0;
    for(i=0;i<vm.nheld_scripts;i++)if(vm.story_held[i]==script)return 1;
    return 0;
}
int AW_MwvmScriptHold(int script,int hold){
    int i;
    if(!ON || script<0 || script>=vm.nscrp)return 0;
    for(i=0;i<vm.nheld_scripts && vm.story_held[i]!=script;i++);
    if(hold){
        if(i<vm.nheld_scripts)return 1;
        if(vm.nheld_scripts>=AW_MWVM_HELD_SCRIPTS)return 0;
        vm.story_held[vm.nheld_scripts++]=(int16_t)script;return 1;
    }
    if(i<vm.nheld_scripts)vm.story_held[i]=vm.story_held[--vm.nheld_scripts];
    return 1;
}
int AW_MwvmAttach(uint32_t reference,int script,int bind_flags,int entity,const float origin[3]){
    int k,n;parked_t *p;aw_mwvm_instance_t *in;
    if(!ON || script<0 || script>=vm.nscrp || !vm.runnable[script] || AW_MwvmScriptHeld(script))return -1;
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
/* An attached object left the loaded map (PositionCell to another place, v0.0.62): its values are parked as a map
 * change parks them, and it no longer runs here; attached again where it arrives. 1 when one was attached. */
int AW_MwvmDetach(uint32_t reference){
    int k;
    if(!ON || !reference)return 0;
    for(k=0;k<vm.ninst;k++){
        aw_mwvm_instance_t *in=&vm.inst[k];parked_t *p;
        if(!(in->flags&AWI_USED) || (in->flags&AWI_GLOBAL) || in->reference!=reference)continue;
        if(!AWB_HELD_KEY(reference) && (p=park_slot(in->reference,in->script))!=NULL)
            memcpy(&vm.park[p->at],&vm.cells[in->locals],p->count*sizeof(aw_mwcell_t));
        in->flags=0;in->entity=-1;
        return 1;
    }
    return 0;
}
/* The entity block of reference REF in a map's entity text (its "aw_ref" key): a pointer at its '{' and *LENGTH the
 * bytes up to and with its '}', or NULL. Pure text: the host's PositionCell reads it from the loaded map or from the
 * actor's home room map (v0.0.62). */
const char *AW_MwvmEntityBlock(const char *text,unsigned long length,uint32_t ref,unsigned long *block){
    char want[24];unsigned long i,n,open=0,start=0;int depth=0,inside=0,quoted=0,strings=0,key_ref=0;
    if(!text || !ref)return NULL;
    {char digits[24];uint32_t v=ref;int d=0;
     while(v){digits[d++]=(char)('0'+v%10);v/=10;}
     for(n=0;d>0;)want[n++]=digits[--d];}
    for(i=0;i<length && text[i];i++){
        if(text[i]=='"'){
            if(!quoted){quoted=1;start=i+1;continue;}
            quoted=0;
            /* a string ended: an even one is a key, an odd one its value; the key "aw_ref", its value the number */
            if(depth && !(strings&1))key_ref=i-start==6 && !memcmp(text+start,"aw_ref",6);
            else if(depth && key_ref && i-start==n && !memcmp(text+start,want,n))inside=1;
            if(depth)strings++;
            continue;
        }
        if(quoted)continue;
        if(text[i]=='{' && !depth){open=i;depth=1;inside=0;strings=0;continue;}
        if(text[i]=='}' && depth){
            depth=0;
            if(inside){*block=i-open+1;return text+open;}
        }
    }
    return NULL;
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
    if(!ON || script<0 || script>=vm.nscrp || !vm.runnable[script] || AW_MwvmScriptHeld(script))return;
    k=global_instance(script,1);
    if(k>=0)vm.inst[k].flags|=AWI_RUNNING;
}
/* a new game begins (any opening): the scripts Main starts under CharGenState == 1 in the original (Startup and
 * VampireCheck), each once; a script that cannot run (hand-written, broken, out of range) is left out by StartScript */
int AW_MwvmNewGame(void){
    int i,started=0,s;
    if(!ON)return 0;
    for(i=0;i<vm.nnewg;i++){
        s=(int)U16(vm.newg+2*i);
        if(s>=0 && s<vm.nscrp && vm.runnable[s]){AW_MwvmStartScript(s);started++;}
    }
    if(started)vm.generation++;
    return started;
}
/* the HELD rows (aw_mwvm.h): sorted by actor, so a lookup is a binary search */
int AW_MwvmHeldCount(void){return vmp && vm.loaded?vm.nheld:0;}
int AW_MwvmHeld(int i,uint32_t *actor,uint32_t *support,float position[3]){
    const unsigned char *r;
    if(!vmp || !vm.loaded || i<0 || i>=vm.nheld)return 0;
    r=vm.held+20*i;
    if(actor)*actor=u32(r);
    if(support)*support=u32(r+4);
    if(position){position[0]=f32(r+8);position[1]=f32(r+12);position[2]=f32(r+16);}
    return 1;
}
int AW_MwvmHeldFind(uint32_t actor){
    int low=0,high=AW_MwvmHeldCount()-1;
    while(low<=high){
        int mid=(low+high)/2;uint32_t a=u32(vm.held+20*mid);
        if(a<actor)low=mid+1;else if(a>actor)high=mid-1;else return mid;
    }
    return -1;
}
/* --- the scripts' own state for a save (CELL-CHANGES-59 slice 5, aw_mwvm.h) --- */
static int attached_instance(uint32_t ref){
    int k;
    for(k=0;k<vm.ninst;k++)if((vm.inst[k].flags&(AWI_USED|AWI_GLOBAL))==AWI_USED && vm.inst[k].reference==ref)return k;
    return -1;
}
int AW_MwvmStartsAtLoad(int script){
    int i;
    if(!ON)return 0;
    for(i=0;i<vm.nstrt;i++)if((int)U16(vm.strt+2*i)==script)return 1;
    return 0;
}
int AW_MwvmLocalCount(int script){return ON && script>=0 && script<vm.nscrp?nlocals(script):0;}
int AW_MwvmScriptRunning(int script){
    int k=ON && script>=0 && script<vm.nscrp?vm.global_instance[script]:-1;
    return k>=0 && (vm.inst[k].flags&AWI_RUNNING)?1:0;
}
void AW_MwvmLocalsEach(void (*fn)(void *user,uint32_t reference,int script,int global,int running,
                                  const aw_mwcell_t *cells,int count),void *user){
    int k,s;
    if(!ON || !fn)return;
    for(k=0;k<vm.ninst;k++){
        const aw_mwvm_instance_t *in=&vm.inst[k];
        if((in->flags&(AWI_USED|AWI_GLOBAL))==AWI_USED && in->reference)
            fn(user,in->reference,in->script,0,0,&vm.cells[in->locals],nlocals(in->script));
    }
    for(k=0;k<vm.nparked;k++){
        const parked_t *p=&vm.parked[k];
        if(attached_instance(p->reference)<0)fn(user,p->reference,p->script,0,0,&vm.park[p->at],p->count);
    }
    for(s=0;s<vm.nscrp;s++)
        if((k=vm.global_instance[s])>=0)
            fn(user,0,s,1,(vm.inst[k].flags&AWI_RUNNING)?1:0,&vm.cells[vm.inst[k].locals],nlocals(s));
}
void AW_MwvmLocalsReset(void){
    int k;
    if(!ON)return;
    vm.nparked=0;vm.park_used=0;vm.warned_park=0;
    for(k=0;k<vm.ninst;k++){
        aw_mwvm_instance_t *in=&vm.inst[k];
        if(!(in->flags&AWI_USED))continue;
        memset(&vm.cells[in->locals],0,nlocals(in->script)*sizeof(aw_mwcell_t));
        in->flags&=~AWI_QUIET;in->flags|=AWI_CELLCHANGED;
        if(in->flags&AWI_GLOBAL){
            if(AW_MwvmStartsAtLoad(in->script))in->flags|=AWI_RUNNING;else in->flags&=~AWI_RUNNING;
        }
    }
    vm.generation++;
}
int AW_MwvmLocalSet(uint32_t reference,int script,int slot,uint32_t bits){
    int k;parked_t *p;
    if(!ON || !reference || script<0 || script>=vm.nscrp || slot<0 || slot>=nlocals(script))return 0;
    if((k=attached_instance(reference))>=0){
        if(vm.inst[k].script!=script)return 0;
        vm.cells[vm.inst[k].locals+slot].i=(int32_t)bits;vm.inst[k].flags&=~AWI_QUIET;
        return 1;
    }
    if(!(p=park_slot(reference,script)))return 0;
    vm.park[p->at+slot].i=(int32_t)bits;
    return 1;
}
int AW_MwvmLocalGet(uint32_t reference,int slot,int *script,aw_mwcell_t *out){
    int k=ON?attached_instance(reference):-1;parked_t *p;
    if(k>=0){
        if(slot<0 || slot>=nlocals(vm.inst[k].script))return 0;
        *script=vm.inst[k].script;*out=vm.cells[vm.inst[k].locals+slot];return 1;
    }
    if(!ON || !(p=find_parked(reference)) || slot<0 || slot>=p->count)return 0;
    *script=p->script;*out=vm.park[p->at+slot];
    return 1;
}
/* OnPCAdd (v0.0.62, CENSUS-INTRO-SCRIPTS-62; OpenMW 0.51: the local OnPCAdd of an item's script reads 1 once the item
 * is in the player's inventory): the PADD row of the item whose folded id hashes to HASH: its script and the slot.
 * 1 found (binary search on the resident rows; nothing read from disk). */
int AW_MwvmPcAddRow(uint32_t hash,int *script,int *slot){
    int low=0,high=ON?vm.npadd-1:-1;
    while(low<=high){
        int mid=(low+high)/2;uint32_t h=u32(vm.padd+8*mid);
        if(h<hash)low=mid+1;else if(h>hash)high=mid-1;
        else{*script=(int)U16(vm.padd+8*mid+4);*slot=vm.padd[8*mid+6];return 1;}
    }
    return 0;
}
/* The item entered the player's inventory: its script's OnPCAdd reads 1 from its next run. The placed reference
 * REFERENCE the player took keeps running its own values (a book read on the table, then taken); without one, the
 * item's script runs as it is carried, one instance per script (the carried ring). 1 an attached placement, 2 the
 * carried instance, 0 none (not runnable, held, or the slot out of range). */
/* MWSCRIPT-UNPLACED-ATTACH-62: SLOT AW_MWVM_NO_SLOT (a PADD row of a script with no OnPCAdd local): the item's
 * script runs while carried (OpenMW 0.51 runs the scripts of the items in the player's inventory), nothing is set.
 * A carried instance that already runs is left as it is (no wake, no state change). */
int AW_MwvmPcAdd(uint32_t reference,int script,int slot){
    int k,none=slot==AW_MWVM_NO_SLOT;
    if(!ON || script<0 || script>=vm.nscrp || !vm.runnable[script] || AW_MwvmScriptHeld(script) || slot<0 ||
       (!none && slot>=nlocals(script)))return 0;
    if(reference && (k=attached_instance(reference))>=0 && vm.inst[k].script==script){
        if(none)return 1;
        vm.cells[vm.inst[k].locals+slot].i=1;vm.inst[k].flags&=~AWI_QUIET;vm.generation++;return 1;
    }
    if((k=global_instance(script,1))<0)return 0;
    if(none && (vm.inst[k].flags&AWI_RUNNING))return 2;
    if(!none){vm.cells[vm.inst[k].locals+slot].i=1;vm.generation++;}
    vm.inst[k].flags|=AWI_RUNNING|(none?AWI_CELLCHANGED:0);vm.inst[k].flags&=~AWI_QUIET;
    return 2;
}
/* The last item of SCRIPT left the player's inventory: its carried instance stops (its values stay, as OpenMW keeps
 * an item's locals with the item). 1 when one was running. */
int AW_MwvmCarriedStop(int script){
    int k;
    if(!ON || script<0 || script>=vm.nscrp || (k=global_instance(script,0))<0 || !(vm.inst[k].flags&AWI_RUNNING))return 0;
    vm.inst[k].flags&=~AWI_RUNNING;
    return 1;
}
/* 1 when an object attached to the loaded map runs SCRIPT (a placement the player took keeps its own instance) */
int AW_MwvmScriptAttached(int script){
    int k;
    if(!ON)return 0;
    for(k=0;k<vm.ninst;k++)
        if((vm.inst[k].flags&(AWI_USED|AWI_GLOBAL))==AWI_USED && (int)vm.inst[k].script==script)return 1;
    return 0;
}
/* LACT (MWSCRIPT-UNPLACED-ATTACH-62): the script of the NPC or creature record whose folded id hashes to HASH (the
 * actor table's base hash), when a levelled list can give it; 1 found (a binary search on the resident rows). */
int AW_MwvmLevelledScript(uint32_t hash,int *script){
    int low=0,high=ON?vm.nlact-1:-1;
    while(low<=high){
        int mid=(low+high)/2;uint32_t h=u32(vm.lact+8*mid);
        if(h<hash)low=mid+1;else if(h>hash)high=mid-1;
        else{*script=(int)U16(vm.lact+8*mid+4);return *script<vm.nscrp;}
    }
    return 0;
}
int AW_MwvmGlobalScriptSet(int script,int running){
    int k;
    if(!ON || script<0 || script>=vm.nscrp || !vm.runnable[script])return 0;
    if((k=global_instance(script,running))<0)return !running;    /* stopped and never made: nothing to keep */
    if(running)vm.inst[k].flags|=AWI_RUNNING;else vm.inst[k].flags&=~AWI_RUNNING;
    vm.inst[k].flags&=~AWI_QUIET;
    return 1;
}
int AW_MwvmGlobalScriptLocal(int script,int slot,uint32_t bits){
    int k;
    if(!ON || script<0 || script>=vm.nscrp || !vm.runnable[script] || slot<0 || slot>=nlocals(script) ||
       (k=global_instance(script,1))<0)return 0;
    vm.cells[vm.inst[k].locals+slot].i=(int32_t)bits;
    return 1;
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
/* GetPCCell: the player's cell against a PCEL row (rooms by stable number, outdoor cells by grid; built at load
 * time from the names, so nothing compares text here) */
static int pc_cell(int row){
    const unsigned char *r;int kind,x=0,y=0,i,rooms,outside;
    if(!vm.host || !vm.host->player_cell || !(kind=vm.host->player_cell(&x,&y)))return 0;
    r=vm.pcel+u32(vm.pcel+4*row);rooms=(int)U16(r);outside=(int)(U16(r+2)&0x7FFF);r+=4;
    if(kind==2){for(i=0;i<rooms;i++)if((int)U16(r+2*i)==x)return 1;return 0;}
    for(r+=2*rooms,i=0;i<outside;i++)if((signed char)r[2*i]==x && (signed char)r[2*i+1]==y)return 1;
    return 0;
}
static int run(int k){
    aw_mwvm_instance_t *in=&vm.inst[k];
    const unsigned char *s=vm.scrp+16*in->script,*pc=vm.code+u32(s+8);
    const aw_mwvm_host_t *h=vm.host;
    aw_mwcell_t stack[AW_MWVM_STACK+1],*sp=stack,*locals=&vm.cells[in->locals];
    int target=AW_MWVM_SELF,ops=0,changed=0,acted=0,limit=vm.ops_run;
    /* CellChanged reads 1 on this run and 0 on the next: the next one runs too ("if ( CellChanged == 0 )" starts
     * the sound markers' loops), so CellChanged needs no VOLATILE */
    int cell_changed=(in->flags&AWI_CELLCHANGED)!=0;
    float elapsed=vm.now-in->last_run;
    if(elapsed<=0)elapsed=vm.dt;     /* the first run after attaching: this frame's time */
    for(;;){
        unsigned op=*pc++;
#ifdef AW_MWVM_PROFILE
        AW_MWVM_PROFILE(op);    /* native measurements only (the bench's opcode pairs); never in the engine build */
#endif
        if(++ops>limit){
            vm.stats.aborted++;
            if(h && h->warn)h->warn("a run reached the opcode limit",AW_MwvmScriptName(in->script));
            break;
        }
        switch(op){
        case AWM_END:case AWM_RET:goto done;
        case AWM_JMP:pc+=2+S16(pc);break;
        case AWM_JZ:--sp;pc+=sp->i?2:2+S16(pc);break;
        case AWM_JNEB:--sp;pc+=sp->i==(int32_t)(int8_t)pc[0]?3:3+S16(pc+1);break;
        case AWM_JCMPB:{
            int32_t v=(--sp)->i,c=(int32_t)(int8_t)pc[1];int ok;
            switch(pc[0]){case 0:ok=v==c;break;case 1:ok=v!=c;break;case 2:ok=v<c;break;case 3:ok=v<=c;break;
                          case 4:ok=v>c;break;default:ok=v>=c;break;}
            pc+=ok?4:4+S16(pc+2);break;}
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
            /* the import route: counted by function number; the host may carry it out by that number with the
             * arguments as the script gave them; else logged once, nothing done, 0 read */
            int fn=(int)U16(pc),flags=pc[4],n=flags&0x1F,done;aw_mwcell_t r;
            sp-=n;vm.stats.notyet_calls++;vm.fcalls[fn]++;r.i=0;
            done=h && h->call?h->call(k,target,fn,sp,n,pc+6,pc[5],&r):0;
            if(done){vm.stats.host_calls++;if(done!=AW_MWVM_CALL_READ)acted=1;in=&vm.inst[k];}
            else{log_notyet((int)U16(pc+2),in->script);r.i=0;}   /* did nothing: not an action for the quiet rule */
            if(flags&0x80)*sp++=r;
            pc+=6+2*pc[5];target=AW_MWVM_SELF;
            break;}
        case AWM_GETPCCELL:sp->i=pc_cell((int)U16(pc));sp++;pc+=2;target=AW_MWVM_SELF;break;
        case AWM_GETPOS:sp->f=h && h->position?h->position(k,target,pc[0]):0.0f;sp++;pc++;target=AW_MWVM_SELF;break;
        case AWM_AIPACKAGE:
            sp->i=h && h->ai_package?h->ai_package(k,target,pc[0]):(pc[0]?0:-1);sp++;pc++;target=AW_MWVM_SELF;break;
        case AWM_PLAYERMOVE:{
            const unsigned char *m=vm.pmov+20*U16(pc);float at[3];
            at[0]=f32(m+4);at[1]=f32(m+8);at[2]=f32(m+12);pc+=2;
            if(h && h->player_move)h->player_move(k,m[0],(int)U16(m+2),at,f32(m+16));
            acted=1;target=AW_MWVM_SELF;break;}
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
        /* the actor record (aw_actorstate.h): a change is state other scripts read, so the generation moves and
         * quiet scripts that read actors wake, as for globals; the engine moves it too (a hit, a death) */
        case AWM_ACTOR:{
            int verb=pc[0],stat=pc[1];aw_mwcell_t v;pc+=2;
            if(verb==AWM_VERB_SET || verb==AWM_VERB_MOD || verb==AWM_VERB_MODCURRENT){
                v=*--sp;
                if(h && h->actor)h->actor(k,target,verb,stat,v);
                changed=1;acted=1;vm.generation++;
            }else{
                v.i=0;
                *sp++=h && h->actor?h->actor(k,target,verb,stat,v):v;
            }
            target=AW_MWVM_SELF;break;}
        case AWM_ITEM:{
            int verb=pc[0],item=(int)U16(pc+1);pc+=3;
            if(verb==0){sp->i=h && h->item?h->item(k,target,0,item,0):0;sp++;}
            else{--sp;if(h && h->item)h->item(k,target,verb,item,sp->i);changed=1;acted=1;vm.generation++;}
            target=AW_MWVM_SELF;break;}
        case AWM_SPELL:{
            int verb=pc[0],spell=(int)U16(pc+1);pc+=3;
            if(verb==0 || verb>=AWM_SPELL_COMMON_DISEASE){sp->i=h && h->spell?h->spell(k,target,verb,spell):0;sp++;}
            else{if(h && h->spell)h->spell(k,target,verb,spell);changed=1;acted=1;vm.generation++;}
            target=AW_MWVM_SELF;break;}
        case AWM_COMBAT:{
            int verb=pc[0],other=U16(pc+1)==AWM_NONE?AW_MWVM_PLAYER:(int)U16(pc+1);pc+=3;
            if(h && h->combat)h->combat(k,target,verb,other);
            acted=1;target=AW_MWVM_SELF;break;}
        case AWM_AIWANDER:{
            int count=3+pc[0],i;int32_t values[13];pc++;
            sp-=count;
            for(i=0;i<count;i++)values[i]=sp[i].i;
            if(h && h->wander)h->wander(k,target,values,count);
            acted=1;target=AW_MWVM_SELF;break;}
        case AWM_DEADCOUNT:
            sp->i=h && h->dead_count && U16(pc)!=AWM_NONE?h->dead_count((int)U16(pc)):0;sp++;pc+=2;
            target=AW_MWVM_SELF;break;
        default:goto done;   /* unreachable: every opcode was checked at load */
        }
    }
done:
    in=&vm.inst[k];
    in->last_run=vm.now;
    if(changed || acted || cell_changed)in->flags&=~AWI_QUIET;else in->flags|=AWI_QUIET;
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
/* A dialogue result script (DIALOGUE-COMPLETE-58): SCRIPT (a _dlg_N row of DRSC) runs once on the speaker's instance
 * (REFERENCE, its SPEAKER script: the result reads and sets the speaker's locals, as the original runs it in the
 * speaker's script context); a speaker not attached now runs on its parked locals (made if needed) through a
 * scratch instance; no speaker script: no locals. 1 ran. */
int AW_MwvmRunDialogue(int script,uint32_t reference,int speaker){
    int k,n,ok;parked_t *p=NULL;aw_mwvm_instance_t *in;
    if(!ON || script<0 || script>=vm.nscrp)return 0;
    for(k=0;k<vm.ninst;k++){
        in=&vm.inst[k];
        if((in->flags&(AWI_USED|AWI_GLOBAL))==AWI_USED && reference && in->reference==reference &&
           (int)in->script==speaker){
            in->script=(uint16_t)script;ok=1;run(k);in->script=(uint16_t)speaker;vm.stats.dialogue_runs++;
            return ok;
        }
    }
    n=nlocals(script);
    if(speaker>=0 && speaker<vm.nscrp && reference)p=park_slot(reference,speaker);
    if(vm.high-n<vm.low || (k=new_instance())<0)return 0;
    vm.high-=n;in=&vm.inst[k];
    in->script=(uint16_t)script;in->flags=AWI_USED|AWI_GLOBAL;in->reference=reference;in->locals=vm.high;in->last_run=vm.now;
    if(p && p->count>=n)memcpy(&vm.cells[vm.high],&vm.park[p->at],n*sizeof(aw_mwcell_t));
    else memset(&vm.cells[vm.high],0,n*sizeof(aw_mwcell_t));
    run(k);
    if(p && p->count>=n)memcpy(&vm.park[p->at],&vm.cells[vm.high],n*sizeof(aw_mwcell_t));
    vm.high+=n;in->flags=0;
    while(vm.ninst>0 && !(vm.inst[vm.ninst-1].flags&AWI_USED))vm.ninst--;
    vm.stats.dialogue_runs++;
    return 1;
}
/* MW-CONSOLE-COMMANDS-62: a console line's target as the instance a script line runs on (its REFERENCE and ENTITY),
 * so the host finds it as it finds a script's own reference (AW_MWVM_SELF); no locals, nothing run; given back with
 * AW_MwvmScratchEnd before the next frame. The instance, -1 none free. */
int AW_MwvmScratch(uint32_t reference,int entity){
    int k;aw_mwvm_instance_t *in;
    if(!ON || !reference || (k=new_instance())<0)return -1;
    in=&vm.inst[k];
    memset(in,0,sizeof(*in));
    in->script=0;in->flags=AWI_USED|AWI_GLOBAL;in->reference=reference;in->entity=entity;in->locals=vm.high;
    in->last_run=vm.now;
    return k;
}
void AW_MwvmScratchEnd(int k){
    if(!ON || k<0 || k>=vm.ninst)return;
    vm.inst[k].flags=0;
    while(vm.ninst>0 && !(vm.inst[vm.ninst-1].flags&AWI_USED))vm.ninst--;
}
uint32_t AW_MwvmTextHash(const char *text,int length){
    uint32_t h=0x811C9DC5u;int i;
    for(i=0;i<length;i++){h^=(unsigned char)text[i];h*=0x01000193u;}
    return h;
}
/* The DRSC row of a result text (its HASH and LENGTH; the section on disk read through READ at file offsets): of the
 * rows for the text, the one compiled with SPEAKER (the speaker's attached script, -1 none) or, failing that, the
 * first; its script, ROW_SPEAKER (the script whose locals it was compiled with, -1 none) and BROKEN. -1 none. */
/* MWSCRIPT-RESULT-LONG-FRAME-62: every AW_DRSC_BLOCK-th row's key, read once (one 12-byte read per block); 1 built.
 * A section of more rows than the index holds: not built (the whole search on disk, as before). */
int AW_MwvmDialogueIndexBuild(int (*read)(void *user,uint32_t offset,void *out,uint32_t bytes),void *user,
                              uint32_t offset,uint32_t rows,aw_drsc_index_t *index){
    uint32_t k,n=(rows+AW_DRSC_BLOCK-1)/AW_DRSC_BLOCK;unsigned char r[12];
    index->count=0;
    if(!read || !rows || n>AW_DRSC_INDEX)return 0;
    for(k=0;k<n;k++){
        if(!read(user,offset+12u*k*AW_DRSC_BLOCK,r,12)){index->count=0;return 0;}
        index->hash[k]=u32(r);index->length[k]=U16(r+4);
    }
    index->count=(int)n;
    return 1;
}
int AW_MwvmDialogueIndex(int (*read)(void *user,uint32_t offset,void *out,uint32_t bytes),void *user){
    uint32_t off,rows,bytes;
    if(drsc_index_state)return drsc_index_state>0;
    drsc_index_state=AW_MwvmSection("DRSC",&off,&rows,&bytes) && AW_MwvmDialogueIndexBuild(read,user,off,rows,&drsc_index)?1:-1;
    return drsc_index_state>0;
}
int AW_MwvmFindDialogue(int (*read)(void *user,uint32_t offset,void *out,uint32_t bytes),void *user,uint32_t hash,
                        int length,int speaker,int *row_speaker,int *broken){
    uint32_t off,rows,bytes;
    *row_speaker=-1;*broken=0;
    if(!read || !AW_MwvmSection("DRSC",&off,&rows,&bytes) || !rows)return -1;
    return AW_MwvmFindDialogueRows(read,user,off,rows,drsc_index_state>0?&drsc_index:NULL,hash,length,speaker,
                                   row_speaker,broken);
}
int AW_MwvmFindDialogueRows(int (*read)(void *user,uint32_t offset,void *out,uint32_t bytes),void *user,
                            uint32_t off,uint32_t rows,const aw_drsc_index_t *index,uint32_t hash,int length,
                            int speaker,int *row_speaker,int *broken){
    uint32_t lo=0,hi=rows,mid;unsigned char r[12];int i,chosen=-1,want=length>0xFFFF?0xFFFF:length;
    *row_speaker=-1;*broken=0;
    if(!read || !rows)return -1;
    if(index && index->count>0){   /* the first indexed row at or after the key: the answer is in the block before it */
        int a=0,b=index->count;
        while(a<b){int m=(a+b)/2;
            if(index->hash[m]<hash || (index->hash[m]==hash && (int)index->length[m]<want))a=m+1;else b=m;}
        if(a>0)lo=(uint32_t)(a-1)*AW_DRSC_BLOCK+1;
        if(a<index->count)hi=(uint32_t)a*AW_DRSC_BLOCK;
    }
    while(lo<hi){   /* the first row at or after (hash, length) */
        uint32_t h;int n;
        mid=(lo+hi)/2;
        if(!read(user,off+12u*mid,r,12))return -1;
        h=u32(r);n=(int)U16(r+4);
        if(h<hash || (h==hash && n<want))lo=mid+1;else hi=mid;
    }
    for(i=(int)lo;(uint32_t)i<rows;i++){
        int sp,script,b=i/AW_DRSC_BLOCK;
        if(index && i%AW_DRSC_BLOCK==0 && b<index->count &&   /* the next block's first row known: no read for it */
           (index->hash[b]!=hash || (int)index->length[b]!=want))break;
        if(!read(user,off+12u*(uint32_t)i,r,12) || u32(r)!=hash || (int)U16(r+4)!=want)break;
        sp=(int)U16(r+6);script=(int)U16(r+8);
        if(chosen<0 || sp==speaker || (sp==0xFFFF && speaker<0)){
            chosen=script;*row_speaker=sp==0xFFFF?-1:sp;*broken=U16(r+10)&1;
            if(sp==speaker)break;
        }
    }
    return chosen;
}
