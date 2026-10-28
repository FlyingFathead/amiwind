# AmiWind v0.0.43-dev4: fixes from the dev2 playtest (in development)

Development snapshot, 18 October 2026, in development. Running on CHIM Engine v0.2.1. Previous snapshot:
[v0.0.43-dev3](RELEASE-v0.0.43-dev3.md). Previous release: [v0.0.42](RELEASE-v0.0.42.md).

Every exterior cell of Vvardenfell on CHIM, as in dev3, with the fixes from the maintainer's dev2 playtest.

## What changed since v0.0.43-dev3

- **Red Mountain's summit** no longer meets a solid sky ceiling
  ([CHIM-RED-MOUNTAIN-SOLID-SKY-43](../../bugs/CHIM-RED-MOUNTAIN-SOLID-SKY-43.md)).
- **Editor markers** (bridge, boat and town markers) are no longer drawn or solid; they stay as invisible
  objects for later sound and effect use ([COLLISION-NC-FLAGS-32](../../bugs/COLLISION-NC-FLAGS-32.md)).
- **Floating plants on Azura's Coast** sit on their trunks again
  ([CHIM-AZURA-FLOATING-FLORA-43](../../bugs/CHIM-AZURA-FLOATING-FLORA-43.md)).
- **Interior plants and trees are sprites by default and NPC heads keep their outline**
  ([INTERIOR-MORAG-TONG-FPS-43](../../bugs/INTERIOR-MORAG-TONG-FPS-43.md),
  [NPC-HEAD-DECIMATION-33](../../bugs/NPC-HEAD-DECIMATION-33.md)).
- **The sea reaches the horizon at Vivec**
  ([VIVEC-ARENA-WATER-FALL-32](../../bugs/VIVEC-ARENA-WATER-FALL-32.md)).
- **Builder:** the CHIM stage uses all its cores
  ([BUILD-STAGE-ALLOWANCE-STUCK-43](../../bugs/BUILD-STAGE-ALLOWANCE-STUCK-43.md)), and the image step accepts a world
  with every cell on CHIM ([BUILD-IMAGE-ALL-CHIM-PREFLIGHT-43](../../bugs/BUILD-IMAGE-ALL-CHIM-PREFLIGHT-43.md)).

## Known in this build

- [CHIM-VIVEC-DOCK-WALKWAY-43](../../bugs/CHIM-VIVEC-DOCK-WALKWAY-43.md): the player still sinks into the Vivec dock
  walkways; the fix waits for a test build.

The rest is as in the [v0.0.43-dev3 notes](RELEASE-v0.0.43-dev3.md#known-in-this-build); everything else is in the
[bug register](../../BUGS.md).
