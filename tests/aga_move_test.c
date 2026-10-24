/* SPDX-License-Identifier: GPL-2.0-or-later
 * The movement speed in the engine (aw_move.c with sv_user.c's SV_AirMove and
 * SV_WaterMove): superspeed gives exactly the old fixed speeds, the default
 * gives the original's speed from the LIVE character sheet (raising Athletics
 * or Speed raises it at once), the settings come from combat/settings.txt,
 * running and jumping cost fatigue, and the console command and variable are
 * registered (docs/PLAYER_MOVEMENT.md).
 */
#include "quakedef.h"
#include "aw_move.h"
#include "aw_character.h"
#include "aw_inventory.h"
#include <assert.h>

extern edict_t *sv_player;
extern float *velocity,*angles,*origin;
extern usercmd_t cmd;
extern float wishspeed;
extern void SV_AirMove(void);
extern void SV_WaterMove(void);
extern cvar_t sv_maxspeed,sv_accelerate;
extern void (*aw_move_after)(float seconds);
cvar_t sv_friction={"sv_friction","4"},sv_stopspeed={"sv_stopspeed","100"};
cvar_t cl_forwardspeed={"cl_forwardspeed","120"},cl_backspeed={"cl_backspeed","120"};
cvar_t cl_sidespeed={"cl_sidespeed","120"},cl_upspeed={"cl_upspeed","200"},cl_movespeedkey={"cl_movespeedkey","1.8"};
kbutton_t in_speed;
double host_frametime;
server_t sv;
server_static_t svs;
aw_character_t aw_character;
aw_race_t aw_races[16];
int aw_race_count;
aw_state_t aw_state;
trace_t SV_Move(vec3_t start,vec3_t mins,vec3_t maxs,vec3_t end,int type,edict_t *passedict)
{trace_t t;memset(&t,0,sizeof t);t.fraction=1;(void)start;(void)mins;(void)maxs;(void)end;(void)type;(void)passedict;return t;}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
void Con_Printf(char *fmt,...){va_list v;va_start(v,fmt);vprintf(fmt,v);va_end(v);}

/* The registry: what AW_MoveInit registers. */
static cvar_t *variables[4];static int variable_count;
static char commands[4][32];static xcommand_t handlers[4];static int command_count;
void Cvar_RegisterVariable(cvar_t *v){v->value=(float)atof(v->string);variables[variable_count++]=v;}
void Cvar_SetValue(char *name,float value){int i;for(i=0;i<variable_count;i++)if(!strcmp(variables[i]->name,name))variables[i]->value=value;}
void Cmd_AddCommand(char *name,xcommand_t f){strcpy(commands[command_count],name);handlers[command_count++]=f;}
static int argc;static char *argv[4];
int Cmd_Argc(void){return argc;}
char *Cmd_Argv(int i){return i<argc?argv[i]:"";}
static void run(const char *a,const char *b){
    int i;argc=0;argv[argc++]=(char *)a;if(b)argv[argc++]=(char *)b;
    for(i=0;i<command_count;i++)if(!strcmp(commands[i],a)){handlers[i]();return;}
    assert(0);
}

/* combat/settings.txt as the builder writes it (combat lines, then the move lines). */
static char settings_text[4096];
int COM_FOpenFile(char *name,FILE **file){
    FILE *f;int n=(int)strlen(settings_text);
    *file=NULL;
    if(strcmp(name,"combat/settings.txt") || !n)return -1;
    f=tmpfile();fwrite(settings_text,1,n,f);rewind(f);*file=f;return n;
}
/* The catalogue: one owned item, a cuirass of 30. */
int AW_InventoryRead(const char *id,aw_inventory_item_t *out){
    memset(out,0,sizeof *out);
    if(strcmp(id,"cuirass"))return 0;
    out->weight=30;return 1;
}
/* The player's fatigue as the combat module holds it. */
static float fatigue=200;static int knocked;
int AW_CombatPlayerKnocked(void){return knocked;}
float AW_CombatPlayerFatigue(float *maximum){if(maximum)*maximum=200;return fatigue;}
void AW_CombatPlayerFatigueLoss(float loss){fatigue=AW_MoveFatigueAfter(fatigue,loss);}

