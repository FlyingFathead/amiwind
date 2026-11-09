# SPDX-License-Identifier: GPL-3.0-only
"""Every function and instruction of MWScript: what it returns, what it takes, which part of the game it touches.

Argument letters (the convention of the language as OpenMW's compiler documents it; our own table):
  c  an object/record id (a string or a bare name; compared without case)
  S  a string kept as written (file paths, cell names, text)
  l  a whole number      s  a short whole number      f  a number with a fraction
  x  an optional string the game ignores    X  an optional number the game ignores
  z  an optional string or number the game ignores
  j  a piece of junk (a "." or a keyword) the game skips
  /  everything after it is optional
Return: '-' an instruction (no value), 'l' a whole number, 'f' a number with a fraction.

Group: what the function needs from the engine. The scripts that need only 'core', 'audio' and 'journal' (and the
globals) are the ones the first interpreter runs whole. 'run' marks the functions the engine's interpreter
(engine/aga/src/aw_mwvm.c) carries out today; every other function compiles to the "not yet" opcode.
"""

# name ret args group
_TABLE = r'''
# --- audio ---
playsound - cXX audio
playsoundvp - cff audio
playsound3d - cXX audio
playsound3dvp - cff audio
playloopsound3d - cXX audio
playloopsound3dvp - cff audio
stopsound - cXX audio
getsoundplaying l c audio
say - SS audio
say3d - SS audio
saydone l - audio
streammusic - S audio
# --- journal ---
journal - cl journal
setjournalindex - cl journal
getjournalindex l c journal
# --- core: the interpreter alone ---
getsecondspassed f - core
random f l core
menumode l - core
cellchanged l - core
startscript - c core
stopscript - c core
scriptrunning l c core
getdistance f c core
getsquareroot f f core
# --- dialogue ---
filljournal - - dialogue
addtopic - S dialogue
choice - j/SlSlSlSlSlSlSlSlSlSlSlSlSlSlSlSlSlSlSlSlSlSlSlSl dialogue
forcegreeting - z dialogue
goodbye - - dialogue
setreputation - l dialogue
modreputation - l dialogue
getreputation l - dialogue
samefaction l - dialogue
modfactionreaction - ccl dialogue
setfactionreaction - ccl dialogue
getfactionreaction l ccX dialogue
clearinfoactor - - dialogue
moddisposition - l dialogue
setdisposition - l dialogue
getdisposition l - dialogue
# --- ai ---
aiactivate - c/l ai
aitravel - fff/lx ai
aiescort - cffff/l ai
aiescortcell - ccffff/l ai
aiwander - fff/llllllllll ai
aifollow - cffff/llllllll ai
aifollowcell - ccffff/l ai
getaipackagedone l - ai
getcurrentaipackage l - ai
getdetected l c ai
sethello - l ai
setfight - l ai
setflee - l ai
setalarm - l ai
modhello - l ai
modfight - l ai
modflee - l ai
modalarm - l ai
gethello l - ai
getfight l - ai
getflee l - ai
getalarm l - ai
getlineofsight l c ai
getlos l c ai
gettarget l c ai
face - ffX ai
toggleai - - console
tai - - console
# --- combat ---
startcombat - c combat
stopcombat - x combat
getattacked l - combat
getweapondrawn l - combat
getweapontype l - combat
ondeath l - combat
onmurder l - combat
onknockout l - combat
hitonme l S combat
hitattemptonme l S combat
getspellreadied l - spells
# --- animation ---
skipanim - - anim
playgroup - c/l anim
loopgroup - cl/l anim
# --- cell and the player's place ---
testcells - - console
testinteriorcells - - console
coc - S position
centeroncell - S position
coe - ll position
centeronexterior - ll position
setwaterlevel - f world
modwaterlevel - f world
getinterior l - cell
getpccell l c cell
getwaterlevel f - cell
# --- inventory ---
additem - clX inventory
getitemcount l cX inventory
removeitem - clX inventory
equip - cX inventory
getarmortype l l inventory
hasitemequipped l c inventory
hassoulgem l c inventory
addsoulgem - ccX inventory
removesoulgem - c/l inventory
drop - cl inventory
dropsoulgem - c inventory
# --- player control ---
togglecollision - - console
tcl - - console
clearforcerun - - control
forcerun - - control
clearforcejump - - control
forcejump - - control
clearforcemovejump - - control
forcemovejump - - control
clearforcesneak - - control
forcesneak - - control
getpcrunning l - control
getpcsneaking l - control
getforcerun l - control
getforcejump l - control
getforcemovejump l - control
getforcesneak l - control
# --- menus, messages and the map ---
enablebirthmenu - - ui
enableclassmenu - - ui
enablenamemenu - - ui
enableracemenu - - ui
enablestatreviewmenu - - ui
enableinventorymenu - - ui
enablemagicmenu - - ui
enablemapmenu - - ui
enablestatsmenu - - ui
enablerest - - ui
enablelevelupmenu - - ui
showrestmenu - - ui
getbuttonpressed l - ui
togglefogofwar - - console
tfow - - console
togglefullhelp - - console
tfh - - console
showmap - Sxxxx ui
fillmap - - ui
menutest - /l console
togglemenus - - console
tm - - console
messagebox - - ui
# --- the world's objects and their state ---
enable - x world
disable - x world
getdisabled l x world
xbox l - core
onactivate l - world
activate - x world
lock - /l world
unlock - - world
getlocked l - world
setdelete - l world
getstandingpc l - world
getstandingactor l - world
getcollidingpc l - world
getcollidingactor l - world
hurtstandingactor - f combat
hurtcollidingactor - f combat
fall - - position
dontsaveobject - - world
# --- spells and effects ---
cast - SS spells
explodespell - S spells
geteffect l S spells
addspell - cz spells
removespell - cz spells
removespelleffects - c spells
removeeffects - l spells
getspell l c spells
getspelleffects l c spells
# --- time, sky and weather ---
getcurrenttime f - time
getwindspeed f - sky
togglesky - - console
ts - - console
turnmoonwhite - - sky
turnmoonred - - sky
changeweather - Sl sky
getmasserphase l - sky
getsecundaphase l - sky
getcurrentweather l - sky
modregion - S/llllllllllX sky
# --- views, rest, jail and the rest of the player's state ---
fadein - f ui
fadeout - f ui
fadeto - ff ui
pcforce1stperson - - control
pcforce3rdperson - - control
pcget3rdperson l - control
togglevanitymode - - console
tvm - - console
getpcsleep l - stats
getpcjumping l - stats
wakeuppc - - stats
playbink - Sl ui
payfine - - stats
payfinethief - - stats
gotojail - - stats
getpcinjail l - stats
getpctraveling l - stats
disableteleporting - - control
enableteleporting - - control
disablelevitation - - control
enablelevitation - - control
# --- stats ---
getpccrimelevel f - stats
setpccrimelevel - f stats
modpccrimelevel - f stats
resurrect - - stats
pcraiserank - /S stats
pclowerrank - /S stats
pcjoinfaction - /S stats
getpcrank l /S stats
setlevel - l stats
getlevel l - stats
getstat l c stats
getdeadcount l c stats
getpcfacrep l /c stats
setpcfacrep - l/c stats
modpcfacrep - l/c stats
getcommondisease l - spells
getblightdisease l - spells
getrace l c stats
getwerewolfkills l - stats
pcexpelled l /S stats
pcexpell - /S stats
pcclearexpelled - /S stats
raiserank - x stats
lowerrank - x stats
iswerewolf l - stats
becomewerewolf - - stats
undowerewolf - - stats
setwerewolfacrobatics - - stats
getpcvisionbonus f - stats
setpcvisionbonus - f stats
modpcvisionbonus - f stats
# --- positions, angles and placing objects ---
setscale - f position
getscale f - position
setangle - cf position
getangle f c position
setpos - cf position
getpos f c position
getstartingpos f c position
getstartingangle f c position
position - ffffz position
positioncell - ffffczz position
placeitemcell - ccffffX position
placeitem - cffffX position
placeatpc - clflX position
placeatme - clflX position
modscale - f position
rotate - cf position
rotateworld - cf position
setatstart - - position
move - cf position
moveworld - cf position
resetactors - - position
fixme - - position
ra - - position
# --- levelled lists ---
addtolevcreature - ccl world
removefromlevcreature - ccl world
addtolevitem - ccl world
removefromlevitem - ccl world
# --- console and debugging (never in a shipped script's real work) ---
togglecollisionboxes - - console
togglecollisiongrid - - console
tcb - - console
tcg - - console
twf - - console
togglewireframe - - console
togglewater - - console
twa - - console
toggleworld - - console
tw - - console
togglepathgrid - - console
tpg - - console
showvars - - console
show - c console
sv - - console
tgm - - console
togglegodmode - - console
togglescripts - - console
betacomment - /S console
bc - /S console
ori - /S console
outputrefinfo - /S console
showscenegraph - /l console
ssg - /l console
tb - - console
toggleborders - - console
help - - console
user1 - - console
user2 - - console
user3 - - console
user4 - - console
'''

