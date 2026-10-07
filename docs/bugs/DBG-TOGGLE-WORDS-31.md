# DBG-TOGGLE-WORDS-31: dbg on/off words turned settings off

## Status: 8 October 2026

Open. Found while checking `dbg fog`; repaired in source, not yet packaged.

## Symptom

`dbg help` says toggle values may be on/off, true/false or 1/0, but for `dbg`
names that map straight onto a setting (`dbg fog`, `dbg skyline fill`,
`dbg fog location`, `dbg warm light` and others) `on` switched the setting off.

## Where

`engine/aga/src/aw_console.c`, `route_format`: the catalogue route passed the
word through unchanged, and Quake reads a setting's value as a number, so
"on" became 0.

## How it happened

Commands with their own argument parsing (`guardtorch`, `headlamp`) accept the
words; settings never did, and the help text promised it for all.

## Why it was not caught

The console tests checked command routes, not routes onto settings with words.

## Reproduction

Any build up to v0.0.31-dev6: `dbg fog on` turns the fog off.

## Repair

A route onto a setting turns on/true/yes into 1 and off/false/no into 0 for a
single argument; commands keep their own words. Native test cases cover both.

## Verification

Native console test; owner check pending.

## Prevention

The help's promise is now covered by a test for settings and commands.