static int near(float a,float b){return fabs(a-b)<=.002f*(fabs(b)>1?fabs(b):1);}
/* The wished ground speed for this command (SV_AirMove, airborne so only the wish is read). */
static float ground(float forward,float side,int shift){
    VectorCopy(vec3_origin,velocity);
    cmd.forwardmove=forward*(shift?cl_movespeedkey.value:1);cmd.sidemove=side*(shift?cl_movespeedkey.value:1);
    in_speed.state=shift?1:0;
    SV_AirMove();
    return wishspeed;
}
static float swim(float forward,int shift){
    int i;
    VectorCopy(vec3_origin,velocity);cmd.forwardmove=forward*(shift?cl_movespeedkey.value:1);cmd.sidemove=0;cmd.upmove=0;
    in_speed.state=shift?1:0;
    for(i=0;i<200;i++)SV_WaterMove();       /* the swimmer reaches the wished speed */
    return Length(velocity);
}

int main(void){
    edict_t player;client_t client;aw_move_settings_t originals;int i,n;
    memset(&player,0,sizeof player);memset(&cmd,0,sizeof cmd);memset(&client,0,sizeof client);
    sv_player=&player;velocity=player.v.velocity;angles=player.v.angles;origin=player.v.origin;
    client.edict=&player;svs.clients=&client;svs.maxclients=1;sv.active=true;
    player.v.health=100;player.v.movetype=MOVETYPE_WALK;
    sv_friction.value=4;sv_maxspeed.value=320;sv_accelerate.value=10;host_frametime=.05;
    cl_forwardspeed.value=cl_backspeed.value=cl_sidespeed.value=120;cl_upspeed.value=200;cl_movespeedkey.value=1.8f;

    /* No hooks yet: the plain Quake wish, the old numbers: walk 120, run 216, diagonal walk 169.7. */
    assert(near(ground(120,0,0),120) && near(ground(120,0,1),216) && near(ground(120,120,0),169.706f));
    {float old_swim=swim(120,0);assert(near(old_swim,84));}        /* 120 x 0.7 */

    /* The settings file the builder writes: every move setting with the original's value, the race weights. */
    AW_MoveSettingsDefault(&originals);
    n=sprintf(settings_text,"AWCS1\nfFatigueBase 1.25\n");
    for(i=0;i<AW_MOVE_SETTING_COUNT;i++)n+=sprintf(settings_text+n,"move %s %g\n",AW_MoveSettingName(i),((float *)&originals)[i]);
    n+=sprintf(settings_text+n,"moverace 1 1 breton\nmoverace 1.25 1 nord\nmoverace 1 0.95 dark elf\nsound miss combat/miss.wav");

    /* Registration: one variable (aw_superspeed, default off, not saved) and one command. */
    AW_MoveInit();
    assert(variable_count==1 && !strcmp(variables[0]->name,"aw_superspeed") && !variables[0]->archive);
    assert(variables[0]->value==0 && !AW_MoveSuperspeed());
    assert(command_count==1 && !strcmp(commands[0],"superspeed"));

    /* A fresh character: Nord male Barbarian, Speed 50, Strength 60, Athletics 35, Acrobatics 15. */
    strcpy(aw_races[0].id,"Breton");strcpy(aw_races[1].id,"Nord");strcpy(aw_races[2].id,"Dark Elf");aw_race_count=3;
    aw_character.valid=1;aw_character.race=1;aw_character.female=0;
    for(i=0;i<8;i++)aw_character.attributes[i]=40;
    aw_character.attributes[0]=50;aw_character.modifiers[0]=10;      /* Strength 60 */
    aw_character.attributes[4]=40;aw_character.modifiers[4]=10;      /* Speed 50 */
    for(i=0;i<27;i++)aw_character.skills[i]=5;
    aw_character.skills[8]=35;aw_character.skills[20]=15;
    {aw_move_inputs_t in;AW_MovePlayerInputs(&in);
     assert(in.speed==50 && in.strength==60 && in.athletics==35 && in.acrobatics==15 && in.scale==1.25f && in.carried==0);}

    /* The original's speeds: walk 46.875, run 98.4375 units/s; diagonal input is not faster. */
    assert(near(ground(120,0,0),46.875f) && near(ground(120,0,1),98.4375f));
    assert(near(ground(120,120,0),46.875f) && near(ground(-120,0,0),46.875f));
    assert(near(ground(0,120,0),35.15625f));                  /* sideways: x 0.75 */
    assert(near(ground(60,0,0),23.4375f));                    /* half input */
    assert(ground(0,0,0)==0);
    /* Swimming: 150 x 0.535 x 1.25 x 0.25. */
    assert(near(swim(120,0),25.078125f));

    /* LIVE: the sheet changes, the speed follows on the next move. */
    aw_character.skills[8]=60;assert(near(ground(120,0,1),352.5f*1.25f*.25f));
    aw_character.modifiers[4]=30;assert(near(ground(120,0,0),170*1.25f*.25f));
    aw_character.damage[4]=20;assert(near(ground(120,0,0),46.875f));   /* Speed damaged back to 50 */
    aw_character.damage[4]=0;aw_character.modifiers[4]=10;aw_character.skills[8]=35;
    aw_character.female=1;assert(near(ground(120,0,0),37.5f));          /* Nord female weight 1 */
    aw_character.female=0;
    /* Load: the cuirass, 30 of 300 (5 x Strength 60): walk x (1 - 0.3 x 0.1). */
    strcpy(aw_state.values[AW_ITEM][0].id,"cuirass");aw_state.values[AW_ITEM][0].value=1;aw_state.count[AW_ITEM]=1;
    assert(near(ground(120,0,0),46.875f*.97f));
    aw_state.values[AW_ITEM][0].value=11;                                  /* 330 > 300: cannot move */
    assert(ground(120,0,0)==0);
    aw_state.count[AW_ITEM]=0;assert(near(ground(120,0,0),46.875f));
    knocked=1;assert(ground(120,0,0)==0);knocked=0;

    /* Fatigue: one second of running costs 5, walking nothing; a jump 5; never below 0. */
    player.v.flags=FL_ONGROUND;aw_move_after(0);
    ground(120,0,1);aw_move_after(1);assert(near(fatigue,195));
    ground(120,0,0);aw_move_after(1);assert(near(fatigue,195));
    ground(0,0,0);player.v.flags=0;player.v.velocity[2]=200;player.v.button2=1;
    aw_move_after(0);assert(near(fatigue,190));
    aw_move_after(0);assert(near(fatigue,190));               /* still in the air: one jump, one cost */
    player.v.flags=FL_ONGROUND;player.v.velocity[2]=0;player.v.button2=0;aw_move_after(0);
    fatigue=3;ground(120,0,1);aw_move_after(1);assert(fatigue==0);
    fatigue=200;player.v.flags=FL_ONGROUND|FL_GODMODE;ground(120,0,1);aw_move_after(1);assert(fatigue==200);
    player.v.flags=FL_ONGROUND;

    /* Superspeed: exactly the old numbers and no fatigue cost; the words; off restores the rules. */
    run("superspeed","on");assert(AW_MoveSuperspeed());
    assert(near(ground(120,0,0),120) && near(ground(120,0,1),216) && near(ground(120,120,0),169.706f));
    assert(near(swim(120,0),84));
    aw_character.skills[8]=100;assert(near(ground(120,0,1),216));   /* stats do not change it */
    aw_character.skills[8]=35;
    ground(120,0,1);aw_move_after(1);assert(fatigue==200);
    run("superspeed","off");assert(!AW_MoveSuperspeed() && near(ground(120,0,0),46.875f));
    run("superspeed","TRUE");assert(AW_MoveSuperspeed());
    run("superspeed","0");assert(!AW_MoveSuperspeed());
    run("superspeed","1");assert(AW_MoveSuperspeed());
    run("superspeed","false");assert(!AW_MoveSuperspeed());
    run("superspeed","maybe");assert(!AW_MoveSuperspeed());          /* refused, unchanged */
    run("superspeed",NULL);assert(!AW_MoveSuperspeed());             /* status only */
    return 0;
}
