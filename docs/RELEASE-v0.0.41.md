# v0.0.41: Combined CHIM world repair

15 October 2026 — The preceding v0.0.41 source snapshot completed 4,242 tests: 4,236 passed, zero failures/errors, three Windows-only skips and three exact Census expected failures; source was unchanged. This does not validate the subsequent v0.0.41-dev1 version alignment or establish image/native/package acceptance.

15 October 2026: active preparation now targets v0.0.41-dev1. The planned final release title is **v0.0.41: Collisions And Boundaries**. Earlier source snapshots, checks and findings retain their recorded version identities; they do not establish acceptance of this development candidate. Matching source validation, completed image assembly/readback, native checks, packaging and delivery remain separate gates. See the [current development candidate](RELEASE-v0.0.41-dev1.md).

[BUILD-INVENTORY-PALETTE-41](bugs/BUILD-INVENTORY-PALETTE-41.md) — 15 October 2026, v0.0.41 source candidate: image assembly prepares inventory before the sky palette pass, which rejected current AWIC icons and AWI2/AWST metadata as unknown images. The source repair validates each inventory format at its exact path, remaps only icon pixels and preserves metadata bytes. Scoped evidence contains 15 passing palette checks and 2 passing inventory-asset checks on matching unchanged source. Actual image assembly, native verification, packaging and shipment remain pending.

[CHIM-FRAME-STATIC-SEAM-40](bugs/CHIM-FRAME-STATIC-SEAM-40.md) — 15 October 2026, v0.0.41 source candidate: the 941 world stopped at the unchanged ownership guard because ten explicitly deferred Seyda references reappeared through a named-town apron. The candidate applies the existing exact owner dispositions to named and regional neighbours alike. All ten original deferred IDs are verified and 38 focused checks pass. Fresh affected-world conversion and renewed boundary/memory checks remain pending; no coverage, native, package or owner acceptance is promoted.

[CHIM-MODEL-ARENA-RESERVE-41](bugs/CHIM-MODEL-ARENA-RESERVE-41.md) — 15 October 2026: exact allocation and predecessor-world checks remain separately recorded. The later 941 world stopped at its ownership guard because named aprons bypassed ten existing deferred-owner dispositions. The source-only disposition repair passes 38 focused checks; fresh world, boundary/model review and native/package acceptance remain pending.

[CHIM-RECIPE-APRON-SCOPE-41](bugs/CHIM-RECIPE-APRON-SCOPE-41.md) — 15 October 2026, v0.0.41 candidate: recipe repair converted all four affected frames with structural PASS. Three still failed the unchanged memory gate (peaks 6,957,632; 6,939,952; 6,644,768 bytes for (10,0), (10,1), (9,2)); (11,0) passed at 5,875,568 bytes. The separate placed-model reserve repair passes all four on identical world bytes. A complete successor world and recipe/model/sprite equivalence and native checks remain pending.

15 October 2026: exact-source validation completed 4,231 tests: 4,225 passed, three Windows-only skips and three tracked Census expected failures. The 71 focused tests and original-data readback across nine frame positions passed, consistently hiding 33 of 158 original references at stronghold state 6 while preserving unknown scripts. All 243 player resources are reusable after exact producer, input and file verification. Complete combined-world conversion, native comparison, packaging and shipment remain pending; coverage counts are unchanged.

## v0.0.41 candidate - visibility aprons, 15 October 2026

[CHIM-VISIBILITY-APRON-SCOPE-41](bugs/CHIM-VISIBILITY-APRON-SCOPE-41.md) - The combined world stopped at Tel Uvirith, original cell (10, 1), because
its approved fixed stronghold snapshot required a source radius of zero.
Regional frames now audit neighbouring cells for separate aprons. The repair
keeps visibility snapshots bound to each original cell across all frames that
audit it. Unknown scripts and unaudited references remain visible. Runtime
quest progression is still deferred; complete conversion and native/package
acceptance remain pending. Coverage counts are unchanged.


## v0.0.41 candidate - window support, 15 October 2026

[CHIM-WINDOW-TOWER-SUPPORT-41](bugs/CHIM-WINDOW-TOWER-SUPPORT-41.md) - The combined v0.0.41 world build stopped while mounting four Nordic windows
from original cell (7, 22) into the adjacent frame apron. Their supporting
thatched tower was present, but the facade search accepted only model names
containing "house". Exact source triangles support all four windows under the
existing distance and outward-normal checks.

The candidate recognizes the original thatched-tower model in both local and
neighbouring facade searches. It keeps original reference ownership, geometry,
collision, mounting range and clearance. Arbitrary props are still rejected.
The failing build is preserved; complete conversion, native comparison and
fresh package readback remain pending. Coverage counts are not promoted.


15 October 2026, v0.0.41 candidate: 50 focused lava/polygon/terrain checks
and 47 emulator preset/launcher checks pass. Both original failing chunks pass
coverage against the unchanged cached geometry. Full combined-world, exact
source suite, native, package and shipment checks remain pending.

The v0.0.40 combined-world build stopped on two chunks in cell (2, -2).
Readback of the exact cached units found five affected coverage samples:
each has one lava surface and lava contents (-5) at the required depth.
A tiny edge collapses to identical adjacent vertices when the chunk is
translated into float32 frame coordinates. The polygon test mistook this
zero-length edge for a boundary through every sample.

The v0.0.41 candidate skips only exactly identical adjacent XY vertices.
It preserves edge ambiguity, outside rejection and empty/degenerate rejection;
no geometry, collision, pool height, tolerance or engine format is changed.
Full-world validation, native checks, fresh package readback and delivery
remain separate and pending. No coverage count is promoted.

[Canonical issue](bugs/CHIM-LAVA-DUPLICATE-VERTEX-40.md).

CHIM remains 0.2.0. The target retains rings 0, 1 and 2, separate aprons,
original-cell ownership and legacy coverage outside the CHIM selection.
The earlier published source and private release artifacts remain unchanged.
