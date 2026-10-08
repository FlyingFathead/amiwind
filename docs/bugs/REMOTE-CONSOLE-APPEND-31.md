# REMOTE-CONSOLE-APPEND-31: Remote console log keeps only the last message

## Status: 8 October 2026

Open; fix in source (not yet in a released build).

## Symptom

With `aw_remote 1`, `AWCTL:console.log` should collect every console line
(Quake's `-condebug` log). In a v0.0.31 benchmark session it held three short
fragments after a long run: each new message was written over the start of
the file, so earlier lines (for example the first of two `timerefresh`
results) were lost.

## Where

`engine/aga/src/console.c` `Con_DebugLog` (also used by `-condebug`'s
`qconsole.log`). Present since the remote console pipe was added in
v0.0.31-dev5.

## How it happened

The log is opened with `open(..., O_WRONLY | O_CREAT | O_APPEND)` for every
message. The Amiga C library opens the file at position 0 and does not apply
`O_APPEND`, so every write started at offset 0.

## Why it was not caught

The remote pipe was checked by reading `state.txt` (rewritten in place by
design) and single command results; no test wrote two console lines and read
both back.

## Reproduction

Start a session with `aw_remote 1`, run `timerefresh` twice, read
`AWCTL:console.log`: one result line remains, followed by fragments of
longer earlier lines.

## Repair

Seek to the end of the file after opening it, before writing; skip the write
when the open fails.

## Verification

8 October 2026, FPU-fixes engine on the v0.0.31 image: a 40-second remote
session kept all 40 once-a-second `fpucount` lines plus both `timerefresh`
results in order (the v0.0.31 engine kept one).

## Prevention

Benchmark scripts compare the number of commands sent with the result lines
read back.