ATTRIBUTES = ('strength', 'intelligence', 'willpower', 'agility', 'speed', 'endurance', 'personality', 'luck')
DYNAMICS = ('health', 'magicka', 'fatigue')
SKILLS = ('block', 'armorer', 'mediumarmor', 'heavyarmor', 'bluntweapon', 'longblade', 'axe', 'spear', 'athletics',
          'enchant', 'destruction', 'alteration', 'illusion', 'conjuration', 'mysticism', 'restoration', 'alchemy',
          'unarmored', 'security', 'sneak', 'acrobatics', 'lightarmor', 'shortblade', 'marksman', 'mercantile',
          'speechcraft', 'handtohand')
EFFECTS = ('resistmagicka', 'resistfire', 'resistfrost', 'resistshock', 'resistdisease', 'resistblight',
           'resistcorprus', 'resistpoison', 'resistparalysis', 'resistnormalweapons', 'waterbreathing', 'chameleon',
           'waterwalking', 'swimspeed', 'superjump', 'flying', 'armorbonus', 'castpenalty', 'silence', 'blindness',
           'paralysis', 'invisible', 'attackbonus', 'defendbonus')
CONTROLS = ('playercontrols', 'playerfighting', 'playerjumping', 'playerlooking', 'playermagic', 'playerviewswitch',
            'vanitymode')

