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
#include "aw_levelup.h"
#include "aw_combat.h"
#include "aw_inventory.h"
#include "aw_effects.h"

#define SKILL_ATHLETICS 8       /* original skill order (aw_character.c skills[]) */
#define SKILL_ACROBATICS 20
#define RACES 16

static cvar_t superspeed={"aw_superspeed","0"};
static aw_move_settings_t settings;
static int settings_state;      /* 0 not read, 1 from the image, 2 the original's values (image has none) */
static struct {char id[64];float male,female;} races[RACES];
static int race_count;
static float last_factor;       /* the last move's input 0..1 (fatigue cost scale) */
static int last_swimming,last_running,last_sneaking,prev_ground,prev_jump;
static float effect_burden,effect_feather;   /* AW_EncumbranceSetEffects */
static double over_shown;                     /* when the over-encumbered line was last raised */

extern void (*aw_move_ground)(float *forwardmove,float *sidemove);
extern int (*aw_move_water)(float forwardmove,float sidemove,float upmove,float *wishspeed);
extern void (*aw_move_after)(float seconds);

int AW_MoveSuperspeed(void) {return superspeed.value!=0;}
/* SNEAK-58: the sneak key held (+aw_sneak, Left Ctrl) by a player on foot in the game: not swimming (the original
 * and OpenMW 0.51 stand up in water), not in noclip (there the key is fast flight), not knocked down or dead. */
/* MWSCRIPT-GAP-FUNCTIONS-62: a script's ForceSneak on the player (OpenMW creaturestats.cpp getStance: the forced flag
 * or the key); ClearForceSneak clears it (aw_mwhost.c) */
int aw_move_force_sneak;
int AW_MoveSneaking(void) {
    edict_t *p=sv.active && svs.clients?svs.clients[0].edict:NULL;
    /* menus clear the held key (cl_input.c IN_AWClearButtons) */
    return p && ((in_sneak.state&1) || aw_move_force_sneak) && p->v.movetype==MOVETYPE_WALK && p->v.waterlevel<2 &&
           p->v.health>0 && !AW_CombatPlayerKnocked();
}

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
/* The carried weight: the item table's running total (aw_state.h, ENCUMBRANCE-INCOMPLETE-61): the records' weights
 * x counts, changed when items come and go, never summed here. */
static float carried(void) {return AW_ItemsBurden(&aw_state);}
void AW_EncumbranceSetEffects(float burden,float feather) {
    effect_burden=burden>0?burden:0;effect_feather=feather>0?feather:0;
}
/* DBG-NOBURDEN-62 (aw_move.h): the debug mode, not saved; New Game turns it off (aw_loadfail.c registers the reset) */
static int noburden;
int AW_MoveNoBurdenOn(void) {return noburden;}
void AW_MoveNoBurdenSet(int on) {noburden=on!=0;}
float AW_PlayerEncumbrance(float *capacity) {
    aw_move_inputs_t in;float weight;
    AW_MovePlayerInputs(&in);
    if(capacity)*capacity=AW_MoveCapacity(&settings,&in);
    weight=in.carried-in.feather+(in.godmode?0:in.burden);
    /* no burden: the bar shows the real load over the largest capacity it shows (the rules see no load) */
    if(noburden){if(capacity)*capacity=AW_MOVE_NOBURDEN_SHOWN;weight=carried()-effect_feather+(in.godmode?0:effect_burden);}
    return weight>0?weight:0;
}
/* The player tried to move or jump while over the limit (OpenMW mwgui/windowmanagerimp.cpp: getEncumbrance >
 * getCapacity): the game's own line, sNotifyMessage59, kept up while he keeps trying (raised again every 2 s). */
