# How AmiWind reduces a model, and how to check it

_Last updated with AmiWind v0.0.62-dev1 (7 November 2026)._

The original game's characters and creatures carry far more triangles than an Amiga can draw at speed, so the
builder reduces every actor model it bakes. A reduction is only correct when the reduced model still has every
part, every limb keeps its thickness and every seam between parts stays closed. This page describes how the
builder does it and how anyone can check a reduced model against its original. The method is tracked as
MESH-REDUCTION-SEAMS-62 in the [bug register](bugs/README.md); the bake details are in
[NPC_MODEL_CACHE.md](NPC_MODEL_CACHE.md), and how a modular NPC's parts meet at its joints in
[MODULAR_NPCS.md](MODULAR_NPCS.md#joint-seams).

## 1. Measure the original first

Before anything is reduced, the original model is measured in 3D, at the pose the bake uses:

- **Parts.** A character is built from separate body parts (head, hair or helmet, neck, chest, hands, wrists,
  forearms, upper arms, feet, ankles, knees, upper legs, clothing and armour that replace some of them). A creature
  is several shapes, often plates that meet at rims. Each part's bounding box (width x depth x height) and surface
  area are recorded.
- **Limb thickness along the length.** For every limb part, the cross-section is measured across its two narrow
  axes, at points along the limb (25 %, 50 % and 75 % of its length), with the least and the mean.
- **Open edges.** An edge used by exactly one triangle is open. Positions that coincide are welded first, within
  each part and across parts, so a seam where two parts meet counts as closed. Some originals have legitimate open
  edges (a mouth, the hem of a robe over skin); they are counted, and only openings the original does not have
  are faults.
- **The join map.** Which part meets which part, where (the seam's centre and the ring of shared points) and how
  long the seam is.

## 2. Budgets

Every actor model has a face budget: the triangles it may draw, set by its class (an NPC's whole-model bake, a
resident's ladder of smaller budgets, a creature's budget). A model gets more faces than its class gives it only
through an entry in `config/model-face-overrides.json`, which names the model, the faces it may add, the reason,
the measured cost as before / added / total, and whether it has been checked on the Raspberry Pi 4B. The builder
reads no other route to more faces, and a test keeps it that way.

A body whose locked seams fit inside its total only when its head gives up more faces than the default floor of
120 is listed in `config/model-head-floors.json` with its own floor (90 or 60), keyed by its body appearance (the
head and hair part ids, so every character sharing that head and hair gets it), the faces before and after (never
more) and the measured result. An entry is accepted only from a bake measured with no uncovered opening and every
limb at 0.5 or more, and the bake's stop still judges every bake that reads it; the receipt names the floor used.
The default floor is not lowered for everyone.

## 3. The reduction

- **Weld and lock the seams.** The points that two parts share at a seam are found once for the whole model, and
  locked on both sides, so both reductions keep the same seam and it cannot drift apart.
- **Floors per part.** Each part keeps at least the faces it needs to hold its shape: the fewest at which its
  cross-section stays at 80 % of the original and no surface is lost. Hands, wrists, forearms and the neck are
  limbs, never four-face details.
- **Who gives up faces.** Inside the model's total, the hair or helmet gives faces first, then the head (never
  below its floor), so the body and limbs keep theirs. A model that still does not fit needs an override entry.
- **Head and hair rims stay put.** The head and the hair or helmet are reduced with their rims locked, and the
  rims stay locked through the steps that keep the head under the hair and the hair outside the head. Before
  this, those steps slid the rims away: the edge round the patch of head the hair hides moved inward and a
  hair's edge slid over the scalp, which opened edges the reduction had kept and that no number of extra faces
  closed (`AMIWIND_NPC_HEAD_RIMS=pushed` is the step before, for comparison). The head faces the hair hides are
  left out, except those touching another part (the nape against the neck): removing those opened an edge at a
  join. A head or hair that still opens an edge is baked again kept whole, and that bake is used when the model
  then passes inside its total.
- **Armour as one piece per slot.** The worn pieces of one limb slot (a pauldron's parts, a greave's parts, a
  bracer's parts) are merged into one shape before reducing, each face keeping its own material, so the slot is
  reduced as one piece with one width floor. Before, a heavily armoured outfit (69 separate pieces on a Hlaalu
  guard) left most pieces at four faces, and its bracers kept a few hundredths of their width.
  `AMIWIND_NPC_WORN_MERGE=pieces` is the step before. Every piece of a limb slot of 24 or more faces is judged on
  its own width (`AMIWIND_NPC_WORN_WIDTHS=each`; `slot` judges the slot as a whole, the step before).
- **Seams that do not fit.** When the locked seams of a dressed character do not fit its total, the locks of one
  piece at a time are let go, clothing and armour first, up to six pieces, before the whole model falls back to
  the free reducer; the receipt names the pieces.
- **Open panels.** A part that is an open panel (a creature's plate) is reduced with its rim kept, so it cannot
  fold away.

## 4. The proof, by numbers

A reduced model passes only when, measured against its original:

- it has **no new open edge** (an opening the original does not have);
- **no limb is under 0.5 of its original width** at its narrowest;
- **every join is kept**: each seam of the join map still meets its partner at the same place.

The bake writes these numbers into each actor's receipt, with the faces before and after: the new openings (for a
character, split into covered and uncovered: an opening counts as covered only on a head patch the bake removed
because the hair or helmet hides it, away from every join), the join map (every seam: the two parts, the seam's
length, how much of it stayed open and the widest opening) and each limb's thickness at 25 %, 50 % and 75 % of its
length. Pictures are for people to look at; the verdict is the numbers.

**The bake stop, a ratchet.** A character fails the seam check with any uncovered new opening or a limb under 0.5
of its width; a creature with any new opening. A creature's thickness is recorded but not judged: its parts are
plates, claws and chains rather than limbs, and a per-part profile reads near zero on parts that are whole.

- `config/mesh-seam-baseline.json` lists today's known failures, per model, with their counts, a date and a reason.
  It is written by `tools/mesh_seam_baseline.py write` from a sweep or from a build's own library records, never by
  hand, and that tool refuses a new failing model or a worse line: the list can only shrink.
- The bake fails when a model that is not in the baseline fails, or when a baselined model gets worse (more
  uncovered openings, or a thinner limb). A baselined model that is no worse prints its numbers and goes on. A
  model with an entry in `config/model-face-overrides.json` prints its numbers and goes on.
- A baselined model that starts passing is printed as leaving the baseline; the next `write` drops it, so it can
  never fail again unnoticed.
- Each library prints its totals: passing, baselined, by an override entry, new, worse. Every stopped model is
  listed before the stage fails; a stopped model is never quietly left out.
- **The first run.** The baseline is recorded by a full build, not a separate sweep: a full build runs once with
  `AMIWIND_MESH_SEAM_STOP=warn`, then
  `python3 tools/mesh_seam_baseline.py write --sweep <that build's NPC library manifest> --sweep <its creature
  library records> --first --reason "..."` writes the file, which is committed. From then on every build runs the
  ratchet. Until that run, the file lists only the models measured by hand (a sample of every race and sex, the
  opening's actors and every creature), and a ratchet build stops on any other model that fails.
- `AMIWIND_MESH_SEAM_STOP=ratchet` is the default; `fail` stops every failing model, baselined or not; `warn`
  prints only (a build in `warn` mode is the whole-game sweep the baseline is written from).

## 5. Running the seam check

In the project's shell container, from a checkout:

    python3 tools/mesh_seam_check.py check --mesh r/duskyalit.nif --model <baked model .mdl> --data-files <game data> --png out.png --json out.json

It prints the open edges of the original and of the reduced model, every new opening with its part and position,
the join map, the thickness of every part at 25 / 50 / 75 % of its length, and PASS or FAIL. With `--png` it draws
the reduced model from the front, the side and three-quarter view with each new opening marked in red. Reading the
counts: "source open" are the original's own open edges, "reduced open" the reduced model's, and "new" the ones the
reduction made; only "new" fails a model there. The thickness table is for reading: a character's limbs are
judged in the bake by their least width over the whole limb (under 0.5 stops the bake), and the 25 / 50 / 75 %
stations show where along the limb it thinned.

## 6. The Toolkit page

`amiwind-toolkit/seam-check.html` (the [Toolkit](AMIWIND_TOOLKIT.md#seam-check)) shows a receipt: the verdict, the
uncovered and covered openings with their positions, the thickness table with every station under 0.5 in red, and
the join map with the open seams first. Open the `--json` file of the seam check, or an actor's bake receipt, with
the button on the page; served by `tools/toolkit_serve.py`, `seam-check.html?receipt=<path>` opens one directly.

Status on 7 November 2026: the checks run in the bake on the development branch; the measurements of the first
models (Jiub, the prison ship guards, Nels Llendo, the Alit) are in the [NPC model page](NPC_MODEL_CACHE.md), and
the sweep over every actor model is in progress.
