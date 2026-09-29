# AmiWind v0.0.23-dev2 corresponding runtime source

Created by FlyingFathead a.k.a. Horstator. Thanks to ChaosWhisperer.
Portions are based on id Software Quake, Peter McGavin's Amiga work,
NovaCoder's AmiQuake and Stephen Leary / terriblefire's GCC port, under GPLv2.
Original notices are retained; see engine/aga/COPYING and docs/aga/COPYING.NEWLIB, relative to the repository root.
No Quake/Morrowind assets, ROMs, compiled programs or binary-recovered assembly.
Pinned upstream: https://github.com/terriblefire/amiquake
Commit: 9c62d905151614af3e788ae3145a0d4ecc8a7bb8

This engine lives at `engine/aga/` inside the single `amiwind/` repository.
Edit C sources under `engine/aga/src/`. Use the repository's builder to compile
an external copy with AmigaPorts GCC 16.2-rc11 (16.2.0b20260825082934):

```sh
python3 tools/build_aga.py engine --sdk /external/m68k-amigaos-gcc-16.2 --out ../engine-build
```

The engine executable is `../engine-build/runtime/build/AmiQuakeGCC`; the
preflight program is alongside it as `AmiWindCheck`. Dev7 prints the AmiWind
version in the preflight banner and pass/fail footer, plus guest-observable CPU/FPU,
AGA, timing and memory checks. A successful report stays visible for a five-second
countdown; Space or Enter skips immediately. Host-only UAE settings are verified by
the portable launcher rather than guessed inside the Amiga. The source checkout remains
free of object files and compiled binaries. See LINUX_BUILD.md and AGA_BUILD.md.

Independent C2P and GPL C spans are used. Output build/AmiQuakeGCC is renamed
AmiWind in the boot image. The same repository includes
qcc and image-building recipes in docs/LINUX_BUILD.md and tools/build_aga.py.
No game data or ROM is needed to compile the engine. Locally converted owned
Morrowind files and a licensed ROM are required for the emulated demo.
See CHECKPOINT_017_VALIDATION.md for the exact native test scope.
Runtime: GPLv2-compatible. Separate host conversion tools: GPL-3.0-only.

The same source supports the experimental sprite-hand build. Pass
`--hands sprites` to the engine builder.
The default is 0 (3D hands). The guided builder exposes `--hands
sprites` and matches the image's QuakeC/asset choices to the engine receipt.
Using the default image data with a differently compiled engine is unsupported.
See FIRST_PERSON_HANDS.md and CONVERSION_RECIPES.md.

The dev2 expanded area reserves an 11 MiB game heap within the unchanged 16 MiB
Fast RAM reference machine. Preflight checks 14 MiB free Fast RAM before loading
the engine, including a contiguous 11 MiB + 16 bytes. The heap is not the whole
working set. Renderer pools are bounded to 12,288 surfaces and 24,576 edges; entity
visibility links have 8,192 entries. Test logs, rather than the old checkpoint
memory figures, describe the current build.