# What the interpreter carries out today (engine/aga/src/aw_mwvm.c); everything else is "not yet".
RUN = {'playsound', 'playsoundvp', 'playsound3d', 'playsound3dvp', 'playloopsound3d', 'playloopsound3dvp',
       'stopsound', 'getsoundplaying', 'say', 'say3d', 'saydone', 'streammusic',
       'journal', 'setjournalindex', 'getjournalindex',
       'getsecondspassed', 'random', 'menumode', 'cellchanged', 'startscript', 'stopscript', 'scriptrunning',
       'getdistance', 'getsquareroot',
       # object state (v0.0.51): an object hidden and not solid, a lock's level
       'enable', 'disable', 'getdisabled', 'lock', 'unlock', 'getlocked',
       # activation (v0.0.51): a script that reads OnActivate takes over its object's use; Activate does it
       'onactivate', 'activate',
       # messages (v0.0.51): a message box with its buttons, the button the player chose
       'messagebox', 'getbuttonpressed',
       # the actor record (v0.0.54, docs/ACTOR_STATE.md): items, spells, combat, the dead count; the stats below
       'additem', 'removeitem', 'getitemcount', 'addspell', 'removespell', 'getspell', 'startcombat', 'stopcombat',
       'getdeadcount',
       # the ambient tables' wander (v0.0.54, engine/aga/src/aw_ambient.h)
       'aiwander',
       # the world and cell lookups (v0.0.54): the player's cell against a build-time table of the cells a name
       # matches (GETPCCELL), an object's position (GETPOS), the diseases among an actor's spells (SPELL verbs 3, 4)
       'getpccell', 'getpos', 'getcommondisease', 'getblightdisease',
       # what OpenMW does nothing for (miscextensions.cpp OpDontSaveObject, OpFall: the falling mage's script calls it,
       # the fall itself is the physics after his platform is disabled) or answers with a constant (OpXBox: 0)
       'dontsaveobject', 'fall', 'xbox',
       # the ambient tables' AI package (v0.0.54, aw_ambient.h AW_AmbientAiPackage): the current one and its end
       'getcurrentaipackage', 'getaipackagedone'}


def _actor_calls():
    """{function: (verb, stat)} of the calls that read or change the actor record's stats (the ACTOR opcode)."""
    from .opcodes import ACTOR_STATS as S, VERBS as V
    calls = {}
    for i, a in enumerate(ATTRIBUTES):
        calls.update({'get' + a: (V['get'], S['attribute'] + i), 'set' + a: (V['set'], S['attribute'] + i),
                      'mod' + a: (V['mod'], S['attribute'] + i)})
    for i, s in enumerate(SKILLS):
        calls.update({'get' + s: (V['get'], S['skill'] + i), 'set' + s: (V['set'], S['skill'] + i),
                      'mod' + s: (V['mod'], S['skill'] + i)})
    for d in DYNAMICS:
        calls.update({'get' + d: (V['get'], S[d]), 'set' + d: (V['set'], S[d]), 'mod' + d: (V['mod'], S[d]),
                      'modcurrent' + d: (V['modcurrent'], S[d]), 'get' + d + 'getratio': (V['ratio'], S[d])})
    for r in ('hello', 'fight', 'flee', 'alarm'):
        calls.update({'get' + r: (V['get'], S[r]), 'set' + r: (V['set'], S[r]), 'mod' + r: (V['mod'], S[r])})
    calls.update({'getlevel': (V['get'], S['level']), 'setlevel': (V['set'], S['level']),
                  'getdisposition': (V['get'], S['disposition']), 'setdisposition': (V['set'], S['disposition']),
                  'moddisposition': (V['mod'], S['disposition']), 'ondeath': (V['get'], S['ondeath'])})
    return calls


ACTOR_CALLS = _actor_calls()
RUN |= set(ACTOR_CALLS)

