# Experimental flags

Work that is in the source but not finished, or not yet the default, ships behind a switch that is
off by default. A default build is unchanged by everything on this page; each switch has a test that
checks it is off by default.

| Switch | Where | Default | What it does | State |
| --- | --- | --- | --- | --- |
| `--skip-census` / `aw_skip_census 1` | builder / engine cvar | off | Quick test builds: New Game skips the Census and Excise Office and opens a quick character screen instead | experimental, unfinished (the screen, its console command and its docs are in progress) |
| `--chim-lighting-type hybrid` | builder | hybrid | CHIM lighting: light styles and the night lamp table widened to every class | partial: terrain lightmaps, model light levels and plant glow not yet |

| `--npc-lod on` (config `npc_lod`) | builder | off | Near and far NPC models chosen by distance (engine `dbg npclod`) | experimental: to be compared in game before it becomes the default |
| `--anim-kit off` / `aw_animkit 0` | builder / engine cvar | on | The previous idle-only residents (the kit is the default) | the old method, kept selectable |

| `--npc-head-detail original` (config `npc_head_detail`) | builder | off (auto = budget) | NPC heads keep every original triangle | experimental: unfinished head/body balance, not yet compared in game |

| `--npc-models parts` | builder | whole | NPC gallery models composed from a shared parts library (each body part converted once) | experimental: joint seams and head spikes still open (NPC-JOINT-GAPS-33, NPC-GALLERY-SPIKE-33) |
| `--chim-native-towns on` | builder | off | CHIM towns other than Seyda Neen built from the game data with no legacy region maps (Balmora on CHIM only) | experimental: the Temple sandbox still has an open actor placement case |
| `--night-lamp-lightmaps on` | builder | off | baked night-lamp light (lightstyle 32) on the terrain and buildings of the rebuilt legacy Balmora cores, from `tools/lamp_lightmaps.py` | prototype from v0.0.31 development: untested in a full build; the shipped night lamps stay the engine lights |

More rows are added as the remaining side branches are gathered into this release.
