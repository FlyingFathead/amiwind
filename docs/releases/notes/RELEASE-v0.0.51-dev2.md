# AmiWind v0.0.51-dev2 (in development)

Development snapshot, 25 October 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.50](RELEASE-v0.0.50.md). Previous snapshot: [v0.0.51-dev1](RELEASE-v0.0.51-dev1.md).

## New since v0.0.51-dev1

- **The game's scripts: message boxes.** `MessageBox` shows its text with its numbers formatted in (`%d`, `%f`,
  `%g` with a precision, `%%`). A box without buttons is a notice in the message line; a box with buttons stops the
  world until the player chooses (Left/Right or A/D move, Enter, Space, E or the mouse choose, 1-9 choose that
  button), and `GetButtonPressed` reads the choice once, as OpenMW does. EXPERIMENTAL, off by default
  (`dbg mwscript on`) ([the game's scripts](../../MWSCRIPT_BYTECODE.md)).
- **Builds: the CHIM world's checks use more of the machine.** The checks after the CHIM world is built ran mostly
  in one process while the other cores waited: the chunk trees went to the workers as one small array per node
  (441 MB), and every visibility row was decoded bit by bit. On the v0.0.51-dev1 world they take 94 s instead of
  116 s ([BUILD-CHIM-STAGE-SERIAL-TAIL-36](../../bugs/BUILD-CHIM-STAGE-SERIAL-TAIL-36.md)). This snapshot rebuilds the CHIM
  stage once, for its changed checks (the world's own pieces come from the cache).
- **Builds: a change of the cache key rules is caught.** The stage keys of a test build are pinned per key form, so
  a change of what the keys count fails the tests until it raises the form (the dev1 build had rebuilt unchanged
  stages once for such a change).
- **32 MB stays free of "zone full".** The engine smoke now fails a run with 32 MB of Fast RAM or more in which a CHIM
  chunk waited for room in the zone ([CHIM-ZONE-BUDGET-33](../../bugs/CHIM-ZONE-BUDGET-33.md)).

## Known in this build

- Everything in [v0.0.51-dev1's known items](RELEASE-v0.0.51-dev1.md#known-in-this-build) still applies.
- Everything else is in the [bug register](../../BUGS.md).