# Carried out by the engine through the import route (v0.0.57): the call keeps its NOTYET form (function number,
# numbers, strings; no new opcode, no change of the file's format) and the host's call() answers it by number
# (engine/aga/src/aw_mwhost.c, aw_pcstanding.c). The player's standing: crime level, reputation, faction rank, the
# expelled mark and the faction reputation (rules from OpenMW apps/openmw/mwscript/statsextensions.cpp and
# dialogueextensions.cpp), and GetRace. EFFECTS: those that change something (the INERT rule).
HOST = {'getpccrimelevel', 'setpccrimelevel', 'modpccrimelevel',
        'getreputation', 'setreputation', 'modreputation',
        'getpcrank', 'pcraiserank', 'pclowerrank', 'pcjoinfaction',
        'pcexpelled', 'pcexpell', 'pcclearexpelled',
        'getpcfacrep', 'setpcfacrep', 'modpcfacrep', 'getrace',
        # v0.0.57: an animation group on a skeletal actor (aw_animkit.c AW_AnimPickScripted; OpenMW
        # animationextensions.cpp OpPlayAnim, OpLoopAnim)
        'playgroup', 'loopgroup',
        # v0.0.57: a topic the player knows (one bit per TOPC row, saved; OpenMW dialogueextensions.cpp OpAddTopic)
        'addtopic',
        # v0.0.57: Cast of the cures on the player (the compiler keeps every other Cast "not yet", codegen.CURES)
        'cast',
        # v0.0.57: GetEffect reads the active spell effects (aw_effects.c; OpenMW miscextensions.cpp OpGetEffect)
        'geteffect',
        # v0.0.57: ForceGreeting plays the actor's greeting as talking to it does (the dialogue window: DIALOGUE-57)
        'forcegreeting',
        # v0.0.57: Rotate on an object with an entity; GetTarget against the combat layer (it fights the player only)
        'rotate', 'gettarget',
        # v0.0.57: AITravel on the ambient tables' routes (aw_ambient.c AW_AmbientTravel; OpenMW aitravel.cpp)
        'aitravel',
        # v0.0.57: AIFollow on the same entry (aifollow.cpp); GetStandingPC on objects with an entity
        'aifollow', 'getstandingpc',
        # v0.0.57: Position of the player (the coordinate teleport) and of objects with an entity (transformationextensions.cpp)
        'position',
        # v0.0.58: Choice and Goodbye in a dialogue result script (the dialogue window: DIALOGUE-COMPLETE-58; OpenMW
        # dialogueextensions.cpp OpChoice, OpGoodbye)
        'choice', 'goodbye',
        # v0.0.58: a faction's reaction toward another (aw_dial.c AW_DialReactionChange; OpenMW dialogueextensions.cpp
        # OpModFactionReaction, OpSetFactionReaction): the disposition reads it, saved
        'modfactionreaction', 'setfactionreaction',
        # v0.0.58: ShowMap records the revealed place (aw_actorstate.c AW_RevealedAdd, saved) for the map's place
        # markers (INGAME-MAP-ORIGINAL-57: shown when the map has them)
        'showmap',
        # v0.0.58: ClearInfoActor in a result script: the speaker's last entry on the topic's journal page goes
        # (aw_dial.c AW_DialHeardRemoveLast; OpenMW DialogueManager::clearInfoActor)
        'clearinfoactor',
        # v0.0.59: RaiseRank / LowerRank of an NPC in its own faction, kept on the world change list by its
        # reference and saved (aw_mwhost.c; OpenMW statsextensions.cpp OpRaiseRank, OpLowerRank)
        'raiserank', 'lowerrank',
        # v0.0.59: ShowRestMenu on a bed (the rest window with the bed, its ownership checked) and GetPCSleep (the
        # window open in rest mode): aw_wait.c AW_RestOpen, AW_RestSleeping (REST-WAIT-59; OpenMW guiextensions.cpp
        # OpShowRestMenu, statsextensions.cpp OpGetPCSleep)
        'showrestmenu', 'getpcsleep',
        # v0.0.62: PositionCell of anything but the player (the player's own keeps its PMOV row): an actor moved to a
        # place in a named cell, kept on the world change list by its reference, spawned there when that room loads
        # (aw_mwhost.c AWF_POSITIONCELL, aw_actors.c; OpenMW transformationextensions.cpp OpPositionCell,
        # MWSCRIPT-POSITIONCELL-ACTORS-62)
        'positioncell',
        # v0.0.62: AIFollowCell (a follower that crosses doors with the player and is done in the named room) and
        # AIEscort / AIEscortCell (the actor leads the target to a point while it keeps up), on the ambient tables
        # (aw_ambient.c AW_AmbientPackage; OpenMW aiextensions.cpp OpAiFollowCell, OpAiEscort, OpAiEscortCell,
        # aifollow.cpp, aiescort.cpp, actionteleport.cpp getFollowers; MWSCRIPT-POSITIONCELL-ACTORS-62)
        'aifollowcell', 'aiescort', 'aiescortcell',
        # v0.0.62: the placing family (OpenMW transformationextensions.cpp OpPlaceAt, OpPlaceItem, OpPlaceItemCell): a
        # new NPC or creature of a record the world already has a converted model for, or a carried item, made at the
        # player, at a reference, at a position or in a named cell, kept on the world change list (aw_mwhost.c
        # AWF_PLACE*, codegen.Program.place_rows; MWSCRIPT-PLACE-OBJECTS-62); any other object stays "not yet"
        'placeatpc', 'placeatme', 'placeitem', 'placeitemcell',
        # v0.0.62: the small functions (MWSCRIPT-SMALL-FUNCTIONS-62; aw_mwhost.c): an object's angles read and set,
        # moved along its own or the world's axes, set on one axis, put back where it started, an actor turned to a
        # point (OpenMW transformationextensions.cpp OpGetAngle, OpSetAngle, OpMove, OpMoveWorld, OpSetPos,
        # OpSetAtStart; aiextensions.cpp OpFace); detection and the line of sight (aiextensions.cpp OpGetDetected,
        # OpGetLineOfSight; actors.cpp isActorDetected; mechanicsmanagerimp.cpp awarenessCheck, the crime rules'
        # check, aw_crime.c); the player's cell an interior (cellextensions.cpp OpGetInterior), the weather
        # (skyextensions.cpp OpGetCurrentWeather), a knockdown's first frame (statsextensions.cpp OpOnKnockout) and
        # the player woken from a rest (miscextensions.cpp OpWakeUpPC); turned about the world's axes
        # (OpRotateWorld), the player sneaking (controlextensions.cpp OpGetPcSneaking), a weapon out
        # (miscextensions.cpp OpGetWeaponDrawn) and SetDelete as the object state's Disable / Enable (OpSetDelete)
        'getangle', 'setangle', 'move', 'moveworld', 'setpos', 'setatstart', 'face', 'rotateworld',
        'getdetected', 'getlos', 'getlineofsight', 'getinterior', 'getcurrentweather', 'onknockout', 'wakeuppc',
        'getpcsneaking', 'getweapondrawn', 'setdelete',
        # v0.0.62: the crimes (CRIME-59; aw_crime.c): OnMurder (statsextensions.cpp OpOnMurder: 1 once after the
        # actor's murder was reported), PayFine (bounty 0, the stolen goods taken, the witnesses calmed), PayFineThief
        # (bounty 0, calmed, the goods kept), GotoJail (the sentence: days pass, skills change, released at the nearest
        # prison marker) and GetPCInJail (miscextensions.cpp OpPayFine, OpPayFineThief, OpGoToJail, OpGetPcInJail;
        # worldimp.cpp goToJail; jailscreen.cpp)
        'onmurder', 'payfine', 'payfinethief', 'gotojail', 'getpcinjail',
        # v0.0.62 (MWSCRIPT-GAP-FUNCTIONS-62): the screen faded to black and back (OpenMW miscextensions.cpp OpFadeIn,
        # OpFadeOut, OpFadeTo, mwgui/screenfader.cpp: from the fade of the moment, over the seconds given; FadeTo's
        # number is a percent), Quake's palette shift (view.c V_ScreenFade); the sneak stance forced and cleared
        # (controlextensions.cpp OpSetMovementFlag, OpClearMovementFlag, OpGetForceSneak; creaturestats.cpp getStance:
        # the forced flag makes the actor sneak): the player sneaks (aw_move.c), an NPC is taken as sneaking by the
        # detection (aw_mwhost.c); the resistances read, set and changed (statsextensions.cpp OpGetMagicEffect,
        # OpSetMagicEffect, OpModMagicEffect: the effect's magnitude less its weakness, the elemental shields counted;
        # Set and Mod move a base modifier the actor keeps, aw_effects.c AW_EffectsBaseModify)
        'fadein', 'fadeout', 'fadeto', 'forcesneak', 'clearforcesneak', 'getforcesneak',
        # v0.0.62: the player's filled soul gems by their soul (miscextensions.cpp OpHasSoulGem, OpRemoveSoulGem;
        # aw_mwhost.c soul_gems)
        'hassoulgem', 'removesoulgem',
        # v0.0.62: the player standing on the object hurt (miscextensions.cpp OpHurtStandingActor; the lava volume's
        # own damage holds back meanwhile, aw_lava.c)
        'hurtstandingactor',
        # v0.0.62: Drop of a carried item that can lie in the world (miscextensions.cpp OpDrop; codegen.drop)
        'drop',
        # v0.0.62: an actor reset to its game data (statsextensions.cpp OpResurrect; aw_mwhost.c resurrect)
        'resurrect',
        # v0.0.62 (MWSCRIPT-UNPLACED-ATTACH-62): a video played over the scene, which goes on after it
        # (miscextensions.cpp OpPlayBink; aw_movie.c AW_MovieScript)
        'playbink',
        # v0.0.62 (MWSCRIPT-INVENTORY-HITONME-62): the actor's last hit object, read and cleared (miscextensions.cpp
        # OpHitOnMe; the player's weapon kept per victim by aw_combat.c AW_CombatLastHit*, aw_mwhost.c hit_on_me)
        'hitonme',
        # v0.0.62 (MWSCRIPT-COMPLETE-LANDMARK): a region's weather set until the next weather change and its weather
        # chances changed for the rest of the game, saved (skyextensions.cpp OpChangeWeather, OpModRegion;
        # weather.cpp WeatherManager::changeWeather, modRegion; aw_weather.c AW_WeatherScript*): the region is worked
        # out here (codegen.hostcall, the region catalogue's index), a region not in the image is no code
        'changeweather', 'modregion',
        # v0.0.63 (MWSCRIPT-GAPS-63): Secunda drawn in the script colour and back (OpenMW skyextensions.cpp
        # OpTurnMoonRed, OpTurnMoonWhite; sky.cpp setMoonColour: Secunda only, the fallback Moons_Script_Color), kept
        # in the saved named facts (aw_story.c AW_MoonRed); an item the actor wears or holds (containerextensions.cpp
        # OpHasItemEquipped: any equipment slot holds the id); the run forced and cleared (controlextensions.cpp
        # OpSetMovementFlag, OpClearMovementFlag, OpGetForceRun): the player runs (aw_move.c), an NPC walks its
        # packages at its run speed (aw_ambient.c), kept in the AWFS save block
        'turnmoonred', 'turnmoonwhite', 'hasitemequipped', 'forcerun', 'clearforcerun', 'getforcerun',
        # v0.0.63 (MWSCRIPT-GAPS-63): the object casts a spell on itself, its effects' areas reaching the actors around
        # it (miscextensions.cpp OpExplodeSpell, spellcasting.cpp inflict, worldimp.cpp explodeSpell; aw_cast.c
        # AW_CastExplode); an actor the player attacked while its fight goes on (statsextensions.cpp OpGetAttacked);
        # an effect of the spell active on the actor (miscextensions.cpp OpGetSpellEffects)
        'explodespell', 'getattacked', 'getspelleffects',
        # v0.0.63 (MWSCRIPT-GAPS-63): the werewolf set (statsextensions.cpp OpSetWerewolf, OpIsWerewolf,
        # OpSetWerewolfAcrobatics, OpGetWerewolfKills; player.cpp setWerewolfStats / restoreStats): the player's form
        # with the werewolf's stats from the game settings and his own kept, his items taken off, the kills counted,
        # an NPC's flag; saved (AWWF); the beast's body is not drawn yet. GetPCTraveling reads 0 (a travel is one
        # step here; miscextensions.cpp OpGetPcTraveling)
        'becomewerewolf', 'undowerewolf', 'iswerewolf', 'setwerewolfacrobatics', 'getwerewolfkills',
        'getpctraveling',
        # v0.0.63: an object's drawn size (transformationextensions.cpp OpSetScale, OpModScale, OpGetScale; the edict's
        # aw_scale, not kept past the map)
        'setscale', 'modscale', 'getscale',
        # v0.0.63 (MW-CONSOLE-COMMANDS-62, the not-yet functions by call sites): GetWaterLevel (cellextensions.cpp
        # OpGetWaterLevel: 0 outdoors, the room's water surface), GetCollidingPC and HurtCollidingActor
        # (miscextensions.cpp: the player touching the object; as HurtStandingActor), GetWeaponType
        # (containerextensions.cpp: the right hand's weapon type, -1 none) and GetStat (statsextensions.cpp: a dummy, 0)
        'getwaterlevel', 'getcollidingpc', 'hurtcollidingactor', 'getweapontype', 'getstat'}
