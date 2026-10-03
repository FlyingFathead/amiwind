# Project development rules

These requirements apply to changes in the public project.

## Required Linux and Windows compatibility

Owner requirement, 3 October 2026: the converter, build pipeline, configuration
and validation tools must support both Linux and Windows. A correction on one
host must not silently break the other. This is a development requirement, not
a claim that every path has already passed both platforms.

- Specify encodings and line endings explicitly for generated text; use UTF-8
  and LF unless the consuming format explicitly requires otherwise.
- Do not assume shell syntax, path separators, case sensitivity or executable
  names are identical. Use portable path/process APIs and documented host tools.
- Hash and size receipts must describe the exact bytes actually packaged.
  Validate legacy source bytes before conversion; never rewrite a receipt merely
  to conceal a mismatch. Any accepted normalization must have a narrowly defined
  format rule and reject substantive content changes.
- Cover cross-host inputs, including LF and CRLF, with focused regression checks.
  Record Linux and Windows verification separately; one host passing does not
  establish the other host's result.

## Mandatory bug and incident documentation

Owner requirement, reaffirmed 3 October 2026: ALWAYS record every bug, issue,
regression and failed build/validation incident in public docs/BUG_JOURNAL.md
and the relevant subsystem documentation, with supporting private production
notes. Record it when discovered; do not wait for a fix or an owner reminder.

- State the affected/first-observed version, location, environment, symptoms and
  reproduction steps. Identify the introducing version/change only when proven.
- Record the established cause, or explicitly mark it unknown/under investigation.
- Record the proposed solution while work is pending; later record the actual
  correction, repair-candidate version, checks, remaining limits and verified
  fixed version. Passing host checks alone do not establish target acceptance.
- A mitigation is a bandage, NOT a fix. Keep those statuses distinct.
- Update the incident and related current-state/release documentation as evidence
  changes. Preserve history; do not let bug reports or fixes become stale.
- Keep proprietary assets and private host paths/receipts out of public docs.

This documentation is a required completion/review gate for every agent.

### Required incident record

Every incident entry must state:

1. What bugged out: symptoms, failure and impact.
2. In what version: affected/first-observed version; introducing change only if
   established; repair candidate and verified fixed version tracked separately.
3. Where, how and when: map/subsystem, host/target, circumstances, reproduction
   steps and discovery/test timestamp. Unknown details stay explicitly unknown.
4. What solution was proposed, and why.
5. What we tried: approaches, relevant failures and evidence.
6. What worked: actual result, validation performed and remaining limitations.
7. Whether the result is a mitigation, a repair candidate or a verified fix.
   **Mitigation is NOT a fix.** Do not close an incident with a bandage.

These records include incidents encountered while developing, converting,
compiling, validating and packaging AmiWind, as well as gameplay bugs. Update
public docs/BUG_JOURNAL.md and subsystem docs alongside private production notes.

### Imperative: keep bug, issue and regression tracking updated at all times

**BUG, ISSUE AND REGRESSION TRACKING MUST BE KEPT UPDATED AT ALL TIMES.**
This includes development, conversion, compilation, validation, packaging and
gameplay failures. Record every such incident when it
is discovered and update its entry whenever new evidence, an attempted
solution, a failure, a mitigation, a correction or a validation result changes
what is known. Do this in the same work, without waiting for an owner reminder.
Keep public bug/subsystem documentation and private production notes consistent.
Preserve dated history and mark unknown/pending facts honestly. Never leave a
resolved issue stale as pending, or a pending/unverified issue described as fixed.
**Mitigation is NOT a fix.** Documentation freshness is a mandatory completion
and handoff gate for every agent.

### Incident classification

| Type | Definition | Evidence to record |
| --- | --- | --- |
| Bug | Confirmed incorrect behavior or invalid data. | Expected versus actual result and reproduction or validation evidence. |
| Issue | A problem, limitation, risk or unresolved concern requiring work. | Observation, impact, uncertainty and investigation plan. |
| Regression | A previously working behavior broken by a subsequent change. | Last known-good and first known-bad versions, comparable conditions and the causal change when established. |

An incident may have several labels: a regression is normally also a bug or
issue. Use a primary category and additional labels without duplicating the
report. Newly discovering an old defect does not establish a regression. Mark
suspected regressions as suspected until version/comparison evidence confirms
that previously working behavior was lost. Track severity and lifecycle status
separately from type; proposed repair, mitigation, host-validated candidate and
target-verified fix are distinct statuses.

## Keep owner playtest material private

Owner playtest packages, playable HDFs, screenshots, recordings and private
playtest receipts stay outside the public repository, source archives, CI
artifacts and public issue attachments. Public documentation may summarize
verified findings in text, but must not embed or link private captures, packages,
machine paths or receipts. Only separately approved and rights-cleared media may
become public.

## Mandatory handoff validation: Linux Docker plus separate Windows checks

Every production handoff requires the full Linux test suite and asset-free Amiga
compile gate inside the authorized project Docker environment. Preserve commands,
environment, logs, exit status, skips and failures. Focused tests are not a
replacement. Record native Windows checks separately; Docker-on-Windows is Linux
container evidence, not native Windows validation. Do not create or run native
Windows helper executables for this gate. Clean up only Docker/WSL resources
started for validation and verify the prior state is restored. The owner performs
publication on Linux. Failed gates remain open; distinguish fixture failures,
unknown failures and product defects until evidence resolves them.
