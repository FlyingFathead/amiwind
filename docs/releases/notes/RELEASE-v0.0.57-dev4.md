# AmiWind v0.0.57-dev4 (in development)

Development snapshot, 30 October 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.57-dev3](RELEASE-v0.0.57-dev3.md).

v0.0.57, "Remembering The Emperor", is dedicated to the memory of Sir Patrick Stewart (1940-2026), the voice of
Emperor Uriel Septim VII.

The fourth snapshot of v0.0.57: cliff racers come at the player, fish swim, more of the game's scripts run, the race
page shows each race's stats, and more places are lighter to draw. The game needs 32 MB of Fast RAM, and the emulator
presets of this snapshot have it.

## New since v0.0.57-dev3

- **Flyers and swimmers.** A hostile flying creature such as a cliff racer now flies straight at the player instead of
  turning away, and slaughterfish and dreugh swim near where they start, at their own depth, without leaving the water.
- **More of the game's scripts run**: scripts can ask which magic effects are on the player (GetEffect), spells cast
  by scripts cure diseases and deal fire, frost, shock and poison damage, and ForceGreeting makes a character greet the
  player. 899 of the game's 1,207 scripts now run whole.
- **Race stats.** The race page has a View Stats button: the race's base attributes for the chosen sex, its skill
  bonuses and its specials.
- **Lighter places**: more of the heaviest models are drawn with fewer faces in Ald Velothi, Bal Isra, Tel Aruhn,
  Holamayan, the Daedric ruins and the Dwemer ruins, with the same check that keeps the edges where parts meet closed.
- **Settlement list arrivals** land on the street of each place: Bal Isra, Uvirith's Grave and the Vivec Temple no
  longer put the player on a roof or below the ground.
- **Memory**: the larger surface cache of dev2 no longer takes its room from the world cache, which had caused
  "CHIM zone full" now and then at 32 MB ([CHIM-CACHE-SURFCACHE-SQUEEZE-57](../../bugs/CHIM-CACHE-SURFCACHE-SQUEEZE-57.md)).

## Known in this build

- A rare crash on arrival at Gnisis ([SPRITE-BAD-TYPE-THREADED-56](../../bugs/SPRITE-BAD-TYPE-THREADED-56.md)), being
  worked on.
- A few places are slow right after arriving.
- Some rooms still load in after you arrive ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).