RESISTS = ('resistfire', 'resistfrost', 'resistshock', 'resistmagicka', 'resistdisease', 'resistblight',
           'resistcorprus', 'resistpoison', 'resistnormalweapons', 'resistparalysis')
# v0.0.63 (UNDERWATER-BREATH-62): Get/Set/ModWaterBreathing, the same host call as the resistances (OpenMW 0.51
# statsextensions.cpp OpGetMagicEffect / OpSetMagicEffect / OpModMagicEffect on Water Breathing, effect 0); the
# breath under water reads the magnitude (aw_breath.c)
MAGIC_EFFECT_CALLS = RESISTS + ('waterbreathing',)
# v0.0.63 (MWSCRIPT-GAPS-63, functions no game script of the three masters calls: the console's and add-on content):
# the other effects of OpenMW 0.51 statsextensions.cpp's magic effect table (Chameleon, Water Walking, Swift Swim,
# Jump, Levitate, Shield, Sound, Silence, Blind, Paralyze, Invisibility, Fortify Attack, Sanctuary), the same host call
MAGIC_EFFECT_CALLS += ('chameleon', 'waterwalking', 'swimspeed', 'superjump', 'flying', 'armorbonus', 'castpenalty',
                       'silence', 'blindness', 'paralysis', 'invisible', 'attackbonus', 'defendbonus')
