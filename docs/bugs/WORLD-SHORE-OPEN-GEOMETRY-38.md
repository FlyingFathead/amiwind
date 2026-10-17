# WORLD-SHORE-OPEN-GEOMETRY-38: Shoreline objects show large open sections and thin disconnected edges

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 12 October 2026, in v0.0.38-dev2 |
| Where | Shoreline cells 6,16 and 6,15; exact HUD poses in report |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.38-dev2 (last seen) |
| Severity | high: Maintainer-visible world or movement defect requiring location-specific reproduction. |
| Family | Object placement and in-game geometry (`placement-geometry`) |
| Playtest version | v0.0.38-dev2 (visible screenshot label) |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM unknown, engine unknown, world format unknown |
| Unknown because | Version visible; exact installed binary and map hashes not supplied. |
| Platform or emulator | unknown (Emulator not identified.) |

<!-- END GENERATED FACTS -->

## Symptom
Maintainer reports broken shoreline objects and missing textures. Two screenshots show broad open-looking sections, thin edges and background visible through the objects. Texture loss versus omitted faces, orientation or visibility is not yet isolated.

## Where
Cell 6,16: global 55749,131690,154, heading 64, pitch -5. Cell 6,15: global 56812,129390,697, heading 163, pitch -13. Both are dev2 maintainer screenshots.

An additional dev2 screenshot supplied on 12 October 2026 shows similar open
sections at cell 6,15: global 56635,125560,1862, heading 226, pitch -4.
The cause is not established by the additional view.

## How it happened
Unknown. Maintainer evidence is preserved; no independent reproduction or cause yet.

## Why it was not caught
No matched native acceptance receipt covers these exact poses. Build-time checks
and other converted cells do not establish correctness at this location.

## Reproduction
Identify original placed reference and model IDs at both poses. Capture matched OpenMW and native views, audit face winding, texture lookup, model bounds and visibility, then test collision separately. Read the existing AmiQuake surface and model drawing paths before designing a repair.