static void over_encumbered(const aw_move_inputs_t *in,int trying) {
    static char line[96];float capacity=AW_MoveCapacity(&settings,in);
    float weight=in->carried-in->feather+(in->godmode?0:in->burden);
    if(!trying || !(weight>capacity) || in->dead || realtime-over_shown<2)return;
    if(!line[0] && !AW_LevelupGameText("sNotifyMessage59",line,sizeof(line)))strcpy(line,"You are over-encumbered.");
    AW_UISubtitle("",line,3);over_shown=realtime;
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
    in->sneaking=AW_MoveSneaking();
    in->knocked=AW_CombatPlayerKnocked();
    in->dead=p && p->v.health<=0;
    in->godmode=p && ((int)p->v.flags&FL_GODMODE);
    in->fatigue=AW_CombatPlayerFatigue(&in->fatigue_max);
    in->burden=effect_burden;in->feather=effect_feather;   /* AW_EncumbranceSetEffects */
    if(noburden)AW_MoveNoBurden(in);                        /* DBG-NOBURDEN-62: no load in any rule */
    /* DBG-SUPERSPEED-62: superspeed reads Speed, Athletics and Acrobatics at the game's maximum, 100 (the character
     * sheet itself untouched, so off gives the real values back at once) */
    if(AW_MoveSuperspeed())in->speed=in->athletics=in->acrobatics=AW_MOVE_SUPERSPEED_STAT;
    /* paralysis, Levitate, Swift Swim, Jump, Slowfall,
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
    over_encumbered(&in,len>0 || (sv_player && sv_player->v.button2));
    if(len<=0){*forwardmove=*sidemove=0;return;}
    last_factor=len>1?1:len;last_swimming=0;last_running=in.running;last_sneaking=in.sneaking;
    speed=AW_MoveCurrentSpeed(&settings,&in,last_factor,AW_MoveStrafing(y,x))*AW_MOVE_UNIT_SCALE;
    *forwardmove=y/len*speed;*sidemove=x/len*speed;
}
static int water(float forwardmove,float sidemove,float upmove,float *wishspeed) {
    aw_move_inputs_t in;float x,y,z,len,run;
    last_factor=0;
    if(AW_MoveSuperspeed())return 0;
    AW_MovePlayerInputs(&in);in.swimming=1;in.sneaking=0;
    run=in.running?cl_movespeedkey.value:1;
    y=axis(forwardmove,(forwardmove>=0?cl_forwardspeed.value:cl_backspeed.value)*run);
    x=axis(sidemove,cl_sidespeed.value*run);
    z=axis(upmove,cl_upspeed.value*run);
    len=sqrt(x*x+y*y+z*z);
    over_encumbered(&in,len>0);
    last_factor=len>1?1:len;last_swimming=1;last_running=in.running;last_sneaking=0;
    *wishspeed=AW_MoveCurrentSpeed(&settings,&in,last_factor,AW_MoveStrafing(y,x))*AW_MOVE_UNIT_SCALE;
    return 1;
}
/* Falls (aw_move.h, SCRIPTED-EVENT-FALLING-MAGE-61): the health a landing from HEIGHT original units costs, with the
 * image's game settings. */
float AW_MoveFallLoss(float height,float acrobatics,float jump,float fatigue,float fatigue_max,int *knockdown) {
    aw_move_inputs_t in;float damage,term;
    load_settings();
    memset(&in,0,sizeof(in));in.fatigue=fatigue;in.fatigue_max=fatigue_max;
    term=AW_MoveFatigueTerm(&settings,&in);
    damage=AW_MoveFallDamage(&settings,height,acrobatics,jump);
    if(knockdown)*knockdown=AW_MoveFallKnockdown(damage,acrobatics,term);
    return AW_MoveFallHealthLoss(damage,term);
}
/* The player's fall (OpenMW 0.51 mtphysics.cpp and character.cpp, aw_move.h): the drop while in the air adds to the
 * fall height, which starts again on the ground, in water, while levitating and while any Slowfall is on; the landing
 * costs the health of AW_MoveFallLoss (not in god mode, not in water). Slowfall slows the fall as OpenMW's physics
 * step does (the factor once each 1/60 s of falling; the engine's own gravity stays Quake's, PHYSICS-GRAVITY-SCALE-36).
 * Knockdown on a hard landing: not yet for the player (no knockdown entry outside a fight). */
static float fall_height,fall_z;static int fall_air;
static unsigned long falls_hurt;static float fall_last;
static void player_fall(edict_t *p,float seconds,int ground_now) {
    float slow,z=p->v.origin[2];
    int water=p->v.waterlevel>=1,levitate;
    static void *fall_map;
    /* a new map, a teleport or a door: no fall from where the player was (sv_maxvelocity 2000 units/s at most) */
    if(fall_map!=(void *)sv.worldmodel || fabs(z-fall_z)>64+2000*seconds){fall_map=(void *)sv.worldmodel;
        fall_height=0;fall_air=0;fall_z=z;return;}
    if(p->v.movetype!=MOVETYPE_WALK || p->v.health<=0){fall_height=0;fall_air=0;fall_z=z;return;}
    /* the effects are looked up only while any is active (a frame without: no look at the effect list) */
    slow=AW_EffectsCount()?AW_MoveSlowFallFactor(AW_EffectsMagnitude(AW_ACTOR_PLAYER_REF,AW_EFFECT_SLOWFALL,AW_EFFECT_NO_ARG)):1;
    levitate=AW_EffectsCount() && AW_EffectsMagnitude(AW_ACTOR_PLAYER_REF,AW_EFFECT_LEVITATE,AW_EFFECT_NO_ARG)>0;
    if(!ground_now){
        if(slow<1 && p->v.velocity[2]<0){
            int steps=(int)(seconds*60+.5f);
            if(steps<1)steps=1;
            if(steps>15)steps=15;
            while(steps-->0)p->v.velocity[2]*=slow;
        }
        if(slow<1 || p->v.waterlevel>=2 || levitate)fall_height=0;
        else if(z<fall_z)fall_height+=(fall_z-z)/AW_MOVE_UNIT_SCALE;
        fall_air=1;
    }else{
        if(fall_air && slow>=1 && !water && z<fall_z)fall_height+=(fall_z-z)/AW_MOVE_UNIT_SCALE;
        if(fall_air && fall_height>0 && !water && !((int)p->v.flags&FL_GODMODE)){
            aw_move_inputs_t in;float loss;int knockdown=0;
            AW_MovePlayerInputs(&in);
            loss=AW_MoveFallLoss(fall_height,in.acrobatics,
                                 AW_EffectsMagnitude(AW_ACTOR_PLAYER_REF,AW_EFFECT_JUMP,AW_EFFECT_NO_ARG),
                                 in.fatigue,in.fatigue_max,&knockdown);
            if(loss>0){falls_hurt++;fall_last=loss;AW_CombatHurtPlayer(loss,"a fall");
                /* LEVEL-UP-INGAME-62: a hurting landing that does not knock the player down is an Acrobatics_Fall
                 * use (OpenMW 0.51 character.cpp, after the fall damage) */
                if(!knockdown)AW_LevelupUse(AW_LU_ACROBATICS,AW_USE_FALL,1);}
        }
        fall_height=0;fall_air=0;
    }
    fall_z=z;
}
/* After the move: running, swimming and sneaking cost fatigue per second of
 * input (character.cpp), a jump costs its own (physicssystem.cpp). The jump is
 * seen as leaving the ground upwards with the jump button held. */
static void after(float seconds) {
    edict_t *p=sv_player;aw_move_inputs_t in;float loss;int ground_now,jumped;
    if(!p)return;
    /* DBG-SUPERSPEED-62: endless stamina while superspeed is on: whatever spent fatigue (a run, a jump, a swing, a block,
     * a blow taken) is filled again every move */
    if(AW_MoveSuperspeed())AW_CombatPlayerFatigueFill();
    ground_now=((int)p->v.flags&FL_ONGROUND)!=0;
    player_fall(p,seconds,ground_now);
    /* SKILL-RAISE-NOT-SEEN-62: the jump itself happens after this think (the game code's pre-think), so the frame that
     * first sees the player off the ground carries the NEXT command: a tapped jump key is already up there. The button
     * of the frame before counts too, else only a held key was ever a jump (no Acrobatics use, no jump fatigue). */
    jumped=prev_ground && !ground_now && p->v.velocity[2]>0 && (p->v.button2 || prev_jump);
    prev_ground=ground_now;prev_jump=p->v.button2!=0;
    if(AW_MoveSuperspeed() || (last_factor<=0 && !jumped)){last_factor=0;return;}
    AW_MovePlayerInputs(&in);in.swimming=last_swimming;in.running=last_running;in.sneaking=last_sneaking;
    loss=AW_MoveMaxSpeed(&settings,&in)>0?AW_MoveFatigueRate(&settings,&in)*last_factor*seconds:0;
    if(jumped)loss+=AW_MoveJumpFatigue(&settings,&in);
    /* LEVEL-UP-58: Acrobatics_Jump at the jump, Athletics per second of running on the ground (not sneaking) or of
     * swimming (OpenMW character.cpp) */
    if(jumped)AW_LevelupUse(AW_LU_ACROBATICS,AW_USE_JUMP,1);
    if(last_factor>0)AW_LevelupMoveSeconds(in.running && ground_now && !in.sneaking,in.swimming,seconds);
    last_factor=0;
    if(loss>0)AW_CombatPlayerFatigueLoss(loss);
}
/* view.c: the lowered eye while sneaking (SNEAK-58) */
extern float (*aw_view_sneak)(void);
static float view_sneak(void) {return AW_MoveSneaking()?1.0f:0.0f;}
static int toggle_word(char *text) {
    if(!Q_strcasecmp(text,"on") || !Q_strcasecmp(text,"true") || !strcmp(text,"1"))return 1;
    if(!Q_strcasecmp(text,"off") || !Q_strcasecmp(text,"false") || !strcmp(text,"0"))return 0;
    return -1;
}
/* superspeed / dbg superspeed [on/off, true/false or 1/0]; no argument turns it the other way (DBG-SUPERSPEED-62: a
 * bare dbg superspeed only printed the state before), then the state and the speeds. */
static void superspeed_command(void) {
    aw_move_inputs_t in;int on=-1;
    if(Cmd_Argc()>2 || (Cmd_Argc()==2 && (on=toggle_word(Cmd_Argv(1)))<0)){
        Con_Printf("Usage: superspeed [on/off, true/false or 1/0]; no argument turns it the other way (not saved).\n");return;}
    Cvar_SetValue(superspeed.name,Cmd_Argc()==2?on:!AW_MoveSuperspeed());
    if(AW_MoveSuperspeed()){
        Con_Printf("superspeed ON: the old fixed fast speeds, walk %ld, run %ld units/s; endless stamina; Speed, Athletics and Acrobatics read as 100\n",
                   (long)cl_forwardspeed.value,(long)(cl_forwardspeed.value*cl_movespeedkey.value));return;}
    AW_MovePlayerInputs(&in);
    {float scale=(in.scale>0?in.scale:1)*AW_MOVE_UNIT_SCALE;
     Con_Printf("superspeed OFF: the original's speeds, walk %ld, run %ld, swim %ld units/s\n",
                (long)(AW_MoveWalkSpeed(&settings,&in)*scale+.5f),(long)(AW_MoveRunSpeed(&settings,&in)*scale+.5f),
                (long)(AW_MoveSwimSpeed(&settings,&in)*scale+.5f));
     Con_Printf(" (Speed %ld, Athletics %ld, load %ld of %ld)\n",(long)in.speed,(long)in.athletics,
                (long)(in.carried+.5f),(long)(AW_MoveCapacity(&settings,&in)+.5f));}
}
extern float (*aw_worldui_encumbrance)(float *capacity);   /* aw_worldui.c: the inventory window's burden bar */
void AW_MoveInit(void) {
    aw_worldui_encumbrance=AW_PlayerEncumbrance;
    Cvar_RegisterVariable(&superspeed);
    Cmd_AddCommand("superspeed",superspeed_command);
    aw_move_ground=ground;aw_move_water=water;aw_move_after=after;aw_view_sneak=view_sneak;
}