# and the reads and view switches of aw_mwhost.c uncalled_call: the game hour, the moons' phases, the placed position
# and angle, the third-person view, the player's jump, the readied spell, an actor standing on or touching the object
HOST |= {'getcurrenttime', 'getmasserphase', 'getsecundaphase', 'getstartingpos', 'getstartingangle',
         'pcget3rdperson', 'pcforce1stperson', 'pcforce3rdperson', 'getpcjumping', 'getspellreadied',
         'getstandingactor', 'getcollidingactor',
         # batch 2: the player's run and the jump flags (aw_move.c), the armour's weight class in a slot, the faction
         # reads (aw_dial.c), effects ended by number or by spell, the soul gems, the level-up window
         'getpcrunning', 'forcejump', 'clearforcejump', 'forcemovejump', 'clearforcemovejump', 'getforcejump',
         'getforcemovejump', 'getarmortype', 'samefaction', 'getfactionreaction', 'removeeffects',
         'removespelleffects', 'addsoulgem', 'dropsoulgem', 'enablelevelupmenu'}
# batch 3 (v0.0.63, MWSCRIPT-GAPS-63): the console group, which OpenMW 0.51 compiles in any script too (aw_mwhost.c
# console_group_call): Show (a global's value), ShowVars (the object's locals by slot, else the globals), ToggleScripts
# (the dbg mwscript switch), ToggleAI (the walking packages, chim actors ambient), ResetActors (the actors back at their
# start), OutputRefInfo (the reference's id, number, place, script), User1..User4 (OpenMW's test hooks: the name only),
# and the original's console aliases run from a script (noclip, dbg god, dbg killhud, dbg vanitycam, dbg unstuck, dbg tp)
CONSOLE_GROUP = {'show', 'showvars', 'sv', 'togglescripts', 'toggleai', 'tai', 'resetactors', 'ra', 'outputrefinfo',
                 'ori', 'user1', 'user2', 'user3', 'user4', 'togglecollision', 'tcl', 'togglegodmode', 'tgm',
                 'togglemenus', 'tm', 'togglevanitymode', 'tvm', 'centeroncell', 'coc', 'centeronexterior', 'coe',
                 'fixme'}
