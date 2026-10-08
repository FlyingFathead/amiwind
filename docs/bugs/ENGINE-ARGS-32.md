# ENGINE-ARGS-32: The C start-up passes no arguments from the boot shell

## Status: 8 October 2026

Open. Found by the renderer counters work (branch v0.0.32-counters, not yet merged).

## Symptom

Programs built with our toolchain get `argc` = 1 when started from the boot shell; `awbench`
now reads its arguments with ReadArgs. Whether the engine's own command line works is unchecked.

## Where

Amiga C start-up of the SDK; `engine/aga`.

## How it happened

Unknown.

## Why it was not caught

The engine is started without arguments today.

## Reproduction

Start `awbench cpu` from the boot shell with the plain C start-up.

## Repair

Not yet: check the engine command line; use ReadArgs where arguments matter.

## Verification

Pending.

## Prevention

A boot-shell argument test.
