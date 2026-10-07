# Bug tracking

One system, three parts. A test (`tests/test_bug_tracker.py`) checks that they
agree; a mismatch fails the build.

| Part | File | Holds |
| --- | --- | --- |
| Register | [`bugs.json`](bugs.json) (schema: [`bugs.schema.json`](bugs.schema.json)), shown as [`docs/BUGS.md`](../BUGS.md) | Every bug exactly once: ID, title, state (open/fixed/closed), fixed in, owner accepted, current status, report link, and optional tags (`performance`: listed together below the table; add with `--tag performance`). The only place for current status. Edit the JSON, or use `tools/bug_register.py add` / `set`, then `tools/bug_register.py render`; never edit the table in BUGS.md by hand. |
| Report | `docs/bugs/<ID>.md` | The full record of one bug (template below). Required for every bug found from v0.0.30 on, and for an older bug when it is worked on again. |
| Journal | [`docs/BUG_JOURNAL.md`](../BUG_JOURNAL.md) | Dated, short entries as things happen: reported, cause found, fixed, shipped, accepted. Each entry starts with the bug ID. |

Frozen history (read-only; current status is in the register):
[journal before 7 October 2026](../journals/BUG_JOURNAL-v0.0.29.md),
[earlier register notes](../journals/BUGS-NOTES-v0.0.29.md),
[v0.0.29-rc1 tracker](../BUGS-v0.0.29-RC1.md),
[v0.0.29-rc2 checkpoint](../RC2_ISSUE_CHECKPOINT.md).

## Rules

- **ID:** `AREA-WHAT-NN`, where `NN` is the version series in which it was
  found (`-30` for v0.0.30). Never reuse or rename an ID.
- **New bug:** add it to `bugs.json` (`tools/bug_register.py add ID --title ... --found vX`),
  a journal entry and the report page in the same change, as soon as it is found, even if the cause is unknown.
- **Fixed** (`state: fixed` with `fixed_in`) means a correction shipped in a named version and was verified.
  A candidate, mitigation or source-only change is not fixed. Keep reported,
  source-checked, packaged, native-verified and owner-accepted distinct, and
  set `owner_accepted` only when the owner has played the fixed build.
- **Regressions** get their own ID, linked to the older bug they resemble.
- Old IDs keep their records; their register row is updated when their status
  changes.

## Report template

```markdown
# <ID>: <short title>

## Status: <date>

<Open / fixed in vX / owner-accepted in vX>. Present in <versions>.

## Symptom

What was seen, where (map, position, version), by whom.

## Where

Files, maps or components affected, and what is known to be unaffected.

## How it happened

The cause, step by step.

## Why it was not caught

Which check was missing or did not cover it.

## Reproduction

Exact steps or data comparison that shows the fault.

## Repair

What changed, and the gates on the result.

## Verification

What was run on which build, and what remains (for example owner playtest).

## Prevention

The check or gate added so it cannot recur unnoticed.
```