HOST |= CONSOLE_GROUP
HOST |= {verb + r for r in MAGIC_EFFECT_CALLS for verb in ('get', 'set', 'mod')}
# v0.0.62: the player's control switches, Disable/Enable and the Get...Disabled readers of the seven input switches,
# and Disable/EnableTeleporting and -Levitation (aw_story.h AW_Control*, saved; OpenMW controlextensions.cpp
# OpSetControl / OpGetDisabled, mwinput/controlswitch.cpp, miscextensions.cpp OpEnableTeleporting / OpEnableLevitation;
# MWSCRIPT-PLAYER-CONTROL-62)
CONTROL_SWITCHES = CONTROLS + ('teleporting', 'levitation')
CONTROL_SETS = {verb + c for c in CONTROL_SWITCHES for verb in ('enable', 'disable')}
HOST |= CONTROL_SETS | {'get' + c + 'disabled' for c in CONTROLS}
# v0.0.62: the menus the census office's scripts turn on (CENSUS-INTRO-SCRIPTS-62; OpenMW guiextensions.cpp
# OpEnableWindow for the stats, inventory, magic and map windows, OpShowDialogue for the class, birth and review
# windows of character creation): aw_story.c AW_StoryMenuEnable (saved), aw_opening.c AW_OpeningScriptMenu
MENU_ENABLES = {'enablestatsmenu', 'enableinventorymenu', 'enablemagicmenu', 'enablemapmenu',
                'enableclassmenu', 'enablebirthmenu', 'enablestatreviewmenu',
                # v0.0.63 (MWSCRIPT-GAPS-63): the ship and dock's scripts: the name and race windows (OpShowDialogue
                # GM_Name, GM_Race; aw_intro.c AW_IntroNamePrompt, aw_opening.c AW_OpeningScriptMenu) and the rest
                # allowed (OpEnableRest; aw_story.h AW_MENU_REST, saved)
                'enablenamemenu', 'enableracemenu', 'enablerest'}
