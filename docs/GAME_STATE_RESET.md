# Game state reset and failed loads

_Last updated with AmiWind v0.0.62-dev2 (8 November 2026)._

## One reset for every game state

New Game (from the main menu) and the console command `dbg restartgame` both reset the game through one registry,
`engine/aga/src/aw_reset.c`. Every part of the engine that keeps game state registers a reset function there; nothing
else resets a game.

A state is anything a game changes that a fresh start does not have: the story stage, script globals and quest
stages, the world change list (objects taken, placed, moved, locked, lights and fires switched), effects, the
character, scene loads in progress, message boxes, the no-burden debug mode (`dbg noburden`).

### Registering a new state

When you add a module that keeps game state, register it at start-up (today the list is in
`engine/aga/src/aw_loadfail.c`, `register_resets`, or from the module's own init function):

```c
AW_ResetRegister("my state", my_reset, my_digest);
```

- `my_reset(int new_game)` puts the module back to what a fresh start has (`new_game` is 1 for New Game, 0 for
  `dbg restartgame`).
- `my_digest()` returns a hash of that state (`AW_ResetHash`), or pass `NULL` when there is nothing to compare.

At the end of the start-up the engine records every digest as a New Game would leave it. After each New Game's reset
it compares them again and prints one console line: either all states are as at a fresh start, or which ones are
not. A state that survives a New Game is therefore named on the console at once. `tests/aga_reset_test.c` checks the
registry's rules.

## dbg restartgame

`dbg restartgame` ends the running game (scene loads, message boxes, story, sounds, the map's memory back to the
level after start-up), then shows the start-up logo and the main menu, as at start-up, without quitting. It also
works after a failed load. The console prints `Boot:` at start-up and `Restart:` after a restart with the memory in
use, so the two can be compared.

## Failed loads

When a load fails (a door, a teleport, a script moving the player, any map load), the player is put back exactly
where they were before it, with the game running, and a message box says so:

- after a teleport: "Unable to teleport, see debug console with F10.";
- after a door or a script: a line of its own.

The console holds the exact reason. The box has two buttons: **OK** stays where you are, **Load Game** opens the load
menu. If the way back fails too, the load menu opens. `dbg loadfail N` (a test aid) makes the next N map loads fail
on purpose: 1 shows the way back, 2 a way back that fails as well.

Every message box shows the mouse pointer; a click on a button chooses it, as the keys do.
