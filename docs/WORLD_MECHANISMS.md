# World mechanisms

_Last updated with AmiWind v0.0.64-dev1 (10 November 2026)._

<!-- contents start -->
## Contents

- [Summary](#summary)
- [Traps](#traps)
- [Morrowind.esm](#morrowindesm)
- [Tribunal.esm](#tribunalesm)
- [Bloodmoon.esm](#bloodmoonesm)

<!-- contents end -->

The objects in the world that the player works to change something else: switches, levers, wheels, valves and buttons whose script moves, turns, enables, disables, locks, unlocks or activates another object, and the doors and containers that carry a trap spell. Counted from the game's masters by `tools/world_mechanisms.py`; the state of each script is the MWScript tracker's (docs/mwscript-features.json, docs/MWSCRIPT_FEATURES.md). An object that only animates itself, or sets a global that another object's script reads, is not counted here.

Masters read: Morrowind.esm, Tribunal.esm, Bloodmoon.esm.

## Summary

| Master | Activators acting on another object | Worked by the player (OnActivate) | Scripts that run |
|---|---:|---:|---:|
| Morrowind.esm | 30 | 26 | 29 |
| Tribunal.esm | 6 | 1 | 0 |
| Bloodmoon.esm | 18 | 9 | 0 |

## Traps

A door or container with a trap spell casts it on the one who opens it without disarming it first; the trap is used up when it is sprung, and the door's or container's key disarms it (the rule OpenMW follows). Trapped references: 468.

| Kind | References |
|---|---:|
| container | 290 |
| hinged door | 167 |
| load door | 11 |

| Master | References |
|---|---:|
| Bloodmoon.esm | 8 |
| Morrowind.esm | 457 |
| Tribunal.esm | 3 |

| Trap spell | References |
|---|---:|
| trap_shock00 | 48 |
| trap_fire00 | 42 |
| trap_frost00 | 38 |
| trap_health00 | 35 |
| trap_poison00 | 35 |
| trap_paralyze00 | 21 |
| potent poison | 17 |
| deadly poison | 16 |
| trap_silence00 | 15 |
| five fingers of pain | 11 |
| blind | 10 |
| burning touch | 9 |
| armor eater | 7 |
| ironhand | 7 |
| shockbite | 6 |
| shocking touch | 6 |
| wounding touch | 6 |
| curse fatigue | 5 |
| black hand | 4 |
| dread curse: health | 4 |
| dread curse: strength | 4 |
| exhausting touch | 4 |
| fire bite | 4 |
| paralysis | 4 |
| sp_hvaulttrap | 4 |
| spider touch | 4 |
| sting | 4 |
| thunder fist | 4 |
| curse agility | 3 |
| curse health | 3 |
| curse strength | 3 |
| flay spirit | 3 |
| hornhand | 3 |
| magicka leech | 3 |
| misfortunate touch | 3 |
| touchdrain security | 3 |
| blood sacrifice | 2 |
| burden touch | 2 |
| clumsy touch | 2 |
| crushing burden touch | 2 |
| curse intelligence | 2 |
| dread curse: fatigue | 2 |
| dread curse: intelligence | 2 |
| dread curse: speed | 2 |
| firefist | 2 |
| freezing touch | 2 |
| fuddle | 2 |
| ghost curse | 2 |
| heartbite | 2 |
| poisonous touch | 2 |
| sp_glyphofweakness | 2 |
| spite touch | 2 |
| stormhand | 2 |
| trap_poison_killer | 2 |
| weapon eater | 2 |
| woe | 2 |
| alad's caliginy | 1 |
| alit bite | 1 |
| burden of sin | 1 |
| cruel noise | 1 |
| curse luck | 1 |
| curse speed | 1 |
| curse spell points | 1 |
| curse willpower | 1 |
| doze | 1 |
| drain blood | 1 |
| dread curse: willpower | 1 |
| flame | 1 |
| frostbite | 1 |
| gash spirit | 1 |
| hand of decay | 1 |
| hand of sleep | 1 |
| heavy burden touch | 1 |
| noise | 1 |
| soul trap | 1 |
| soulpinch | 1 |
| spirit knife | 1 |
| strength leech | 1 |
| tempting touch | 1 |
| touchdrain agility | 1 |
| touchdrain alteration | 1 |
| touchdrain block | 1 |
| touchdrain mercantile | 1 |
| trap_frost_killer | 1 |
| viper | 1 |
| weakening touch | 1 |

## Morrowind.esm

| Activator | Name | Script | Player | Placed in | Acts on | State |
|---|---|---|---|---|---|---|
| active_dae_azura | Statue of Azura | DaedraAzura | yes | Shrine of Azura | golden saint_staada (enables), daedroth_az (enables), hunger_az_01 (enables), atronach_flame_az (enables), atronach_storm_az (enables), hunger_az_02 (enables) and 1 more | runs |
| active_dae_malacath | Statue of Malacath | DaedraMalacath | yes | Assurdirapal, Inner Shrine | farvyn oreyn (enables), dreynis nothro (enables), vala herennius (enables), netch_bull_dead (enables), netch_bull_dead_2 (enables) | runs |
| active_dae_mephala | Shrine to Mephala | DaedraMephala | yes | not placed | balyn omavel (disables), balyn omavel-dead (enables), furn_de_p_chair_02_uni2 (enables), misc_com_metal_plate_07_uni2 (enables), ingred_bread_01_uni2 (enables), misc_com_wood_knife_uni2 (enables) and 7 more | runs |
| active_dae_molagbal | Statue of Molag Bal | DaedraMolagBal | yes | Yansirramus, Shrine | daedroth_menta_unique (enables) | runs |
| active_dae_sheogorath | Statue of Sheogorath | DaedraSheogorath | yes | Ihinipalit, Shrine | netch_giant_unique (enables) | runs |
| active_nels_pelagiad | Nels Llendo Scriptholder | nels_llendoScript | no | Pelagiad (0, -7) | nels llendo (moves) | runs |
| active_port_andra | Andasreth Propylon | Warp_Andra | yes | Berandas, Propylon Chamber, Hlormaren, Propylon Chamber | player (moves) | runs |
| active_port_beran | Berandas Propylon | Warp_Beran | yes | Andasreth, Propylon Chamber, Falasmaryon, Propylon Chamber | player (moves) | runs |
| active_port_falas | Falasmaryon Propylon | Warp_Falas | yes | Berandas, Propylon Chamber, Valenvaryon, Propylon Chamber | player (moves) | runs |
| active_port_falen | Falensarano Propylon | Warp_Falen | yes | Indoranyon, Propylon Chamber, Telasero, Propylon Chamber | player (moves) | runs |
| active_port_hlor | Hlormaren Propylon | Warp_Hlor | yes | Andasreth, Propylon Chamber, Marandus, Propylon Chamber | player (moves) | runs |
| active_port_indo | Indoranyon Propylon | Warp_Indo | yes | Falensarano, Propylon Chamber, Rotheran, Propylon Chamber | player (moves) | runs |
| active_port_maran | Marandus Propylon | Warp_Maran | yes | Hlormaren, Propylon Chamber, Telasero, Propylon Chamber | player (moves) | runs |
| active_port_roth | Rotheran Propylon | Warp_Roth | yes | Indoranyon, Propylon Chamber, Valenvaryon, Propylon Chamber | player (moves) | runs |
| active_port_telas | Telasero Propylon | Warp_Telas | yes | Falensarano, Propylon Chamber, Marandus, Propylon Chamber | player (moves) | runs |
| active_port_valen | Valenvaryon Propylon | Warp_Valen | yes | Falasmaryon, Propylon Chamber, Rotheran, Propylon Chamber | player (moves) | runs |
| active_velothi_altar_Mephala | Altar to Mephala | DaedraMephala | yes | Vivec, Arena Hidden Area | balyn omavel (disables), balyn omavel-dead (enables), furn_de_p_chair_02_uni2 (enables), misc_com_metal_plate_07_uni2 (enables), ingred_bread_01_uni2 (enables), misc_com_wood_knife_uni2 (enables) and 7 more | runs |
| azura spirit | - | AzuraEnd | no | Dagoth Ur, Facility Cavern | ring of azura (enables) | runs |
| ex_dwrv_crank_dagoth | Dwarven Crank | Dagoth_doors | yes | Dagoth Ur (2, 8) | dagoth_door00 (turns), dagoth_door01 (turns) | runs |
| ex_gg_gateswitch_01 | Switch | GG_OpenGate1 | yes | Ghostgate (2, 4) | ex_gg_portcullis_01 (moves) | runs |
| ex_gg_gateswitch_02 | Switch | GG_OpenGate2 | yes | Ghostgate (2, 4), Red Mountain Region (2, 5) | ex_gg_portcullis_02 (moves) | runs |
| in_dwrv_crank_akula00 | Dwarven Crank | Akula_innerdoors | yes | Akulakhan's Chamber | akula_door00 (turns), akula_door01 (turns) | runs |
| in_dwrv_crank_akula10 | Dwarven Crank | Akula_outerdoors | yes | not placed | akula door b (turns), akula door a (turns) | inert: its records are never placed and nothing makes them: it never runs in the original either |
| in_dwrv_crank_arkn | Dwarven Crank | Arkn_doors | yes | Molag Mar Region (0, -2) | arkn_door00 (turns), arkn_door01 (turns) | runs |
| in_dwrv_crank_nchuleft_01 | Dwarven Crank | nchuleftingthWrong1 | yes | Nchuleftingth, Test of Pattern | steam_nchuleftingth_01 (disables, enables) | runs |
| in_dwrv_crank_nchuleft_02 | Dwarven Crank | nchuleftingthWrong2 | yes | Nchuleftingth, Test of Pattern | steam_nchuleftingth_02 (disables, enables) | runs |
| in_dwrv_crank_nchuleft_03 | Dwarven Crank | nchulfetingthRight | yes | Nchuleftingth, Test of Pattern | in_dwrv_wall_nchuleftingth1 (disables, moves) | runs |
| lucan_scriptholder | Lucan Scriptholder | lucan_ostorius | no | Ald-ruhn (-2, 6) | lucan ostorius (disables) | runs |
| misc_skull00_shishi | A Breton Skull | Shishi_door | yes | Shishi | in_velothi_platform_shishi (moves) | runs |
| puzzle canal stairs | - | puzzlecanal | no | Vivec, Puzzle Canal, Center | puzzle canal bridge a (disables, enables), puzzle canal bridge b (disables, enables), puzzle canal glow (disables), puzzle canal force field (disables) | runs |

## Tribunal.esm

| Activator | Name | Script | Player | Placed in | Acts on | State |
|---|---|---|---|---|---|---|
| act_dwe_powerbox00 | Dwemer Junction Box | powerboxScript | yes | Bamz-Amschend, Skybreak Gallery | misc_dwrv_weather2 (enables) | not-in-image: placed only in an add-on world, not in the image yet |
| act_sotha_red00 | - | sothalightScript | no | Sotha Sil, Dome of Serlyn | act_sotha_green00 (disables, enables), act_sotha_red10 (enables, disables), act_sotha_green10 (disables, enables) | not-in-image: placed only in an add-on world, not in the image yet |
| active_assassin_unique | - | barAssScript | no | Mournhold, Royal Palace: Barenziah's Chambers | light_bar1_out_unique (disables, enables), light_bar2_out_unique (disables, enables), light_bar3_out_unique (disables, enables), light_bar4_out_unique (disables, enables), light_bar5_out_unique (disables, enables), light_bar6_out_unique (disables, enables) and 10 more | not-in-image: placed only in an add-on world, not in the image yet |
| Script_IgnBBot2 | Script_IgnBBot2 | IgnatiusBBot2Script | no | Mournhold, Ignatius Flaccus' House | centurion_spider_bbot3 (disables, enables), centurion_steam_bbot4 (disables, enables), centurion_sphere_bbot5 (disables, enables), centurion_sphere_bbot6 (disables, enables), centurion_spider_bbot7 (disables, enables), centurion_steam_bbot8 (disables, enables) and 7 more | not-in-image: placed only in an add-on world, not in the image yet |
| Script_PlayScript | Script_PlayScript | playScript | no | Mournhold, Great Bazaar | in_mh_door_02_play (activates) | not-in-image: placed only in an add-on world, not in the image yet |
| Script_Taren_Enable | Script_Taren_Enable | tarenEnableScript | no | not placed | taren andoren (disables, enables) | inert: its records are never placed and nothing makes them: it never runs in the original either |

## Bloodmoon.esm

| Activator | Name | Script | Player | Placed in | Acts on | State |
|---|---|---|---|---|---|---|
| Act_BM_pipe_01 | Hollow Stalagmite | stal1Script | yes | Solstheim, Chamber of Song | act_bm_steam_01 (enables) | not-in-image: placed only in an add-on world, not in the image yet |
| Act_BM_pipe_02 | Hollow Stalagmite | stal2Script | yes | Solstheim, Chamber of Song | act_bm_steam_02 (enables) | not-in-image: placed only in an add-on world, not in the image yet |
| Act_BM_pipe_03 | Hollow Stalagmite | stal3Script | yes | Solstheim, Chamber of Song | act_bm_steam_03 (enables) | not-in-image: placed only in an add-on world, not in the image yet |
| Act_BM_pipe_05 | - | stalloopScript | no | Solstheim, Chamber of Song | act_bm_steam_04 (enables), act_bm_steam_05 (enables), act_bm_steam_06 (enables), act_bm_steam_02 (enables), act_bm_steam_03 (enables), act_bm_steam_01 (enables) | not-in-image: placed only in an add-on world, not in the image yet |
| Act_BM_stone_beast_01 | Beast Stone | stoneBeastsScript | yes | Felsaad Coast Region (-20, 24) | act_bm_beast_parts (enables) | not-in-image: placed only in an add-on world, not in the image yet |
| Act_BM_stone_earth_01 | Earth Stone | stoneEarthScript | yes | Hirstaang Forest Region (-26, 20) | act_bm_earth_parts (enables) | not-in-image: placed only in an add-on world, not in the image yet |
| Act_BM_stone_sun_01 | Sun Stone | stoneSunScript | yes | Isinfier Plains Region (-20, 19) | act_bm_sun_parts (enables) | not-in-image: placed only in an add-on world, not in the image yet |
| Act_BM_stone_tree_01 | Tree Stone | stoneTreesScript | yes | Isinfier Plains Region (-22, 21) | act_bm_tree_parts (enables) | not-in-image: placed only in an add-on world, not in the image yet |
| Act_BM_stone_water_01 | Water Stone | stoneWaterScript | yes | Moesring Mountains Region (-26, 23) | act_bm_water_parts (enables) | not-in-image: placed only in an add-on world, not in the image yet |
| Act_BM_stone_wind_01 | Wind Stone | stoneWindScript | yes | Moesring Mountains Region (-22, 25) | act_bm_wind_parts (enables) | not-in-image: placed only in an add-on world, not in the image yet |
| active_frostattack_unique | - | cariusgoneScript | no | Fort Frostmoth (-22, 17) | falx carius (disables), gaea artoria (enables), saenus lusius (enables) | not-in-image: placed only in an add-on world, not in the image yet |
| Colony_Assassin_act | - | ColonyAssassinItems | no | Raven Rock (-25, 19) | cimber valerius (disables), capiton popillius (disables), steel arrow_carnius (disables, enables), steel longbow_carnius (disables, enables), sc_hiddenkiller (disables, enables), baslod (disables, enables) | not-in-image: placed only in an add-on world, not in the image yet |
| In_Thirsk_archpiece01 | Rubble | ThirskRubble | no | Solstheim, Thirsk | ingred_udyrfrykte_heart (enables, disables), bm_misc_skull_griss_floor (disables, enables), in_thirsk_columnpiece01 (disables, enables), in_thirsk_columnpiece02 (disables, enables), in_thirsk_archpiece02 (disables, enables), in_thirsk_beampiece01 (disables, enables) and 14 more | not-in-image: placed only in an add-on world, not in the image yet |
| In_Thirsk_archpiece02 | Rubble | ThirskRubble | no | Solstheim, Thirsk | ingred_udyrfrykte_heart (enables, disables), bm_misc_skull_griss_floor (disables, enables), in_thirsk_columnpiece01 (disables, enables), in_thirsk_columnpiece02 (disables, enables), in_thirsk_archpiece01 (disables, enables), in_thirsk_beampiece01 (disables, enables) and 14 more | not-in-image: placed only in an add-on world, not in the image yet |
| In_Thirsk_beampiece01 | Rubble | ThirskRubble | no | Solstheim, Thirsk | ingred_udyrfrykte_heart (enables, disables), bm_misc_skull_griss_floor (disables, enables), in_thirsk_columnpiece01 (disables, enables), in_thirsk_columnpiece02 (disables, enables), in_thirsk_archpiece01 (disables, enables), in_thirsk_archpiece02 (disables, enables) and 14 more | not-in-image: placed only in an add-on world, not in the image yet |
| In_Thirsk_beampiece03 | Rubble | ThirskRubble | no | Solstheim, Thirsk | ingred_udyrfrykte_heart (enables, disables), bm_misc_skull_griss_floor (disables, enables), in_thirsk_columnpiece01 (disables, enables), in_thirsk_columnpiece02 (disables, enables), in_thirsk_archpiece01 (disables, enables), in_thirsk_archpiece02 (disables, enables) and 14 more | not-in-image: placed only in an add-on world, not in the image yet |
| In_Thirsk_columnpiece01 | Rubble | ThirskRubble | no | Solstheim, Thirsk | ingred_udyrfrykte_heart (enables, disables), bm_misc_skull_griss_floor (disables, enables), in_thirsk_columnpiece02 (disables, enables), in_thirsk_archpiece01 (disables, enables), in_thirsk_archpiece02 (disables, enables), in_thirsk_beampiece01 (disables, enables) and 14 more | not-in-image: placed only in an add-on world, not in the image yet |
| In_Thirsk_columnpiece02 | Rubble | ThirskRubble | no | Solstheim, Thirsk | ingred_udyrfrykte_heart (enables, disables), bm_misc_skull_griss_floor (disables, enables), in_thirsk_columnpiece01 (disables, enables), in_thirsk_archpiece01 (disables, enables), in_thirsk_archpiece02 (disables, enables), in_thirsk_beampiece01 (disables, enables) and 14 more | not-in-image: placed only in an add-on world, not in the image yet |
