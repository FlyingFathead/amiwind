# AmiWind v0.0.25-rc9

Original carried torch and source-region debug header. Complete source update
from rc7 or rc8; includes the rc8 brush-lighting crash correction.

- Convert the owner's original `torch` mesh, materials and holding animation.
  Preserve all 238 torch triangles; attach source-textured flames to its emitter.
  Support both 3D hands and the existing sprite build option.
- Use the carried-light attachment rotation and source BoneOffset; replace the
  independent placeholder shaft. Document the source anatomy in [TORCH.md](TORCH.md).
- Show `AmiWind v<version> Vvardenfell / <original region name>` in the debug
  header. Resolve player source coordinates through CELL/RGNN to REGN/FNAM.
  Interior headers retain their original area name; missing data is not guessed.
- Add toggleable original-game CELL boundaries/labels to the generated world
  atlas, separate from generated terrain-region boundaries.
- Document the asset/reference catalogue and future asset gallery. Record the
  confirmed scaled-flora omission and the distinction between HDF capacity and
  actual file payload. These scenery omissions are not repaired by this update.

The longstanding brief fist blink repeats roughly every 1–2 seconds; hands are
visible between blinks. Its cause remains open. F once becoming unresponsive is
a separate unreproduced state report. Neither is declared fixed here.

[Validation](validation/rc9-source.json) records checks actually performed.
A complete rc9 game image and target-emulator playtest remain owner-side work.
Run [engine/gallery/image recovery](IMAGE_RECOVERY.md) against the original retained rc3
conversion; terrain/music are reused, strict actor checks stay enabled. Generated
torch assets remain private. No game data, HDFs or ROMs are in this source package.

Test this checkpoint before deciding on final v0.0.25. The asset gallery remains
future work rather than another untested feature added to this checkpoint.

NPC gallery is included by default for debugging and regression inspection.
Only an explicit `--no-npc-gallery` for exceptional debugging purposes skips it. Default builds fail on missing gallery
payload. Recovery generates this previously omitted catalogue without rebuilding
terrain; expect additional conversion time for its body/outfit variants.

**Warning: gallery omission is for debugging builds only. All NPCs and their
required assets remain necessary for a complete game. `--no-npc-gallery` skips
inspection-only conversion/packaging; it must never remove world NPC placements,
models, dialogue or other gameplay dependencies, or be advertised as a complete
content profile. Normal builds include the NPC gallery for debugging and
regression inspection. This requirement does not claim that every original
world NPC has already been converted or placed by the current demake.**

**All NPCs must be included and loadable by the engine for the game to be complete.
NPC gallery creation MUST NOT be skipped except for exceptional, explicitly
requested debugging purposes. Build time and disk usage are not reasons to omit it.**

**Outside approval is required for any exception affecting either gallery.**
Neither the NPC gallery nor the upcoming static-asset gallery may be disabled,
reduced or bypassed, including model/asset generation, catalogue coverage,
quality and validation, without a specific documented case or scenario **and
explicit approval from the project owner**. A builder or contributor cannot
approve its own exception. Build time, disk pressure and convenience do not
supply that approval. An opt-out flag is a mechanism for an approved exceptional
debugging case, not permission to choose that exception independently.

All NPCs and other game assets must remain intact, packaged and loadable by the
engine for the complete game to function properly. Skipping their creation
alongside either gallery is pointless and counterproductive: the final product
requires those assets anyway. An exceptional debug build must be labelled
incomplete and cannot redefine the complete game's required content. Runtime
loading may be on demand; this does not require every asset to reside in RAM
simultaneously. The static-asset gallery is still planned, not implemented.
