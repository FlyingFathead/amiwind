# AmiWind v0.0.38-dev1 - Piece By Piece, Cell By Cell

Candidate for the next private playtest. No playtest package has been validated or delivered yet.

## Candidate changes

- Lava source-stage reuse now includes conversion mode and source digests. Stale converter output is preserved before regeneration.
- Lava beds, visible surfaces and liquid contents are checked separately in offline CHIM audits. All 25 affected cells convert and pass format checks; six retain hull-policy holds.
- The opt-in `lava-pools` MiniWind preset builds cell (1,-2) for lava visibility, contact and damage checks. It does not add this test area to default builds.

## Known in this build

- [CHIM-LAVA-HUNK-GAP-38](bugs/CHIM-LAVA-HUNK-GAP-38.md): native lava scene leaves 93,088 bytes less than the 2 MiB hunk-gap safety. Memory review is pending.
- Five original leveled-creature spawn markers in the lava test cell remain unconverted gameplay content; no resident-contact acceptance is claimed.

- [CHIMPORT-RETRY-LAVA-STALE-SOURCE-36](bugs/CHIMPORT-RETRY-LAVA-STALE-SOURCE-36.md): converter recovery is verified; native lava acceptance and release integration remain pending.
- [CHIM-LAVA-TERRAIN-AUDIT-37](bugs/CHIM-LAVA-TERRAIN-AUDIT-37.md): offline audit repairs passed; six hull holds and matched gameplay checks remain.
- [CHIM-COAST-OBJECTS-MISSING-36](bugs/CHIM-COAST-OBJECTS-MISSING-36.md): coast object coverage remains unresolved.
- [ENGINE-SYNC-IO-MAIN-LOOP-36](bugs/ENGINE-SYNC-IO-MAIN-LOOP-36.md): nonblocking world streaming remains roadmap work.

Green-cell expansion, adaptive cache sizing and measured 68060 performance work are pending. The baseline boot smoke for the preceding converter candidate is not acceptance of this new sandbox.