HOST |= MENU_ENABLES
HOST_EFFECTS = set(CONTROL_SETS) | MENU_ENABLES | {'placeatpc', 'placeatme', 'placeitem', 'placeitemcell', 'setangle', 'move', 'moveworld', 'setpos', 'setatstart', 'face', 'wakeuppc',
                                    'rotateworld', 'setdelete', 'payfine', 'payfinethief', 'gotojail',
                                    'fadein', 'fadeout', 'fadeto', 'forcesneak', 'clearforcesneak', 'removesoulgem',
                                    'hurtstandingactor', 'hurtcollidingactor', 'drop', 'turnmoonred', 'turnmoonwhite', 'forcerun',
                                    'clearforcerun', 'explodespell', 'pcforce1stperson', 'pcforce3rdperson',
                                    'forcejump', 'clearforcejump', 'forcemovejump', 'clearforcemovejump',
                                    'removeeffects', 'removespelleffects', 'addsoulgem', 'dropsoulgem',
                                    'enablelevelupmenu', 'becomewerewolf', 'undowerewolf',
                                    'setwerewolfacrobatics', 'setscale', 'modscale', 'resurrect', 'playbink', 'changeweather', 'modregion',
                                    'aifollowcell', 'aiescort', 'aiescortcell', 'positioncell','showrestmenu', 'raiserank', 'lowerrank', 'showmap', 'clearinfoactor', 'choice', 'goodbye', 'modfactionreaction', 'setfactionreaction', 'forcegreeting', 'rotate', 'aitravel', 'aifollow', 'position','playgroup', 'loopgroup', 'addtopic', 'cast','setpccrimelevel', 'modpccrimelevel', 'setreputation', 'modreputation', 'pcraiserank',
                'pclowerrank', 'pcjoinfaction', 'pcexpell', 'pcclearexpelled', 'setpcfacrep', 'modpcfacrep'} | \
    {verb + r for r in MAGIC_EFFECT_CALLS for verb in ('set', 'mod')} | CONSOLE_GROUP

# Groups the measurement reports as "the engine does not have it yet" (the brief's list), and the rest.
MISSING_GROUPS = ('ai', 'inventory', 'combat', 'spells', 'position')
ALL_GROUPS = ('core', 'audio', 'journal', 'dialogue', 'ai', 'inventory', 'combat', 'spells', 'position', 'stats',
              'world', 'cell', 'ui', 'anim', 'control', 'time', 'sky', 'console')


class Function:
    __slots__ = ('name', 'ret', 'args', 'group', 'run', 'number')

    def __init__(self, name, ret, args, group):
        self.name, self.ret, self.args, self.group = name, ret, args, group
        self.run = name in RUN or name in HOST
        self.number = None

    def required(self):
        return self.args.split('/')[0]

    def __repr__(self):
        return 'Function(%s %s %s %s)' % (self.name, self.ret, self.args or '-', self.group)


def _build():
    table = {}

    def add(name, ret, args, group):
        if name in table:
            raise ValueError('Duplicate MWScript function ' + name)
        table[name] = Function(name, ret, '' if args == '-' else args, group)

    for line in _TABLE.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        name, ret, args, group = line.split()
        add(name, ret, args, group)
    for a in ATTRIBUTES:
        add('get' + a, 'f', '-', 'stats'); add('set' + a, '-', 'f', 'stats'); add('mod' + a, '-', 'f', 'stats')
    for d in DYNAMICS:
        add('get' + d, 'f', 'x', 'stats'); add('set' + d, '-', 'f', 'stats'); add('mod' + d, '-', 'f', 'stats')
        add('modcurrent' + d, '-', 'f', 'stats'); add('get' + d + 'getratio', 'f', '-', 'stats')
    for s in SKILLS:
        add('get' + s, 'f', '-', 'stats'); add('set' + s, '-', 'f', 'stats'); add('mod' + s, '-', 'f', 'stats')
    for e in EFFECTS:
        add('get' + e, 'l', '-', 'spells'); add('set' + e, '-', 'l', 'spells'); add('mod' + e, '-', 'l', 'spells')
    for c in CONTROLS:
        add('enable' + c, '-', '-', 'control'); add('disable' + c, '-', '-', 'control')
        add('get' + c + 'disabled', 'l', '-', 'control')
    for name in RUN | HOST:
        if name not in table:
            raise ValueError('Run function missing from the table: ' + name)
    return table


FUNCTIONS = _build()
# Every function's number, the operand of a NOTYET call (the import route, docs/MWSCRIPT_BYTECODE.md): the names in
# alphabetical order, so the engine can count each not-yet function and carry one out by its number (host call())
# with the arguments the call already passes, without a new opcode or a change of the file's format. The engine's
# AWF_* numbers (aw_mwcode.h) are checked against these by tests/test_mwscript.py.
FUNCTION_NUMBERS = {name: i for i, name in enumerate(sorted(FUNCTIONS))}
for _name, _fn in FUNCTIONS.items():
    _fn.number = FUNCTION_NUMBERS[_name]
HOST_EFFECT_NUMBERS = frozenset(FUNCTION_NUMBERS[n] for n in HOST_EFFECTS)
KEYWORDS = ('begin', 'end', 'short', 'long', 'float', 'if', 'endif', 'else', 'elseif', 'while', 'endwhile',
            'return', 'messagebox', 'set', 'to')


def lookup(name):
    return FUNCTIONS.get(name.casefold())
