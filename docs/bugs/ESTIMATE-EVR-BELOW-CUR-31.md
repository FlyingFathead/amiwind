# ESTIMATE-EVR-BELOW-CUR-31: World estimate: "everything" comes out below "current content" in some regions

## Status: 8 October 2026

Open. Found by the Toolkit map metrics layer work.

## Symptom

In 894 exterior regions the "every object placed" estimate is lower than the
"current content" one for faces, heap, brush models and vertexes (texture mappings
in 866, entities in 35). The gaps are small (worst heap 12,475 bytes, brush models
-10, entities -7), but "everything" can never be less.

## Where

The private world estimator (being ported to the builder).

## How it happened

Unknown: probably a different placement filter or duplicate removal between the two scenarios.

## Why it was not caught

No check that one scenario contains the other.

## Reproduction

Compare the evr and cur columns per region in the estimate output.

## Repair

Find the cause while porting the estimator; add a test that "everything" is never below "current content".

## Verification

Pending.

## Prevention

The same test in the suite.
