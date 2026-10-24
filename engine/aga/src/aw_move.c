/* SPDX-License-Identifier: GPL-2.0-or-later
 * The player's movement by the original's rules: the engine side of aw_move.h
 * (docs/PLAYER_MOVEMENT.md "Movement speed").
 *
 * Every frame the player's inputs are read from the LIVE character sheet
 * (Speed, Strength, Athletics, Acrobatics as they are now: levelling, skill
 * gains, scripted changes and later Fortify/Drain effects take effect at once),
 * the carried weight and the race's weight; nothing is baked at build time or
 * at character creation. The game settings come from the image's
 * combat/settings.txt "move" lines (tools/prepare_combat.py, from the user's
 * own master file).
 *
 * Superspeed (aw_superspeed, dbg superspeed / superspeed on|off; default off,
 * not saved; the maintainer's debugging request, 23 October 2026) leaves the
 * Quake movement exactly as it was before: cl_forwardspeed, cl_movespeedkey and
 * sv_maxspeed alone, and no movement fatigue cost.
 */
#include "quakedef.h"
#include "aw_move.h"
#include "aw_character.h"
#include "aw_combat.h"
#include "aw_inventory.h"

#define SKILL_ATHLETICS 8       /* original skill order (aw_character.c skills[]) */
#define SKILL_ACROBATICS 20
#define RACES 16

static cvar_t superspeed={"aw_superspeed","0"};
static aw_move_settings_t settings;
static int settings_state;      /* 0 not read, 1 from the image, 2 the original's values (image has none) */
static struct {char id[64];float male,female;} races[RACES];
static int race_count;
static float last_factor;       /* the last move's input 0..1 (fatigue cost scale) */
static int last_swimming,last_running,prev_ground;
static unsigned long carried_key;
static float carried_weight;

extern void (*aw_move_ground)(float *forwardmove,float *sidemove);
extern int (*aw_move_water)(float forwardmove,float sidemove,float upmove,float *wishspeed);
extern void (*aw_move_after)(float seconds);

int AW_MoveSuperspeed(void) {return superspeed.value!=0;}

/* combat/settings.txt: "move NAME VALUE" and "moverace MALE FEMALE RACE ID" lines.
 * Honours COM_FOpenFile's member size (the file may sit inside a pak). */
static void load_settings(void) {
    FILE *f=NULL;char line[128],name[64];int left,n=0,c,count=0;float a,b;
    if(settings_state)return;
    AW_MoveSettingsDefault(&settings);race_count=0;
    left=COM_FOpenFile("combat/settings.txt",&f);
    if(f){
        while(left>0){
            c=fgetc(f);left--;
            if(c==EOF)break;
            if(c!='\n' && c!='\r'){if(n<(int)sizeof(line)-1)line[n++]=(char)c;if(left>0)continue;}
            line[n]=0;n=0;
            if(!strncmp(line,"move ",5)){if(Q_sscanf(line+5,"%63s %f",name,&a)==2 && AW_MoveSettingSet(&settings,name,a))count++;}
            else if(!strncmp(line,"moverace ",9) && race_count<RACES &&
                    Q_sscanf(line+9,"%f %f",&a,&b)==2 && a>0 && b>0 && a<10 && b<10){
                char *id=line+8;int field;
                for(field=0;field<2 && *id;field++){while(*id==' ')id++;while(*id && *id!=' ')id++;}
                while(*id==' ')id++;
                if(*id && strlen(id)<sizeof(races[0].id)){
                    strcpy(races[race_count].id,id);races[race_count].male=a;races[race_count].female=b;race_count++;
                }
            }
        }
        fclose(f);
    }
    settings_state=count==AW_MOVE_SETTING_COUNT?1:2;
    if(settings_state==2)Con_Printf("Movement settings: %ld of %ld in this image; the original's values are used.\n",
                                    (long)count,(long)AW_MOVE_SETTING_COUNT);
}
/* The carried weight: the owned items' catalogue weights x counts, read again
 * only when the owned items change (a key over ids and counts). */
