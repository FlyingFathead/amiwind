# Local source checkpoint: v0.0.25-rc9

Use the complete update kit to apply rc9 over rc7 or rc8. Replacements are backed
up, checksums are verified and conflicting local edits stop before writes.
The owner's post-rc7 README cleanup is an accepted base and is preserved.

RECOVER-IMAGE.sh rebuilds the engine, default NPC gallery and image from the ORIGINAL failed rc3
full run with passed world-terrain. Do not pass a later image-recovery run.
The original torch is converted during new image assembly; existing terrain,
scenery and music remain intact. No actor waiver is used.

Playtest F/V controls, torch grip/flame, cave lighting and region labels before
running PUBLISH.sh --publish. That script commits/pushes main, checks CI at the
exact commit, tags, creates a source prerelease and verifies downloaded assets.
The owner runs all remote operations. Final v0.0.25 is a later explicit promotion
after the candidate is accepted; existing release tags are not replaced.

NPC gallery is included by default for debugging and regression inspection.
Only explicit `--no-npc-gallery` for exceptional debugging skips it. Default builds fail on missing gallery
payload. Recovery generates this previously omitted catalogue without rebuilding
terrain; expect additional conversion time for its body/outfit variants.

**Warning: gallery omission is for debugging builds only. All NPCs and their
required assets remain necessary for a complete game. `--no-npc-gallery` skips
inspection-only conversion/packaging; it must never remove world NPC placements,
models, dialogue or other gameplay dependencies, or be advertised as a complete
content profile. Normal builds include the NPC gallery for debugging and
regression inspection. This requirement does not claim that every original
world NPC has already been converted or placed by the current demake.**

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
