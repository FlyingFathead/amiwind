# AmiWind v0.0.27-rc4 - Rocks, Mushrooms, and Then Some

Repair candidate in preparation, not release-ready. The preceding rc3 owner playtest returned to AmigaDOS when `dbg aw hors 0` loaded Seyda Neen from Jiub name entry. See [the incident](HEAP_CRASH_v0.0.27-rc3.md).

The repair work removes duplicate incoming visibility buffers, measures bounded town payloads, and investigates renderer storage for collision-only BSP nodes. These are separate changes and require matching final-map estimates, target allocation-lifetime profiling and exact packaged playtesting. A static pass is not incident closure.

Every newly compiled image must advance the release-candidate number. Preserve earlier images and their receipts; never relabel an older engine as a new candidate. Engine-only experiments within this candidate have distinct numbered workspaces and must identify their actual embedded VERSION.

The current rectangular subdivision proposal still has inadequate growth room in some maps. Off-centre boundary shifts are valid candidates: compare both resulting payloads, preserve coverage and collision, and verify crossings in both directions. Heatmap density is a guide, not a heap measurement. Do not lower the 3 MiB non-map reserve or 2 MiB safety margin to accept a candidate.

Publication remains owner-run on Linux after final preparation and target acceptance.