static float carried(void) {
    unsigned long key=5381;int i,n=aw_state.count[AW_ITEM];const char *s;float total=0;
    aw_inventory_item_t item;
    for(i=0;i<n;i++){
        for(s=aw_state.values[AW_ITEM][i].id;*s;s++)key=key*33+(unsigned char)*s;
        key=key*33+(unsigned long)aw_state.values[AW_ITEM][i].value;
    }
    key=key*33+(unsigned long)n;
    if(key==carried_key)return carried_weight;
    for(i=0;i<n;i++)
        if(aw_state.values[AW_ITEM][i].value>0 && AW_InventoryRead(aw_state.values[AW_ITEM][i].id,&item))
            total+=item.weight*aw_state.values[AW_ITEM][i].value;
    carried_key=key;carried_weight=total;
    return total;
}
static float attribute(int i) {
    return (float)(aw_character.attributes[i]+aw_character.modifiers[i]-aw_character.damage[i]);
}
void AW_MovePlayerInputs(aw_move_inputs_t *in) {
    edict_t *p=sv.active && svs.clients?svs.clients[0].edict:NULL;int i;
    load_settings();
    memset(in,0,sizeof(*in));
    if(aw_character.valid){
        in->speed=attribute(AW_SPD);in->strength=attribute(AW_STR);
        in->athletics=aw_character.skills[SKILL_ATHLETICS];in->acrobatics=aw_character.skills[SKILL_ACROBATICS];
    }else{
        /* No character yet (test maps): the combat sheet's defaults (AW_CombatPlayerSheet). */
        in->speed=in->strength=50;in->athletics=in->acrobatics=30;
    }
    in->carried=carried();
    in->scale=1;
    if(aw_character.valid && aw_character.race>=0 && aw_character.race<aw_race_count)
        for(i=0;i<race_count;i++)if(!Q_strcasecmp(races[i].id,aw_races[aw_character.race].id)){
            in->scale=aw_character.female?races[i].female:races[i].male;break;}
    in->running=(in_speed.state&1)!=0;
    in->knocked=AW_CombatPlayerKnocked();
    in->dead=p && p->v.health<=0;
    in->godmode=p && ((int)p->v.flags&FL_GODMODE);
    in->fatigue=AW_CombatPlayerFatigue(&in->fatigue_max);
    /* sneaking, paralysis, Feather/Burden, Levitate, Swift Swim, Jump, Slowfall,
     * Water Walking: no input or magic effect in the engine yet (0 = no effect). */
}
/* The command's input as a fraction of full input on each axis (Shift scales
 * the command by cl_movespeedkey, so it is divided out). */
static float axis(float move,float full) {return full>0?move/full:0;}
static void ground(float *forwardmove,float *sidemove) {
    aw_move_inputs_t in;float x,y,len,speed,run;
    last_factor=0;
    if(AW_MoveSuperspeed())return;
    AW_MovePlayerInputs(&in);
    run=in.running?cl_movespeedkey.value:1;
    y=axis(*forwardmove,(*forwardmove>=0?cl_forwardspeed.value:cl_backspeed.value)*run);
    x=axis(*sidemove,cl_sidespeed.value*run);
    len=sqrt(x*x+y*y);
    if(len<=0){*forwardmove=*sidemove=0;return;}
    last_factor=len>1?1:len;last_swimming=0;last_running=in.running;
    speed=AW_MoveCurrentSpeed(&settings,&in,last_factor,AW_MoveStrafing(y,x))*AW_MOVE_UNIT_SCALE;
    *forwardmove=y/len*speed;*sidemove=x/len*speed;
}
static int water(float forwardmove,float sidemove,float upmove,float *wishspeed) {
    aw_move_inputs_t in;float x,y,z,len,run;
    last_factor=0;
    if(AW_MoveSuperspeed())return 0;
    AW_MovePlayerInputs(&in);in.swimming=1;
    run=in.running?cl_movespeedkey.value:1;
    y=axis(forwardmove,(forwardmove>=0?cl_forwardspeed.value:cl_backspeed.value)*run);
    x=axis(sidemove,cl_sidespeed.value*run);
    z=axis(upmove,cl_upspeed.value*run);
    len=sqrt(x*x+y*y+z*z);
    last_factor=len>1?1:len;last_swimming=1;last_running=in.running;
    *wishspeed=AW_MoveCurrentSpeed(&settings,&in,last_factor,AW_MoveStrafing(y,x))*AW_MOVE_UNIT_SCALE;
    return 1;
}
/* After the move: running, swimming and sneaking cost fatigue per second of
 * input (character.cpp), a jump costs its own (physicssystem.cpp). The jump is
 * seen as leaving the ground upwards with the jump button held. */
