# CHIM cell result format (aw-cell-result-1)

A cell result file is how a conversion run (CHIMport, or any tool that converts cells) tells the [CHIM Progress Tracker](PROGRESS_TRACKER.md) what happened to each exterior cell: whether it converted, what each audit found, what went wrong and the figures that were measured. The tracker stores the file and folds it into `cell-progress.json`; the conversion run never edits that file itself.

```bash
python3 tools/cell_progress.py result --out DIR --file RESULT.json
```

The command validates the file, keeps a copy under `DIR/results/`, and ingests again. Sending a cell again replaces the fields it carries; later files win.

## File

```json
{
  "format": "aw-cell-result-1",
  "build": "run-001",
  "generated": "2026-10-09T05:40:00+03:00",
  "provenance": {"source_commit": "abc1234", "chim_version": "0.1.0", "world_format": "0.5", "built_at": "2026-10-09T05:30:00+03:00"},
  "cells": {
    "-3,-2": {
      "converted": true,
      "status": "passed",
      "errors": [],
      "audits": {
        "seam_tears": {"status": "passed", "detail": "0 tears in 531 meshes", "numbers": {"meshes": 531}},
        "stair_walk": {"status": "failed", "detail": "2 flights"}
      },
      "stats": {
        "records": {"refs_total": 420, "by_type": {"STAT": 261, "DOOR": 41}},
        "records_by_type": {"STAT": {"placed": 5, "converted": 4, "deferred": {"reason": 1}, "failed": 0, "skipped": {}}},
        "meshes": {"unique": 84, "new": 80, "reused": 4},
        "faces": {"before": 32266, "after": 195147, "chim_terrain": 5196, "chim_placed": 189951}
      }
    }
  }
}
```

## Top level

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `format` | string | yes | Always `aw-cell-result-1` |
| `build` | string | yes | The name of the run or build; becomes each cell's provenance build |
| `generated` | ISO 8601 string | no | When the file was written (host clock); the tracker stamps it when absent |
| `provenance` | object | no | `source_commit`, `chim_version`, `world_format`, `built_at`, and free extra keys such as `builder` or `run` |
| `cells` | object | yes | Cell ID `"x,y"` (integers, negative allowed) to a cell record |

## Cell record

Every field is optional; a field that is absent is left as it was.

| Field | Type | Meaning |
| --- | --- | --- |
| `converted` | boolean | `true`: counts as converted. `false`: tried and not converted |
| `status` | string | The run's own verdict: `passed`, `failed`, `not_converted`, `hull_pending` (alias `policy_pending`) or `empty` |
| `empty` | boolean | The cell holds only terrain and water; nothing was placed. Shown as empty sea, never counted as passed |
| `policy_pending` | boolean | The only open problem is hull-chain depth, waiting for one shared rule. Neither passed nor failed |
| `errors` | array | Replaces the cell's error list; `[]` clears it. Each entry is a string or `{"stage", "mechanism", "message"}` |
| `audits` | object | Audit id to an audit result (below) |
| `stats` | object | Measured figures (below). Absent keys are "not measured" |
| `provenance` | object | Per-cell overrides of the file's provenance |

`status: not_converted` means the cell could not be built (for example an object placed across a cell edge) and is a failure-type state; it is never counted as done. A cell is successful only when it is converted **and** every audit that was measured passed. Never send `passed` for something that was not measured: leave the audit out.

## Audit result

The audit ids are `format_validation`, `stair_walk`, `memory_fit`, `seam_tears`, `hull_bevels`, `sky_bank_texels`, `hidden_faces`, `far_terrain`, `sprite_shape`, `actor_grounding` and `door_links`. Their pass rules are in the import policy of the generated [CHIM cell tracker](CELL_TRACKER.md#import-policy).

| Field | Type | Meaning |
| --- | --- | --- |
| `status` | string | `passed`, `failed`, `accepted` (failed, and the owner accepted it) or `not_measured` |
| `detail` | string | One line saying what was found |
| `numbers` | object | Free numeric figures behind the result |
| `build` | string | The build the audit ran on; defaults to the file's `build`. A result measured on another build than the cell's current one is shown as stale and counts as not measured |
| `outcome` | string | Optional refinement of the status. Reserved value `kept_as_chain`: the meshes were deliberately left as collision chains to save memory; the audit passes. The name may change before it is used by a release |

## Stats

All keys are optional and numeric unless noted. The tracker sums the listed figures per island and ring and shows any other numeric figure under "Other measured numbers" and in the CSV export as `stats.<path>`.

- `records`: `refs_total`, `by_type` (record type to count).
- `records_by_type`: per record type (`STAT`, `DOOR`, `LIGH`, `NPC_` ...): `placed`, `converted`, `failed`, `deferred` (reason to count) and `skipped` (reason to count). This drives the per-object-type tables and the two completion levels: a cell is only complete when nothing is deferred, skipped or failed (actors may be deferred for terrain complete).
- `meshes`: `unique`, `new`, `reused`. When you do not send `new` and `reused`, the tracker derives them from the original references in conversion order; what you send wins.
- `faces`: `before`, `after`, `chim_terrain`, `chim_placed`, `chim_stored`.
- `textures`: `count`, `bytes`. `bytes`: `chim`, `legacy`. `chunks`: `count`, `bytes`, `legacy_maps`, `legacy_bytes`.
- `hull` or `collision`: `clipnodes`, `nodes`, `max_depth` / `max_hull_depth`.
- `memory`: ring peaks, `heap_status`, `zone_bytes`, `budget_bytes`, `least_headroom_bytes`, `largest_block`.
- `vis`: `entities_sent`, `faces_clipped`, `bsp_nodes_per_face`. `time`: `convert_s`, `cpu_s`.

Use bytes for sizes and seconds for times.

## Rules

- Cells outside the land and content universe of the game data are listed under `result_ignored` in the tracker data, never silently dropped.
- Interiors are not in result files yet.
- The tracker never writes the owner's fields (`release`, playtested, approved); a result file cannot set them.

## Versioning

The format name carries the version. Adding an optional field, an audit id or a stat key does not change it: readers ignore keys they do not know. A change that alters what an existing field means, or removes one, becomes `aw-cell-result-2`, and the tracker refuses a file whose format it does not know with a clear message. `tests/test_cell_progress.py` checks the validation and every field above on synthetic data.
