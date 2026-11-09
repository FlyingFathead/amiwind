/* SPDX-License-Identifier: GPL-2.0-or-later
 * Breath and drowning under water: the engine side of aw_breath.h (UNDERWATER-BREATH-62). Once a frame, after the
 * lava damage (sv_phys.c): the player's breath left, the drowning damage through the one world-damage check (god mode
 * takes none), the "drown" sound and the breath bar's state. Fixed state only (about 130 bytes), no allocation; the
 * settings are read once from combat/settings.txt. */
#include "quakedef.h"
#include "aw_breath.h"
#include "aw_combat.h"
#include "aw_effects.h"
#include "aw_cast.h"
#include "aw_reset.h"

static aw_breath_settings_t settings;
static int settings_state;               /* 0 not read, 1 from the image, 2 the original's values */
static char sound_path[64];static float sound_seconds;
static float left=-1;                    /* the breath left, seconds; -1 full (not under water since the reset) */
static int submerged,breathing;          /* this frame */
static void *breath_map;                 /* a new map (a load, a door): a full breath */
static double sound_next;
static unsigned long drown_ticks;static float drown_damage;

static void load_settings(void) {
    FILE *f=NULL;char line[128],name[64],path[64];float value,seconds;int count=0,c,n=0,bytes;
    if(settings_state)return;
    AW_BreathSettingsDefault(&settings);sound_path[0]=0;sound_seconds=0;
    bytes=COM_FOpenFile("combat/settings.txt",&f);
    if(f){
        while(bytes>0){
            c=fgetc(f);bytes--;
            if(c==EOF)break;
            if(c!='\n' && c!='\r'){if(n<(int)sizeof(line)-1)line[n++]=(char)c;if(bytes>0)continue;}
            line[n]=0;n=0;
            if(strncmp(line,"breath ",7))continue;
            if(Q_sscanf(line+7,"sound %63s %f",path,&seconds)==2){
                if(!strstr(path,"..")){strcpy(sound_path,path);sound_seconds=seconds>0 && seconds<30?seconds:1;}
                continue;
            }
            if(Q_sscanf(line+7,"%63s %f",name,&value)==2 && AW_BreathSettingSet(&settings,name,value))count++;
        }
        fclose(f);
    }
    settings_state=count==AW_BREATH_SETTING_COUNT?1:2;
    if(settings_state==2)Con_DPrintf("Breath settings: %ld of %ld in this image; the original's values are used.\n",
                                     (long)count,(long)AW_BREATH_SETTING_COUNT);
}
/* Water Breathing on the player: the active effects and the always-active spells of his list (a race's ability),
 * by the combat layer's effect hook (aw_mwhost.c effect_magnitude_of); only asked while the head is under water */
static float water_breathing(edict_t *p) {
    if(aw_combat_effect_magnitude)return aw_combat_effect_magnitude(p,AW_EFFECT_WATER_BREATHING);
    return AW_EffectsMagnitude(AW_ACTOR_PLAYER_REF,AW_EFFECT_WATER_BREATHING,AW_EFFECT_NO_ARG);
}
void AW_BreathPhysics(void) {
    edict_t *p;float dt=(float)host_frametime,loss;
    submerged=breathing=0;
    if(!sv.active || svs.maxclients!=1 || !svs.clients || !(p=svs.clients[0].edict)){left=-1;return;}
    if(breath_map!=(void *)sv.worldmodel){breath_map=(void *)sv.worldmodel;left=-1;}
    if(p->v.health<=0 || p->v.movetype==MOVETYPE_NOCLIP){left=-1;return;}
    load_settings();
    submerged=AW_BreathSubmerged((int)p->v.watertype,(int)p->v.waterlevel);
    breathing=submerged && water_breathing(p)>0;
    left=AW_BreathStep(left,settings.hold,submerged,breathing,dt);
    loss=AW_BreathDamage(left,settings.suffocation,dt);
    if(!(loss>0))return;
    drown_ticks++;drown_damage+=loss;
    AW_CombatHurtPlayer(loss,"drowning");
    /* the "drown" sound, again whenever it has ended (OpenMW plays it while it is not playing) */
    if(sound_path[0] && realtime>=sound_next && p->v.health>0){S_LocalSoundBeside(sound_path);sound_next=realtime+sound_seconds;}
}
static int bar(float *fraction,int *flashing) {
    if(!AW_BreathBarShown(left,settings.hold))return 0;
    *fraction=AW_BreathFraction(left,settings.hold);
    *flashing=left<=0 && ((int)(realtime*4)&1);
    return 1;
}
/* dbg breath: the state by number */
static void breath_command(void) {
    edict_t *p=sv.active && svs.clients?svs.clients[0].edict:NULL;float world_held=0;unsigned long held;
    load_settings();
    held=AW_CombatWorldGodHeld(&world_held);
    Con_Printf("Breath: %.1f of %.1f s left%s; head under water %s; Water Breathing %.0f\n",
               left<0?settings.hold:left,settings.hold,left<0?" (full)":"",submerged?"yes":"no",
               p?water_breathing(p):0.0f);
    Con_Printf(" drowning: %.0f health a second once it is gone; taken %.1f in %lu frames; sound %s\n",
               settings.suffocation,drown_damage,drown_ticks,sound_path[0]?sound_path:"none in this image");
    Con_Printf(" settings %s; god mode held back %lu world damages (%.1f health) and %lu script or spell losses\n",
               settings_state==1?"from the image":"the original's values",held,world_held,AW_MwscriptGodHealthHeld());
}
/* New Game: a full breath, nothing taken (aw_reset.h) */
static void reset_breath(int new_game) {(void)new_game;left=-1;submerged=breathing=0;drown_ticks=0;drown_damage=0;sound_next=0;}
static unsigned long digest_breath(void) {return AW_ResetHash(AW_RESET_SEED,&left,sizeof(left));}
void AW_BreathInit(void) {
    aw_breath_bar=bar;
    Cmd_AddCommand("aw_breath",breath_command);
    AW_ResetRegister("breath (drowning)",reset_breath,digest_breath);
}
