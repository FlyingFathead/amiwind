# The original game's console commands in AmiWind

_Last updated with AmiWind v0.0.63-dev3 (9 November 2026)._

Debug steps written for the original game work in AmiWind's console as typed: an original console command that does not clash with one of AmiWind's runs AmiWind's own command for the same job, or runs through the game's script interpreter as a script line would. The names are matched without regard to case, the short and long forms alike (tgm and ToggleGodMode). A line may name its target first (player->SetStrength 50); arguments are separated by spaces or commas, and an id with spaces goes in quotes. These names are not listed in dbg help; dbg help mw (or dbg mw help) lists them page by page. A line without a target runs on the console target, chosen with dbg mw target from a list of the references on the map (typed to filter by name, id or kind, nearest first; the input line shows it), or on the player when none is chosen. Item and spell ids are found in the actor table (what an actor carries or a script names), so such a line may take a moment.

With thanks to the UESP for its Morrowind:Console page (https://en.uesp.net/wiki/Morrowind:Console), which lists the original's commands; the list here is also checked against OpenMW 0.51.

391 commands: 18 alias, 282 vm, 3 collision, 75 planned, 13 not applicable.

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
| addtopic |  | Dialogue | planned | its arguments are worked out by the compiler (the topic row) |
| aiactivate |  | Ai | planned | not carried out yet: the ambient tables have no package that walks to an object and uses it |
| aiescort |  | Ai | works (run as a script line) | the MWScript host (aw_mwhost.c host_call AIEscort), on any reference by id-> or the console target |
| aiescortcell |  | Ai | planned | its arguments are worked out by the compiler (the room number) |
| aifollow |  | Ai | works (run as a script line) | the MWScript host (aw_mwhost.c host_call AIFollow), on any reference by id-> or the console target |
| aifollowcell |  | Ai | planned | its arguments are worked out by the compiler (the room number) |
| aitravel |  | Ai | works (run as a script line) | the MWScript host (aw_mwhost.c host_call AITravel), on any reference by id-> or the console target |
| aiwander |  | Ai | works (run as a script line) | the MWScript host (aw_mwhost.c host_wander), on any reference by id-> or the console target |
| becomewerewolf |  | Stats | planned | its arguments are worked out by the compiler (the werewolf settings) |
| betacomment | bc | Misc | not applicable | editor note |
| cast |  | Misc | planned | its arguments are worked out by the compiler (the spell's effect row) |
| cellchanged |  | Cell | planned | an interpreter opcode with compiled arguments (a sound, topic, script or message row) |
| centeroncell | coc | Cell | works (AmiWind's own command) | dbg tp "<cell>" |
| centeronexterior | coe | Cell | works (AmiWind's own command) | dbg tp <x*8192+4096> <y*8192+4096> |
| changeweather |  | Sky | planned | its arguments are worked out by the compiler (the region index) |
| choice |  | Misc | planned | its arguments are worked out by the compiler (a dialogue result only) |
| clearforcejump |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| clearforcemovejump |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| clearforcerun |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| clearforcesneak |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| clearinfoactor |  | Dialogue | planned | its arguments are worked out by the compiler (a dialogue result only) |
| disable |  | Misc | works (run as a script line) | the MWScript host (aw_mwhost.c host_object), on any reference by id-> or the console target |
| disablelevitation |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| disableteleporting |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| dontsaveobject |  | Misc | planned | an interpreter opcode with compiled arguments (a sound, topic, script or message row) |
| drop |  | Misc | planned | its arguments are worked out by the compiler (the item's row) |
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
| enableracemenu |  | Gui | works (AmiWind's own command) | dbg characterchange race |
| enablerest |  | Gui | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| enablestatreviewmenu |  | Gui | works (AmiWind's own command) | dbg quickchar review |
| enablestatsmenu |  | Gui | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| enableteleporting |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| equip |  | Container | works (run as a script line) | the MWScript host (aw_mwhost.c the inventory's equip (the player only)), on any reference by id-> or the console target |
| explodespell |  | Misc | planned | its arguments are worked out by the compiler (the spell's row) |
| face |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| fadein |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| fadeout |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| fadeto |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| fall |  | Misc | planned | an interpreter opcode with compiled arguments (a sound, topic, script or message row) |
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
| getalarm |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (host_actor), on any reference by id-> or the console target |
| getalchemy |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getalteration |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getangle |  | Transformation | works (run as a script line) | the MWScript host (aw_mwhost.c host_call GetAngle), on any reference by id-> or the console target |
| getarmorer |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getarmortype |  | Container | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getathletics |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getattacked |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getaxe |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getblock |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getbluntweapon |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getbuttonpressed |  | Gui | planned | an interpreter opcode with compiled arguments (a sound, topic, script or message row) |
| getcollidingpc |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getconjuration |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getcurrenttime |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getcurrentweather |  | Sky | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getdeadcount |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (host_dead_count), on any reference by id-> or the console target |
| getdestruction |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getdetected |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getdisabled |  | Misc | works (run as a script line) | the MWScript host (aw_mwhost.c host_object), on any reference by id-> or the console target |
| getdisposition |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (host_actor), on any reference by id-> or the console target |
| getdistance |  | Transformation | works (run as a script line) | the MWScript host by the compiler's function table (host_distance), on any reference by id-> or the console target |
| geteffect |  | Misc | planned | its arguments are worked out by the compiler (the effect number) |
| getenchant |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getendurance |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getfactionreaction |  | Dialogue | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getfatigue |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getfight |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (host_actor), on any reference by id-> or the console target |
| getflee |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (host_actor), on any reference by id-> or the console target |
| getforcejump |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getforcerun |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getforcesneak |  | Control | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| gethandtohand |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| gethealth |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getheavyarmor |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| gethello |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (host_actor), on any reference by id-> or the console target |
| getillusion |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getintelligence |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getinterior |  | Cell | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getitemcount |  | Container | works (run as a script line) | the MWScript host (aw_mwhost.c host_item), on any reference by id-> or the console target |
| getjournalindex |  | Dialogue | planned | an interpreter opcode with compiled arguments (a sound, topic, script or message row) |
| getlevel |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (host_actor), on any reference by id-> or the console target |
| getlightarmor |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getlineofsight |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getlocked |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (host_object), on any reference by id-> or the console target |
| getlongblade |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getlos |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getluck |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getmagicka |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getmarksman |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getmasserphase |  | Sky | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getmediumarmor |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getmercantile |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getmysticism |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getpccell |  | Cell | planned | an interpreter opcode with compiled arguments (a sound, topic, script or message row) |
| getpccrimelevel |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
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
| getpos |  | Transformation | works (run as a script line) | the MWScript host (aw_mwhost.c host_position), on any reference by id-> or the console target |
| getrace |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getreputation |  | Dialogue | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getrestoration |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getscale |  | Transformation | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getsecondspassed |  | Misc | planned | an interpreter opcode with compiled arguments (a sound, topic, script or message row) |
| getsecundaphase |  | Sky | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getsecurity |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getshortblade |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getsneak |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getspear |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getspeechcraft |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getspeed |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getspell |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (host_spell), on any reference by id-> or the console target |
| getsquareroot |  | Misc | planned | an interpreter opcode with compiled arguments (a sound, topic, script or message row) |
| getstandingpc |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getstartingpos |  | Transformation | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getstat |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getstrength |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| gettarget |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getunarmored |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getwaterlevel |  | Cell | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getweapondrawn |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getweapontype |  | Container | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getwerewolfkills |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| getwillpower |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| getwindspeed |  | Misc | planned | not carried out yet: the weather has no wind speed yet |
| goodbye |  | Dialogue | planned | its arguments are worked out by the compiler (a dialogue result only) |
| gotojail |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| hassoulgem |  | Container | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| help |  | Misc | AmiWind's own command of that name | AmiWind's help (dbg help); the original's list of commands is under dbg help mw |
| hitattemptonme |  | Misc | planned | not carried out yet: the combat layer keeps only the blows that land (HitOnMe); a missed swing is not kept |
| hitonme |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| hurtcollidingactor |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| hurtstandingactor |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| iswerewolf |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| journal |  | Dialogue | planned | an interpreter opcode with compiled arguments (a sound, topic, script or message row) |
| lock |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (host_object), on any reference by id-> or the console target |
| loopgroup |  | Animation | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| lowerrank |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| menumode |  | Misc | planned | an interpreter opcode with compiled arguments (a sound, topic, script or message row) |
| menutest |  | Gui | not applicable | OpenMW test |
| modacrobatics |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modagility |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modalarm |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (host_actor), on any reference by id-> or the console target |
| modalchemy |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modalteration |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modarmorer |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modathletics |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modaxe |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modblock |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modbluntweapon |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modconjuration |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modcurrentfatigue |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modcurrenthealth |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modcurrentmagicka |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| moddestruction |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| moddisposition |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (host_actor), on any reference by id-> or the console target |
| modenchant |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modendurance |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modfactionreaction |  | Dialogue | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| modfatigue |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modfight |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (host_actor), on any reference by id-> or the console target |
| modflee |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (host_actor), on any reference by id-> or the console target |
| modhandtohand |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modhealth |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modheavyarmor |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modhello |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (host_actor), on any reference by id-> or the console target |
| modillusion |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modintelligence |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modlightarmor |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modlongblade |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modluck |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modmagicka |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modmarksman |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modmediumarmor |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modmercantile |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modmysticism |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modpccrimelevel |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| modpcfacrep |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| modpcvisionbonus |  | Stats | planned | not carried out yet: the renderer has no player-side brightness term (Night Eye) yet; it needs an A/B on the Pi |
| modpersonality |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modregion |  | Sky | planned | its arguments are worked out by the compiler (the region index) |
| modreputation |  | Dialogue | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| modrestoration |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modscale |  | Transformation | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| modsecurity |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modshortblade |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modsneak |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modspear |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modspeechcraft |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modspeed |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modstrength |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modunarmored |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| modwaterlevel |  | Cell | planned | not carried out yet: a room's water is baked into its map; moving it needs moving water in the engine |
| modwillpower |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| move |  | Transformation | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| moveworld |  | Transformation | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| onactivate |  | Misc | planned | an interpreter opcode with compiled arguments (a sound, topic, script or message row) |
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
| placeatme |  | Transformation | planned | its arguments are worked out by the compiler (the placing rows) |
| placeatpc |  | Transformation | planned | its arguments are worked out by the compiler (the placing rows) |
| placeitem |  | Transformation | planned | its arguments are worked out by the compiler (the placing rows) |
| placeitemcell |  | Transformation | planned | its arguments are worked out by the compiler (the placing rows) |
| playbink |  | Misc | not applicable | the original's video player (AmiWind: dbg playvid) |
| playgroup |  | Animation | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| playloopsound3d |  | Misc | planned | an interpreter opcode with compiled arguments (a sound, topic, script or message row) |
| playloopsound3dvp |  | Misc | planned | an interpreter opcode with compiled arguments (a sound, topic, script or message row) |
| playsound |  | Sound | planned | an interpreter opcode with compiled arguments (a sound, topic, script or message row) |
| playsound3d |  | Sound | planned | an interpreter opcode with compiled arguments (a sound, topic, script or message row) |
| playsound3dvp |  | Sound | planned | an interpreter opcode with compiled arguments (a sound, topic, script or message row) |
| playsoundvp |  | Sound | planned | an interpreter opcode with compiled arguments (a sound, topic, script or message row) |
| position |  | Transformation | works (run as a script line) | the MWScript host (aw_mwhost.c host_call Position), on any reference by id-> or the console target |
| positioncell |  | Transformation | works (run as a script line) | the MWScript host (aw_mwhost.c dbg tp to the cell (the player only)), on any reference by id-> or the console target |
| raiserank |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| random |  | Misc | planned | an interpreter opcode with compiled arguments (a sound, topic, script or message row) |
| reloadlua |  | Misc | not applicable | OpenMW Lua |
| removeeffects |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| removefromlevcreature |  | Misc | planned | not carried out yet: the levelled lists are read from the actor table on disk; an edit needs a saved change list |
| removefromlevitem |  | Misc | planned | not carried out yet: the levelled lists are read from the actor table on disk; an edit needs a saved change list |
| removeitem |  | Container | works (run as a script line) | the MWScript host (aw_mwhost.c host_item), on any reference by id-> or the console target |
| removesoulgem |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| removespell |  | Stats | works (run as a script line) | the MWScript host (aw_mwhost.c host_spell), on any reference by id-> or the console target |
| removespelleffects |  | Misc | planned | its arguments are worked out by the compiler (the spell's row) |
| repairedonme |  | Misc | works (AmiWind's own command) | echo 0 (as OpenMW 0.51: always 0) |
| resetactors | ra | Transformation | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| resurrect |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| rotate |  | Transformation | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| rotateworld |  | Transformation | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| samefaction |  | Dialogue | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| say |  | Sound | AmiWind's own command of that name | the engine's chat line (say); the script function Say runs from scripts |
| saydone |  | Sound | planned | an interpreter opcode with compiled arguments (a sound, topic, script or message row) |
| scriptrunning |  | Misc | planned | an interpreter opcode with compiled arguments (a sound, topic, script or message row) |
| setacrobatics |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setagility |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setalarm |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (host_actor), on any reference by id-> or the console target |
| setalchemy |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setalteration |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setangle |  | Transformation | works (run as a script line) | the MWScript host (aw_mwhost.c host_call SetAngle), on any reference by id-> or the console target |
| setarmorer |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setathletics |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setatstart |  | Transformation | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setaxe |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setblock |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setbluntweapon |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setconjuration |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setdelete |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setdestruction |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setdisposition |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (host_actor), on any reference by id-> or the console target |
| setenchant |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setendurance |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setfactionreaction |  | Dialogue | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setfatigue |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setfight |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (host_actor), on any reference by id-> or the console target |
| setflee |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (host_actor), on any reference by id-> or the console target |
| sethandtohand |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| sethealth |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setheavyarmor |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| sethello |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (host_actor), on any reference by id-> or the console target |
| setillusion |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setintelligence |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setjournalindex |  | Dialogue | planned | an interpreter opcode with compiled arguments (a sound, topic, script or message row) |
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
| setpccrimelevel |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setpcfacrep |  | Stats | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setpcvisionbonus |  | Stats | planned | not carried out yet: the renderer has no player-side brightness term (Night Eye) yet; it needs an A/B on the Pi |
| setpersonality |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setpos |  | Transformation | works (run as a script line) | the MWScript host (aw_mwhost.c host_call SetPos), on any reference by id-> or the console target |
| setreputation |  | Dialogue | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setrestoration |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setscale |  | Transformation | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| setsecurity |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setshortblade |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setsneak |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setspear |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setspeechcraft |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setspeed |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setstrength |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setunarmored |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| setwaterlevel |  | Cell | planned | not carried out yet: a room's water is baked into its map; moving it needs moving water in the engine |
| setwerewolfacrobatics |  | Misc | planned | its arguments are worked out by the compiler (the werewolf settings) |
| setwillpower |  | Stats | works (run as a script line) | the MWScript host's actor call (aw_mwhost.c host_actor), on any actor by id-> or the console target |
| show |  | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| showmap |  | Gui | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| showrestmenu |  | Gui | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| showscenegraph | ssg | Misc | not applicable | OpenMW scene graph |
| showvars | sv | Misc | works (run as a script line) | the MWScript host by the compiler's function table (the host's call by number), on any reference by id-> or the console target |
| skipanim |  | Animation | planned | not carried out yet: the animation kit has no per-frame skip |
| startcombat |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (host_combat), on any reference by id-> or the console target |
| startscript |  | Misc | planned | an interpreter opcode with compiled arguments (a sound, topic, script or message row) |
| stopcombat |  | Ai | works (run as a script line) | the MWScript host by the compiler's function table (host_combat), on any reference by id-> or the console target |
| stopscript |  | Misc | planned | an interpreter opcode with compiled arguments (a sound, topic, script or message row) |
| stopsound |  | Sound | AmiWind's own command of that name | the engine's stopsound (all sounds); the script function StopSound runs from scripts |
| streammusic |  | Sound | planned | an interpreter opcode with compiled arguments (a sound, topic, script or message row) |
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
| togglewater | twa | Misc | planned | not carried out yet: a room's water is baked into its map as world surfaces; the renderer has no switch to leave it out |
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
| xbox |  | Misc | planned | an interpreter opcode with compiled arguments (a sound, topic, script or message row) |