static void after(float seconds) {
    edict_t *p=sv_player;aw_move_inputs_t in;float loss;int ground_now,jumped;
    if(!p)return;
    ground_now=((int)p->v.flags&FL_ONGROUND)!=0;
    jumped=prev_ground && !ground_now && p->v.velocity[2]>0 && p->v.button2;
    prev_ground=ground_now;
    if(AW_MoveSuperspeed() || (last_factor<=0 && !jumped)){last_factor=0;return;}
    AW_MovePlayerInputs(&in);in.swimming=last_swimming;in.running=last_running;
    loss=AW_MoveMaxSpeed(&settings,&in)>0?AW_MoveFatigueRate(&settings,&in)*last_factor*seconds:0;
    if(jumped)loss+=AW_MoveJumpFatigue(&settings,&in);
    last_factor=0;
    if(loss>0)AW_CombatPlayerFatigueLoss(loss);
}
static int toggle_word(char *text) {
    if(!Q_strcasecmp(text,"on") || !Q_strcasecmp(text,"true") || !strcmp(text,"1"))return 1;
    if(!Q_strcasecmp(text,"off") || !Q_strcasecmp(text,"false") || !strcmp(text,"0"))return 0;
    return -1;
}
/* superspeed / dbg superspeed [on/off, true/false or 1/0]; no argument = status. */
static void superspeed_command(void) {
    aw_move_inputs_t in;int on=-1;
    if(Cmd_Argc()>2 || (Cmd_Argc()==2 && (on=toggle_word(Cmd_Argv(1)))<0)){
        Con_Printf("Usage: superspeed [on/off, true/false or 1/0]; no argument = status (not saved).\n");return;}
    if(Cmd_Argc()==2)Cvar_SetValue(superspeed.name,on);
    if(AW_MoveSuperspeed()){
        Con_Printf("superspeed ON: the old fixed fast speeds, walk %ld, run %ld units/s; no running fatigue\n",
                   (long)cl_forwardspeed.value,(long)(cl_forwardspeed.value*cl_movespeedkey.value));return;}
    AW_MovePlayerInputs(&in);
    {float scale=(in.scale>0?in.scale:1)*AW_MOVE_UNIT_SCALE;
     Con_Printf("superspeed OFF: the original's speeds, walk %ld, run %ld, swim %ld units/s\n",
                (long)(AW_MoveWalkSpeed(&settings,&in)*scale+.5f),(long)(AW_MoveRunSpeed(&settings,&in)*scale+.5f),
                (long)(AW_MoveSwimSpeed(&settings,&in)*scale+.5f));
     Con_Printf(" (Speed %ld, Athletics %ld, load %ld of %ld)\n",(long)in.speed,(long)in.athletics,
                (long)(in.carried+.5f),(long)(AW_MoveCapacity(&settings,&in)+.5f));}
}
void AW_MoveInit(void) {
    Cvar_RegisterVariable(&superspeed);
    Cmd_AddCommand("superspeed",superspeed_command);
    aw_move_ground=ground;aw_move_water=water;aw_move_after=after;
}
