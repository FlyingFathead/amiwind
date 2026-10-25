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
       'messagebox', 'getbuttonpressed'}

# Groups the measurement reports as "the engine does not have it yet" (the brief's list), and the rest.
MISSING_GROUPS = ('ai', 'inventory', 'combat', 'spells', 'position')
ALL_GROUPS = ('core', 'audio', 'journal', 'dialogue', 'ai', 'inventory', 'combat', 'spells', 'position', 'stats',
              'world', 'cell', 'ui', 'anim', 'control', 'time', 'sky', 'console')


class Function:
    __slots__ = ('name', 'ret', 'args', 'group', 'run')

    def __init__(self, name, ret, args, group):
        self.name, self.ret, self.args, self.group = name, ret, args, group
        self.run = name in RUN

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
    for name in RUN:
        if name not in table:
            raise ValueError('Run function missing from the table: ' + name)
    return table


FUNCTIONS = _build()
KEYWORDS = ('begin', 'end', 'short', 'long', 'float', 'if', 'endif', 'else', 'elseif', 'while', 'endwhile',
            'return', 'messagebox', 'set', 'to')


def lookup(name):
    return FUNCTIONS.get(name.casefold())