The maintainer reports repeated shapes and longstanding gaps since rocks were
separated from the topomap. A 153-model diagnostic found original material-rim
vertex loss in 129 production reductions; boundary locking retained every
measured rim vertex. This is a lead, not proof of an open seam or a repaired
view. Original openings, source transforms and the exact visible model still
need comparison. See [the rock investigation](../WHAT_ARE_ROCKS.md#v0038-investigation-repeated-shoreline-rock-gaps).

## Repair
Pending diagnosis. Preserve the reported scene and distinguish a proposed
repair from verified package behavior and maintainer acceptance.

## Verification
Maintainer-reported in v0.0.38-dev2 on 12 October 2026. No repaired package,
matched comparison or acceptance. Screenshot coordinates are copied from HUD.

On 12 October, an original OpenMW reference near global 46864,132139,155
(cell 5,16, heading 129, noon) showed continuous rock faces. The maintainer identified
the difference as further evidence of stitching problems. This supports the
conversion investigation, but the camera is not yet matched: measured eye height
was about 228.6 and the base pitch readback was zero despite requested extra tilt.
It does not establish the precise cause or a repaired result.

The dev2 terrain and partition manifests route all 17 additional reported poses
across cells 3,15; 4,16; 5,16; 6,15; 6,16; 7,15 and 7,16 to legacy BSP maps.
These receipts identify the intended build path; they do not identify the exact
bytes installed by the maintainer or the specific visible rock reference.

## Prevention
Additional maintainer evidence on 12 October in v0.0.38-dev2: thin bright openings
cross several dark rock silhouettes at global 4222,148957,1765, local
31,-648,57, cell 0,18, heading 309, pitch -20, time 08:41. This extends the
reproduction set; it does not identify the mesh or establish that the sampled
boundary-reduction mismatch is the cause of each visible opening. Preserve the
original image and obtain the matched original view and source reference IDs.

Add the confirmed reproduction to cell-level native and source-reference
coverage. Keep missing assets, collision and visibility findings separate.


## Maintainer evidence reconciliation, 13 October 2026

The following maintainer screenshot evidence was visually reviewed. Original images
remain in the private evidence archive; identifiers bind this report to those
originals. This records reported symptoms and comparison controls, not a repair
or runtime acceptance. Missing build or pose information remains unknown.

- `OWNER-20261012-171124`: SHA-256 `51418e4623116e8a04e437071bdf4176f4a328ce6ea6a5acf364de821ebd45c3`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-171206`: SHA-256 `495b5902b899057b84aaf7c1c7f5ee4f7c56e26e1ab729f4c7fe8275b4e58b98`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-171450`: SHA-256 `3ca6a21bb9ca3d35b7b228bb312d946de8fcda2d6f41a4842817e4fca315cda8`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-172147`: SHA-256 `e2cef2f462e1cd276a01675b9a18aae310043247cfe72d8b5b26302702d9d9b8`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-172443`: SHA-256 `53fc48619c1733445d27abc180bf04c51a82d2895a746afbbaf033e7da355ac1`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-172533`: SHA-256 `272c64b20754ee12ab2320a443be951e8d3a59a8e47b4f63a3ff8ab22759dd83`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-172606`: SHA-256 `59b18984e217c8b72300ceded822155ece6bf151df67f2179e8058e3e23ad2c3`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-172630`: SHA-256 `ffa716b1f550311455fad81601356b443484cbf90e108a603046765b0787fbd8`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-172723`: SHA-256 `284fbadd60d2fe567ac07089eeb089a7e96c68d566f8d69b8245342bb0e79518`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-172801`: SHA-256 `17696a82bc0ceb5e9111ae48e691cc8b524521c1319a50f05cc6073767c943d1`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-172929`: SHA-256 `b6d3eb64cc246dae63376462dc771c54e2be97b299c0956a16f45edd9005abb0`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-172949`: SHA-256 `52e06d9f6dea7de41537d90db0ee478f6fdb612484d0d61c74d6b3dd15087696`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-173013`: SHA-256 `31855b85c3444d0d96b1fc6c9e355823a74f3da9579d812ebe5fa69db1204ce5`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-173045`: SHA-256 `0ae573b9b3a9705bfa49e37adea10a6ab12fbbdf2fe3cdae200e52c3d035a7b5`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-173403`: SHA-256 `263fddfe8dc1f3f08f8d9f61e1ebd8cea1ce1c3b6b84df4fbdaecd2f44fefd81`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-173452`: SHA-256 `ab797f65dabfb50cb5aaa3d8f003bbe4b5984c080c1e0bd979232fee8852cf9d`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-173506`: SHA-256 `cd493a299ad87638b8cea0a0848e298bb0001682963aae43a7ab9497332ba0df`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-173518`: SHA-256 `f7e70c3aa32b17b3df5557784109f96960e3410e7143e7f1e265837c2267e484`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-173658`: SHA-256 `99a47bcd57b3b08dfd4c90c4c2ad657949a01902d738b4dd3d4f409ecd3ac07b`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-173739`: SHA-256 `636f29bb8f21a5d2112b8bf1cd85552c0ba0787b190fb4cab74338ae7ea4b231`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-173814`: SHA-256 `39b120edacfaa182a933f3621c93bfbba66c363504aa9a3f63e6544b5d62eebe`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-180435`: SHA-256 `4e202003d2e35002397cfe1cb8cb9025d70204bc1e130934a047c1fb3648fcfa`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-180628`: SHA-256 `dc9764e7668ad18483cb6eeab535470f7b0c822c977298505528ec60cb6c818e`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-181153`: SHA-256 `5a74e1549bc192cbf1055a03f77e0af103bfbb6d3ea0a67a0345a6c774d305d2`. Screenshot association checked; no repair or behavioral acceptance inferred.
- `OWNER-20261012-183402`: SHA-256 `3095dfb3b73f234d27937f93eb1bac92acd63d1031ec35cc291f1f5945299b33`. Screenshot association checked; no repair or behavioral acceptance inferred.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Object placement and in-game geometry (`placement-geometry`). Placed objects match the original (OpenMW A/B at the same pose). See [families](README.md#families).

- AW-20260928-03 (no report page): Silt Strider landing geometry
- AW-20260928-04 (no report page): Invisible barriers across plank
- AW-20260928-06 (no report page): Player can leave pier and become stranded
- AW-20260928-11 (no report page): Census missing floor and wall / falling into void
- AW-20260928-20 (no report page): Census clipped outside room near captain wing
- [CENSUS-ENTITIES-30](CENSUS-ENTITIES-30.md): Census Office objects misplaced (upright rug, ceiling hole, tapestry)
- [CHIM-TERRAIN-ROCK-EXEMPT-38](CHIM-TERRAIN-ROCK-EXEMPT-38.md): Terrain-named placed rocks bypass experimental buried-surface clipping
- [CONVERTER-ROOT-ROTATION-30](CONVERTER-ROOT-ROTATION-30.md): Converter applied NIF root-node rotation to placed meshes
- ROCK-FLORA-SURFACE-29 (no report page): Angular rock-like surfaces newly appearing in Bitter Coast
- SHACK-VISIBILITY-29 (no report page): Indrele Rathryon shack front walls missing

<!-- END GENERATED CATEGORY -->
