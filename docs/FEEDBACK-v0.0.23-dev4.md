# v0.0.23-dev4 tester feedback

Recorded 29 September 2026; follow-up checkpoint v0.0.23-dev5.

| Report | Follow-up |
| --- | --- |
| Speech split awkwardly across boxes | Shared sentence-aware pagination; oversized sentences word-wrap; duration distributed by page length |
| Two-line text too high in the panel | Center using painted glyph bounds, including the follow-guard instruction |
| NPC names overlay the world | Default name above Talk: E below viewport; suppress intro target names |
| F10 full console lost | Half/full/closed cycle restored; Escape closes; F1 identifies F10 |
| Bare debug/dbg should show help | Retained aliases verified and tested |
| Exterior stalls at -37 792 75 / 265 / -4 | House-group isolation, visibility caching and first window flattening pass |
| Projecting windows waste geometry | Reusable non-destructive per-type configuration; Nord windows first |
| Intro exterior too expensive | Separate intro_docks_variant 2, full scene retained as variant 1; full route acceptance still open |
| TTF parchment looks degraded; uppercase H concern | Fresh Magic Cards paper conversion matches shipped data; appearance diagnosis remains open |
| Darvame destinations unavailable through E | Travel service remains open; no available destination or gold-charge claim |

See [mesh findings](MESH_TIPS_AND_TRICKS.md) for Problem, Investigation and
Solution, exact camera coordinates, rejected assumptions and measured limits.
