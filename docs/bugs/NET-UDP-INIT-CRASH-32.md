# NET-UDP-INIT-CRASH-32: UDP network start-up can stop the game at boot when bsdsocket.library is present

## Status: 8 October 2026

Open; runtime impact unverified. Found by the source study for a two-Amiga duel mode.

## Symptom

`engine/aga/src/net_amigaudp.c` uses the `gethostbyname` result without a NULL check (lines
78-80), and two later failures call `Sys_Error` (lines 90 and 135), which ends the game. This code
runs at boot in single-player whenever `bsdsocket.library` opens: a real Amiga TCP/IP stack, or an
emulator's bsdsocket emulation (an option some WinUAE and FS-UAE users enable). No playtest
configuration enables it, so the path has never run.

## Where

`engine/aga/src/net_amigaudp.c` (upstream AmiQuake code, unchanged by AmiWind).

## How it happened

Inherited from upstream; AmiWind never needed networking, so the start-up path was not exercised.

## Why it was not caught

Every test configuration runs without bsdsocket.library.

## Reproduction

To verify: boot with `bsdsocket_library = 1` in FS-UAE (or WinUAE's bsdsocket emulation) and with
no host name resolvable.

## Repair

Not yet: network start-up only when a network game is requested, and failures report and
continue in single-player instead of `Sys_Error`.

## Verification

Pending: an FS-UAE boot with bsdsocket emulation on.

## Prevention

A boot test with bsdsocket emulation in the emulator smoke set.
