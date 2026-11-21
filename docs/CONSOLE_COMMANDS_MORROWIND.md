# The original game's console commands in AmiWind

_Last updated with AmiWind v0.0.68-dev4 (21 November 2026)._

Debug steps written for the original game work in AmiWind's console as typed: an original console command that does not clash with one of AmiWind's runs AmiWind's own command for the same job, or runs through the game's script interpreter as a script line would. The names are matched without regard to case, the short and long forms alike (tgm and ToggleGodMode). A line may name its target first (player->SetStrength 50); arguments are separated by spaces or commas, and an id with spaces goes in quotes. These names are not listed in dbg help; dbg help mw (or dbg mw help) lists them page by page. A line without a target runs on the console target, chosen with dbg mw target from a list of the references on the map (typed to filter by name, id or kind, nearest first; the input line shows it), or on the player when none is chosen. Item and spell ids are found in the actor table (what an actor carries or a script names), so such a line may take a moment.

With thanks to the UESP for its Morrowind:Console page (https://en.uesp.net/wiki/Morrowind:Console), which lists the original's commands; the list here is also checked against OpenMW 0.51.

502 commands: 22 alias, 428 vm, 3 collision, 36 planned, 13 not applicable.

Very high values of Speed or Acrobatics (SetSpeed, SetAcrobatics) make the player hard to control, as in the original.

## Collisions

These names are AmiWind's own commands; AmiWind's meaning is kept.

| Command | AmiWind |
|---|---|
| help | AmiWind's help (dbg help); the original's list of commands is under dbg help mw |
| say | the engine's chat line (say); the script function Say runs from scripts |
| stopsound | the engine's stopsound (all sounds); the script function StopSound runs from scripts |

## Every command

| Command | Short | Group | State | In AmiWind |
|---|---|---|---|---|
| activate |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (host_object), on any reference by id-> or the console target |
| additem |  | Container | works (run as a script line) | the MWScript host (aw_mwhost.c host_item (an id no actor carries: the player's inventory, dbg give's own call)), on any reference by id-> or the console target |
| addsoulgem |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| addspell |  | Stats | works (run as a script line) | the MWScript host (aw_mwhost.c host_spell), on any reference by id-> or the console target |
| addtolevcreature |  | Misc | planned | not carried out yet: the levelled lists are read from the actor table on disk; an edit needs a saved change list |
| addtolevitem |  | Misc | planned | not carried out yet: the levelled lists are read from the actor table on disk; an edit needs a saved change list |
| addtopic |  | Dialogue | works (run as a script line) | the MWScript host (aw_mwhost.c console_spells: the topic by its name, then the call a compiled AddTopic makes) |
| aiactivate |  | Ai | planned | not carried out yet: the ambient tables have no package that walks to an object and uses it |
| aiescort |  | Ai | works (run as a script line) | the MWScript host (aw_mwhost.c host_call AIEscort), on any reference by id-> or the console target |
| aiescortcell |  | Ai | works (run as a script line) | the MWScript host (aw_mwhost.c console_cell_line: the cell by its name in the compiled scripts' cell table, worked out as the compiler does, then the call a compiled AIEscortCell makes); a cell the game has not starts no package |
| aifollow |  | Ai | works (run as a script line) | the MWScript host (aw_mwhost.c host_call AIFollow), on any reference by id-> or the console target |
| aifollowcell |  | Ai | works (run as a script line) | the MWScript host (aw_mwhost.c console_cell_line: the cell by its name in the compiled scripts' cell table, worked out as the compiler does, then the call a compiled AIFollowCell makes) |
| aitravel |  | Ai | works (run as a script line) | the MWScript host (aw_mwhost.c host_call AITravel), on any reference by id-> or the console target |
| aiwander |  | Ai | works (run as a script line) | the MWScript host (aw_mwhost.c host_wander), on any reference by id-> or the console target |
| becomewerewolf |  | Stats | works (run as a script line) | the MWScript host (aw_mwhost.c console_werewolf: the werewolf's game settings from the compiled scripts, then the call a compiled BecomeWerewolf makes): the player takes the werewolf's attributes and skills, his own kept for UndoWerewolf, his equipped items taken off; an NPC by id-> counts as a werewolf |
| betacomment | bc | Misc | not applicable | editor note |
| cast |  | Misc | works (run as a script line) | the MWScript host (aw_mwhost.c console_spells: the spell by its id; the player selects it, anything else casts it on the target by the call a compiled Cast makes) |
| cellchanged |  | Cell | works (run as a script line) | the MWScript host by the compiler's function table (AW_MwvmCellChanged), on any reference by id-> or the console target |
| centeroncell | coc | Cell | works (AmiWind's own command) | dbg tp "<cell>" |
| centeronexterior | coe | Cell | works (AmiWind's own command) | dbg tp <x*8192+4096> <y*8192+4096> |
| changeweather |  | Sky | works (run as a script line) | the MWScript host (aw_mwhost.c console_weather: the region by its id in the compiled scripts' region table, then the call a compiled ChangeWeather makes): the region's weather 0 (clear) to 9 (blizzard) until its next weather change; a region the image has not is named with the image's regions |
| choice |  | Misc | planned | its arguments are worked out by the compiler (a dialogue result only) |
| clearforcejump |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| clearforcemovejump |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| clearforcerun |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| clearforcesneak |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| clearinfoactor |  | Dialogue | planned | its arguments are worked out by the compiler (a dialogue result only) |
| disable |  | Misc | works (run as a script line) | the MWScript host (aw_mwhost.c host_object), on any reference by id-> or the console target |
| disablelevitation |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| disableplayercontrols |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| disableplayerfighting |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| disableplayerjumping |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| disableplayerlooking |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| disableplayermagic |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| disableplayerviewswitch |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| disableteleporting |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| disablevanitymode |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| dontsaveobject |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (nothing to do, as OpenMW), on any reference by id-> or the console target |
| drop |  | Misc | works (run as a script line) | the MWScript host (aw_mwhost.c console_spells: the item by its id among those the game's Drop and Place calls name, then the call a compiled Drop makes): from the target (id-> or the console target) |
| dropsoulgem |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| enable |  | Misc | works (run as a script line) | the MWScript host (aw_mwhost.c host_object), on any reference by id-> or the console target |
| enablebirthmenu |  | Gui | works (AmiWind's own command) | dbg quickchar birthsign |
| enableclassmenu |  | Gui | works (AmiWind's own command) | dbg quickchar class |
| enableinventorymenu |  | Gui | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| enablelevelupmenu |  | Gui | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| enablelevitation |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| enablemagicmenu |  | Gui | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| enablemapmenu |  | Gui | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| enablenamemenu |  | Gui | works (AmiWind's own command) | dbg quickchar name |
| enableplayercontrols |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| enableplayerfighting |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| enableplayerjumping |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| enableplayerlooking |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| enableplayermagic |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| enableplayerviewswitch |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| enableracemenu |  | Gui | works (AmiWind's own command) | dbg characterchange race |
| enablerest |  | Gui | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| enablestatreviewmenu |  | Gui | works (AmiWind's own command) | dbg quickchar review |
| enablestatsmenu |  | Gui | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| enableteleporting |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| enablevanitymode |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| equip |  | Container | works (run as a script line) | the MWScript host (aw_mwhost.c the inventory's equip (the player only)), on any reference by id-> or the console target |
| explodespell |  | Misc | works (run as a script line) | the MWScript host (aw_mwhost.c console_spells: the spell by its id, then the call a compiled ExplodeSpell makes): at the target (id-> or the console target) |
| face |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| fadein |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| fadeout |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| fadeto |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| fall |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (nothing to do, as OpenMW), on any reference by id-> or the console target |
| filljournal |  | Dialogue | planned | not carried out yet: a debug fill of every journal entry: the dated history keeps only what was earned |
| fillmap |  | Gui | planned | not carried out yet: a debug fill of every map place: the revealed places come one by one from ShowMap |
| fixme |  | Transformation | works (AmiWind's own command) | dbg unstuck |
| forcegreeting |  | Dialogue | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| forcejump |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| forcemovejump |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| forcerun |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| forcesneak |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getacrobatics |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getagility |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getaipackagedone |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (host_ai_package), on any reference by id-> or the console target |
| getalarm |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (host_actor), on any reference by id-> or the console target |
| getalchemy |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getalteration |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getangle |  | Transformation | works (run as a script line) | the MWScript host (aw_mwhost.c host_call GetAngle), on any reference by id-> or the console target |
| getarmorbonus |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getarmorer |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getarmortype |  | Container | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getathletics |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getattackbonus |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getattacked |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getaxe |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getblightdisease |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (host_spell), on any reference by id-> or the console target |
| getblindness |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getblock |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getbluntweapon |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getbuttonpressed |  | Gui | works (run as a script line) | the MWScript host by the compiler's function table (host_button), on any reference by id-> or the console target |
| getcastpenalty |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getchameleon |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getcollidingactor |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getcollidingpc |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getcommondisease |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (host_spell), on any reference by id-> or the console target |
| getconjuration |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getcurrentaipackage |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (host_ai_package), on any reference by id-> or the console target |
| getcurrenttime |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getcurrentweather |  | Sky | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getdeadcount |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (host_dead_count), on any reference by id-> or the console target |
| getdefendbonus |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getdestruction |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getdetected |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getdisabled |  | Misc | works (run as a script line) | the MWScript host (aw_mwhost.c host_object), on any reference by id-> or the console target |
| getdisposition |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (host_actor), on any reference by id-> or the console target |
| getdistance |  | Transformation | works (run as a script line) | the MWScript host by the compiler's function table (host_distance), on any reference by id-> or the console target |
| geteffect |  | Misc | works (run as a script line) | the MWScript host (aw_mwhost.c console_spells: the effect by its game setting id or its number, then the call a compiled GetEffect makes): 1 while an effect of it is on the target |
| getenchant |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getendurance |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getfactionreaction |  | Dialogue | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getfatigue |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getfatiguegetratio |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (host_actor), on any reference by id-> or the console target |
| getfight |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (host_actor), on any reference by id-> or the console target |
| getflee |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (host_actor), on any reference by id-> or the console target |
| getflying |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getforcejump |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getforcemovejump |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getforcerun |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getforcesneak |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| gethandtohand |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| gethealth |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| gethealthgetratio |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (host_actor), on any reference by id-> or the console target |
| getheavyarmor |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| gethello |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (host_actor), on any reference by id-> or the console target |
| getillusion |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getintelligence |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getinterior |  | Cell | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getinvisible |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getitemcount |  | Container | works (run as a script line) | the MWScript host (aw_mwhost.c host_item), on any reference by id-> or the console target |
| getjournalindex |  | Dialogue | works (AmiWind's own command) | aw_mwscript_status call getjournalindex "<quest>" (prints the index kept now) |
| getlevel |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (host_actor), on any reference by id-> or the console target |
| getlightarmor |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getlineofsight |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getlocked |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (host_object), on any reference by id-> or the console target |
| getlongblade |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getlos |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getluck |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getmagicka |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getmagickagetratio |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (host_actor), on any reference by id-> or the console target |
| getmarksman |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getmasserphase |  | Sky | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getmediumarmor |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getmercantile |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getmysticism |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getparalysis |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getpccell |  | Cell | works (run as a script line) | the MWScript host (aw_mwhost.c console_cell_line: the player's cell's name from the compiled scripts' cell table, the room's by its number or the exterior cell's as OpenMW names it, against the typed start, any case) |
| getpccrimelevel |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getpcexpelled |  | Stats | works (AmiWind's own command) | aw_mwscript_status call pcexpelled "<faction>" (the read form of PCExpelled: 1 when the player is expelled) |
| getpcfacrep |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getpcinjail |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getpcjumping |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getpcrank |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getpcrunning |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getpcsleep |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getpcsneaking |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getpctraveling |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getpcvisionbonus |  | Stats | planned | not carried out yet: the renderer has no player-side brightness term (Night Eye) yet; it needs an A/B on the Pi |
| getpersonality |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getplayercontrolsdisabled |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getplayerfightingdisabled |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getplayerjumpingdisabled |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getplayerlookingdisabled |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getplayermagicdisabled |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getplayerviewswitchdisabled |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getpos |  | Transformation | works (run as a script line) | the MWScript host (aw_mwhost.c host_position), on any reference by id-> or the console target |
| getrace |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getreputation |  | Dialogue | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getresistblight |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getresistcorprus |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getresistdisease |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getresistfire |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getresistfrost |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getresistmagicka |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getresistnormalweapons |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getresistparalysis |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getresistpoison |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getresistshock |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getrestoration |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getscale |  | Transformation | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getsecondspassed |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (AW_MwvmFrameSeconds), on any reference by id-> or the console target |
| getsecundaphase |  | Sky | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getsecurity |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getshortblade |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getsilence |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getsneak |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getsoundplaying |  | Sound | works (run as a script line) | the MWScript host (aw_mwhost.c console_sound: the sound by its id among the sounds the game's scripts name): 1 while that sound plays on the target, else 0 |
| getspear |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getspeechcraft |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getspeed |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getspell |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (host_spell), on any reference by id-> or the console target |
| getspelleffects |  | Misc | works (run as a script line) | the MWScript host (aw_mwhost.c console_spells: the spell by its id, then the call a compiled GetSpellEffects makes): 1 while an effect of it is on the target |
| getspellreadied |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getsquareroot |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the square root, as the opcode), on any reference by id-> or the console target |
| getstandingactor |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getstandingpc |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getstartingangle |  | Transformation | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getstartingpos |  | Transformation | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getstat |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getstrength |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getsuperjump |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getswimspeed |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| gettarget |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getunarmored |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getvanitymodedisabled |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getwaterbreathing |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getwaterlevel |  | Cell | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getwaterwalking |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getweapondrawn |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getweapontype |  | Container | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getwerewolfkills |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getwillpower |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getwindspeed |  | Misc | planned | not carried out yet: the weather has no wind speed yet |
| goodbye |  | Dialogue | planned | its arguments are worked out by the compiler (a dialogue result only) |
| gotojail |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| hasitemequipped |  | Misc | works (run as a script line) | the MWScript host (aw_mwhost.c console_spells: the item by its id, then the call a compiled HasItemEquipped makes): 1 when the target wears or holds it |
| hassoulgem |  | Container | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| help |  | Misc | AmiWind's own command of that name | AmiWind's help (dbg help); the original's list of commands is under dbg help mw |
| hitattemptonme |  | Misc | planned | not carried out yet: the combat layer keeps only the blows that land (HitOnMe); a missed swing is not kept |
| hitonme |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| hurtcollidingactor |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| hurtstandingactor |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| iswerewolf |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| journal |  | Dialogue | works (AmiWind's own command) | aw_mwscript_status call journal "<quest>" <index> (a script's Journal: the dated entry; a lower index is ignored) |
| lock |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (host_object), on any reference by id-> or the console target |
| loopgroup |  | Animation | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| lowerrank |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| menumode |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (host_menu_mode), on any reference by id-> or the console target |
| menutest |  | Gui | not applicable | OpenMW test |
| messagebox |  | Gui | planned | an interpreter opcode with compiled arguments (a sound, topic, script or message row) |
| modacrobatics |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modagility |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modalarm |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (host_actor), on any reference by id-> or the console target |
| modalchemy |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modalteration |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modarmorbonus |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| modarmorer |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modathletics |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modattackbonus |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| modaxe |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modblindness |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| modblock |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modbluntweapon |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modcastpenalty |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| modchameleon |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| modconjuration |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modcurrentfatigue |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modcurrenthealth |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modcurrentmagicka |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| moddefendbonus |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| moddestruction |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| moddisposition |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (host_actor), on any reference by id-> or the console target |
| modenchant |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modendurance |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modfactionreaction |  | Dialogue | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| modfatigue |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modfight |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (host_actor), on any reference by id-> or the console target |
| modflee |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (host_actor), on any reference by id-> or the console target |
| modflying |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| modhandtohand |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modhealth |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modheavyarmor |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modhello |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (host_actor), on any reference by id-> or the console target |
| modillusion |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modintelligence |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modinvisible |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| modlightarmor |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modlongblade |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modluck |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modmagicka |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modmarksman |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modmediumarmor |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modmercantile |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modmysticism |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modparalysis |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| modpccrimelevel |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| modpcfacrep |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| modpcvisionbonus |  | Stats | planned | not carried out yet: the renderer has no player-side brightness term (Night Eye) yet; it needs an A/B on the Pi |
| modpersonality |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modregion |  | Sky | works (run as a script line) | the MWScript host (aw_mwhost.c console_weather: the region by its id in the compiled scripts' region table, then the call a compiled ModRegion makes): the region's chances for the rest of the game, up to ten in the weathers' order, each 0 to 100, the ones not given 0; saved |
| modreputation |  | Dialogue | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| modresistblight |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| modresistcorprus |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| modresistdisease |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| modresistfire |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| modresistfrost |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| modresistmagicka |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| modresistnormalweapons |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| modresistparalysis |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| modresistpoison |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| modresistshock |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| modrestoration |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modscale |  | Transformation | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| modsecurity |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modshortblade |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modsilence |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| modsneak |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modspear |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modspeechcraft |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modspeed |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modstrength |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modsuperjump |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| modswimspeed |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| modunarmored |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modwaterbreathing |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| modwaterlevel |  | Cell | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| modwaterwalking |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| modwillpower |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| move |  | Transformation | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| moveworld |  | Transformation | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| onactivate |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (AW_MwvmOnActivate), on any reference by id-> or the console target |
| ondeath |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (host_actor), on any reference by id-> or the console target |
| onknockout |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| onmurder |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| ori |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| outputrefinfo |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| payfine |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| payfinethief |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| pcclearexpelled |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| pcexpell |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| pcexpelled |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| pcforce1stperson |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| pcforce3rdperson |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| pcget3rdperson |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| pcjoinfaction |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| pclowerrank |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| pcraiserank |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| placeatme |  | Transformation | works (run as a script line) | the MWScript host (aw_mwhost.c console_place: the object by its id among those the game's Place calls name, then the call a compiled PlaceAtMe makes): at the target (id-> or the console target) |
| placeatpc |  | Transformation | works (run as a script line) | the MWScript host (aw_mwhost.c console_place: the object by its id among those the game's Place calls name, then the call a compiled PlaceAtPC makes) |
| placeitem |  | Transformation | works (run as a script line) | the MWScript host (aw_mwhost.c console_place: the object by its id among those the game's Place calls name, then the call a compiled PlaceItem makes): in the player's cell |
| placeitemcell |  | Transformation | works (run as a script line) | the MWScript host (aw_mwhost.c console_cell_line: the object among those the game's Place calls name, the cell by its name in the compiled scripts' cell table, then the call a compiled PlaceItemCell makes); a cell the game has not places nothing |
| playbink |  | Misc | not applicable | the original's video player (AmiWind: dbg playvid) |
| playgroup |  | Animation | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| playloopsound3d |  | Misc | planned | runs in scripts; typed on the console not yet: a loop runs while the script that starts it runs; a typed loop has no script to keep it going, and the original's StopSound that ends it is AmiWind's own stopsound here |
| playloopsound3dvp |  | Misc | planned | runs in scripts; typed on the console not yet: a loop runs while the script that starts it runs; a typed loop has no script to keep it going, and the original's StopSound that ends it is AmiWind's own stopsound here |
| playsound |  | Sound | works (run as a script line) | the MWScript host (aw_mwhost.c console_sound: the sound by its id among the sounds the game's scripts name, then the call a compiled PlaySound makes): on the listener |
| playsound3d |  | Sound | works (run as a script line) | the MWScript host (aw_mwhost.c console_sound: the sound by its id among the sounds the game's scripts name, then the call a compiled PlaySound3D makes): at the target (id-> or the console target) |
| playsound3dvp |  | Sound | works (run as a script line) | the MWScript host (aw_mwhost.c console_sound, as PlaySound3D with the volume; the engine's mixer has no pitch) |
| playsoundvp |  | Sound | works (run as a script line) | the MWScript host (aw_mwhost.c console_sound, as PlaySound with the volume; the engine's mixer has no pitch) |
| position |  | Transformation | works (run as a script line) | the MWScript host (aw_mwhost.c host_call Position), on any reference by id-> or the console target |
| positioncell |  | Transformation | works (run as a script line) | the MWScript host (aw_mwhost.c console_cell_line: the cell by its name in the compiled scripts' cell table, worked out as the compiler does: the player into the room's map at that point, or outdoors; anything else the call a compiled PositionCell makes), on any reference by id-> or the console target |
| raiserank |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| random |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (AW_MwvmRandom), on any reference by id-> or the console target |
| reloadlua |  | Misc | not applicable | OpenMW Lua |
| removeeffects |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| removefromlevcreature |  | Misc | planned | not carried out yet: the levelled lists are read from the actor table on disk; an edit needs a saved change list |
| removefromlevitem |  | Misc | planned | not carried out yet: the levelled lists are read from the actor table on disk; an edit needs a saved change list |
| removeitem |  | Container | works (run as a script line) | the MWScript host (aw_mwhost.c host_item), on any reference by id-> or the console target |
| removesoulgem |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| removespell |  | Stats | works (run as a script line) | the MWScript host (aw_mwhost.c host_spell), on any reference by id-> or the console target |
| removespelleffects |  | Misc | works (run as a script line) | the MWScript host (aw_mwhost.c console_spells: the spell by its id, then the call a compiled RemoveSpellEffects makes): on the target (id-> or the console target) |
| repairedonme |  | Misc | works (AmiWind's own command) | echo 0 (as OpenMW 0.51: always 0) |
| resetactors | ra | Transformation | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| resurrect |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| rotate |  | Transformation | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| rotateworld |  | Transformation | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| samefaction |  | Dialogue | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| say |  | Sound | AmiWind's own command of that name | the engine's chat line (say); the script function Say runs from scripts |
| say3d |  | Sound | planned | an interpreter opcode with compiled arguments (a sound, topic, script or message row) |
| saydone |  | Sound | works (run as a script line) | the MWScript host (aw_mwhost.c console_sound, the call a compiled SayDone makes): 1 when the target's spoken line has ended, else 0 |
| scriptrunning |  | Misc | works (run as a script line) | the MWScript host (aw_mwhost.c console_script: the global script by its id, found by its name hash in the compiled scripts): 1 while it runs, else 0 |
| setacrobatics |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setagility |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setalarm |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (host_actor), on any reference by id-> or the console target |
| setalchemy |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setalteration |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setangle |  | Transformation | works (run as a script line) | the MWScript host (aw_mwhost.c host_call SetAngle), on any reference by id-> or the console target |
| setarmorbonus |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setarmorer |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setathletics |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setatstart |  | Transformation | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setattackbonus |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setaxe |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setblindness |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setblock |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setbluntweapon |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setcastpenalty |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setchameleon |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setconjuration |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setdefendbonus |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setdelete |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setdestruction |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setdisposition |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (host_actor), on any reference by id-> or the console target |
| setenchant |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setendurance |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setfactionreaction |  | Dialogue | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setfatigue |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setfight |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (host_actor), on any reference by id-> or the console target |
| setflee |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (host_actor), on any reference by id-> or the console target |
| setflying |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| sethandtohand |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| sethealth |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setheavyarmor |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| sethello |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (host_actor), on any reference by id-> or the console target |
| setillusion |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setintelligence |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setinvisible |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setjournalindex |  | Dialogue | works (AmiWind's own command) | aw_mwscript_status call setjournalindex "<quest>" <index> (the index alone, no entry) |
| setlevel |  | Stats | works (AmiWind's own command) | dbg setlvl <n> (the player) |
| setlightarmor |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setlongblade |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setluck |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setmagicka |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setmarksman |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setmediumarmor |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setmercantile |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setmysticism |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setnavmeshnumber |  | Misc | not applicable | OpenMW navigation mesh |
| setparalysis |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setpccrimelevel |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setpcfacrep |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setpcvisionbonus |  | Stats | planned | not carried out yet: the renderer has no player-side brightness term (Night Eye) yet; it needs an A/B on the Pi |
| setpersonality |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setpos |  | Transformation | works (run as a script line) | the MWScript host (aw_mwhost.c host_call SetPos), on any reference by id-> or the console target |
| setreputation |  | Dialogue | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setresistblight |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setresistcorprus |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setresistdisease |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setresistfire |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setresistfrost |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setresistmagicka |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setresistnormalweapons |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setresistparalysis |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setresistpoison |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setresistshock |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setrestoration |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setscale |  | Transformation | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setsecurity |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setshortblade |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setsilence |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setsneak |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setspear |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setspeechcraft |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setspeed |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setstrength |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setsuperjump |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setswimspeed |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setunarmored |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setwaterbreathing |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setwaterlevel |  | Cell | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setwaterwalking |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setwerewolfacrobatics |  | Misc | works (run as a script line) | the MWScript host (aw_mwhost.c console_werewolf: the game setting fWereWolfAcrobatics from the compiled scripts, then the call a compiled SetWerewolfAcrobatics makes): the player's Acrobatics |
| setwillpower |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| show |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| showmap |  | Gui | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| showrestmenu |  | Gui | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| showscenegraph | ssg | Misc | not applicable | OpenMW scene graph |
| showvars | sv | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| skipanim |  | Animation | planned | not carried out yet: the animation kit has no per-frame skip |
| startcombat |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (host_combat), on any reference by id-> or the console target |
| startscript |  | Misc | works (run as a script line) | the MWScript host (aw_mwhost.c console_script: the global script by its id, found by its name hash in the compiled scripts, started as a compiled StartScript starts it; saved, New Game resets it) |
| stopcombat |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (host_combat), on any reference by id-> or the console target |
| stopscript |  | Misc | works (run as a script line) | the MWScript host (aw_mwhost.c console_script: the global script by its id, found by its name hash in the compiled scripts, stopped as a compiled StopScript stops it; saved, New Game resets it) |
| stopsound |  | Sound | AmiWind's own command of that name | the engine's stopsound (all sounds); the script function StopSound runs from scripts |
| streammusic |  | Sound | works (run as a script line) | the MWScript host (aw_mwhost.c console_sound: the file a script names, else its soundtrack number by the file's stem from the music catalogue, then played once as a compiled StreamMusic plays it, the playlist after it) |
| t3d |  | Misc | not applicable | renderer test |
| testcells |  | Cell | planned | not carried out yet: loading every exterior cell in turn: a test of a desktop engine, far beyond a 32 MB machine |
| testinteriorcells |  | Cell | planned | not carried out yet: loading every interior cell in turn: a test of a desktop engine, far beyond a 32 MB machine |
| testmodels |  | Misc | not applicable | OpenMW model loader test |
| toggleactorspaths | tap | Misc | not applicable | OpenMW navigation mesh |
| toggleai | tai | Ai | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| toggleborders | tb | Misc | planned | not carried out yet: the renderer has no overlay of the cell borders yet |
| togglecollision | tcl | Control | works (AmiWind's own command) | noclip (AmiWind's own tcl) |
| togglecollisionboxes | tcb | Misc | planned | not carried out yet: the renderer has no overlay of the collision boxes yet |
| togglecollisiongrid | tcg | Misc | planned | not carried out yet: the renderer has no overlay of the collision grid yet |
| togglecombatstats | tcs | Console | works (AmiWind's own command) | aw_combat_readout toggled (the combat rolls on the console) |
| toggledebugtext | tdt | Console | works (AmiWind's own command) | dbg hud (the debug HUD, toggles) |
| toggledialoguestats | tds | Console | planned | a console-only command with no AmiWind counterpart yet: a readout of the dialogue filter checks; the dialogue window has no such trace yet |
| togglefogofwar | tfow | Gui | planned | not carried out yet: the map screen reveals places one by one from ShowMap; it has no fog of war to switch off |
| togglefullhelp | tfh | Gui | planned | not carried out yet: the aim box shows the name only; it has no extended reference readout to switch on |
| togglegodmode | tgm | Misc | works (AmiWind's own command) | dbg god |
| togglegrid | tg | Console | planned | a console-only command with no AmiWind counterpart yet: the exterior cell grid drawn over the world; the renderer has no such overlay yet |
| togglekillstats | tks | Console | planned | a console-only command with no AmiWind counterpart yet: a count of the kills by kind; the change list keeps deaths per actor, no tally readout yet |
| togglelights | tl | Console | works (AmiWind's own command) | r_fullbright toggled (the lighting off and on) |
| toggleloadfade |  | Console | planned | a console-only command with no AmiWind counterpart yet: AmiWind's loading screen has no fade to switch |
| togglemagicstats | tms | Console | planned | a console-only command with no AmiWind counterpart yet: a readout of the active effects; dbg cast spell lists spells, not a live overlay |
| togglemenus | tm | Gui | works (AmiWind's own command) | dbg killhud |
| togglenavmesh |  | Misc | not applicable | OpenMW navigation mesh |
| togglepathgrid | tpg | Misc | planned | not carried out yet: the path grids are read per actor from the ambient table; nothing draws them yet |
| togglerecastmesh |  | Misc | not applicable | OpenMW navigation mesh |
| togglescripts |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| togglesky | ts | Sky | planned | not carried out yet: the sky is drawn as part of the world map's sky surfaces; the renderer has no switch to leave it out |
| togglestats | tst | Console | works (AmiWind's own command) | dbg fps (the FPS counter, toggles) |
| toggletexturestring | tts | Console | not applicable | original renderer readout |
| togglevanitymode | tvm | Misc | works (AmiWind's own command) | dbg vanitycam on |
| togglewater | twa | Misc | planned | not carried out yet: a room's water is drawn as its map's world surfaces; the renderer has no switch to leave it out |
| togglewireframe | twf | Misc | not applicable | renderer |
| toggleworld | tw | Misc | planned | not carried out yet: the renderer has no switch to leave out the world map while drawing the objects |
| turnmoonred |  | Sky | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| turnmoonwhite |  | Sky | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| undowerewolf |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| unlock |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (host_object), on any reference by id-> or the console target |
| user1 |  | User | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| user2 |  | User | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| user3 |  | User | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| user4 |  | User | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| wakeuppc |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| xbox |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the constant 0, as OpenMW), on any reference by id-> or the console target |
