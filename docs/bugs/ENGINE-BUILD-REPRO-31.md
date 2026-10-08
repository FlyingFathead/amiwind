# ENGINE-BUILD-REPRO-31: engine builds from identical source give different binaries

## Status: 8 October 2026

Open; fixed in source (FPU fixes branch, not yet released). Cause: the
`__TIME__`/`__DATE__` stamps in `engine/aga/src/host.c` and `host_cmd.c`; two
builds of one source differed only there. Two fresh builds of the repaired
source are byte-identical.

## Symptom

Two `build_aga.py engine` runs from identical engine sources produced different
binary hashes (`ec169536...` and `7f0be807...`).

## Where

The engine build (`tools/build_aga.py engine`, the Amiga cross-compiler, the
link step and any embedded build data).

## How it happened

The engine embeds the compile time (`__TIME__`, `__DATE__`) in two version strings.

## Why it was not caught

The gates compare an engine binary with its own build receipt, never two
builds of the same source with each other.

## Reproduction

Build the engine twice from the same commit in fresh containers and compare
`AmiWind` hashes.

## Repair

The two version lines print the build's version from `VERSION`
(`Exe: AmiWind v<version>`) instead of the compile time.

## Verification

8 October 2026: two `build_aga.py engine` runs of the same source, each in a
fresh offline builder container, gave the same `AmiWind`
(`3656a07485a304b2c5401bea424b7ddbf931c2759951744b8a24a024752e47a6`, both) and
the same unstripped relink. Adding the linker map (`-Wl,-Map`) for the FPU
check leaves the binary unchanged (two builds before and after: identical).

## Prevention

A gate step that builds twice and compares, as part of the from-scratch build
rule in [DEVELOPMENT.md](../DEVELOPMENT.md).
