# BUILD-FINALIZE-SCENE-31: Image finalisation stops on an undefined name before media staging

## Status: 8 October 2026

Open. Repaired in source (one line); not yet exercised by a full image build.
Present since v0.0.29-dev4.

## Symptom

`tools/build_aga.py image` (and so every guided AGA build) stops with a
Python `NameError: name 'scene' is not defined` in `finalize_image`, after
the map, actor and heap gates and before the music and media are staged. No
HDF is made. Not yet seen in a build log; found reading the source.

## Where

`tools/build_aga.py`, `finalize_image`: the media step reads
`scene/'intro-conversion.json'`, but `scene` is a local of `image()`, not of
`finalize_image`.

## How it happened

v0.0.29-dev4 added the intro conversion receipt to media staging inside
`finalize_image`, using the name `scene` from `image()`. `finalize_image` only
has `args.scene`.

## Why it was not caught

No test runs `finalize_image` to the media step (it needs a complete stage),
the existing tests only check the order of its steps in the source text, and
the toolchain has no undefined-name check. The playtest disks since then were
assembled by adding files to earlier images, which does not run this code.

## Reproduction

In Docker: `symtable` on `tools/build_aga.py` shows `scene` in
`finalize_image` as an unbound global, and the module binds no `scene`.

## Repair

Read the receipt from `Path(args.scene)/'intro-conversion.json'`.

## Verification

The same `symtable` check after the change finds no use of `scene` in
`finalize_image`; full suite in Docker. Pending: a full image build.

## Prevention

A full image build (or a test that runs `finalize_image` on a complete
synthetic stage) before the next release; consider an undefined-name check in
the source gate.
