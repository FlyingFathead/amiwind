# Horstator’s musings (7 Oct 2026): “Well, It Looks Like You Should Always Check and Recheck—”

—and then check again, and then, just to be thorough, look at the thing you
were sure you had already looked at.

Four days ago I wrote that fog might actually hinder you: in central Balmora a
*longer* view distance seemed to run better, and I mused about clipping costs
at the cutoff and cache churn. Tonight the fog turned around and told on the
real culprit. Dropping the fog distance to 250 in Balmora roughly doubled the
frame rate. Fog doesn't make anything cheaper by itself; it only helps when
it's the one thing actually throwing work away. Which raised the obvious
question: why was the fog the *only* thing throwing work away?

## The question I kept asking

For weeks I've been asking some version of the same thing. Are we using vis?
Are we culling properly? Is there polycount in here we're paying for and never
see? And for weeks the answer came back as some flavour of "that's about as
good as it gets on this hardware." A 68040 is a 68040. Balmora is a big town.
Deal with it.

I never quite bought it. Quake ran on machines like this. Quake has an entire
offline tool, `vis`, whose one job is to work out ahead of time what can be
seen from where, so the engine never even considers the rest. A town of
houses is close to the best case for it: walls everywhere, every house hiding
the houses behind it.

## It was not the fog after all...

...so we finally looked at the data instead of the frame rate.

Not "does it feel faster", not "what does the profiler say about this one
function": the actual visibility data inside each map, the list Quake keeps
of what every spot can possibly see. And there it was.

Every building we convert from Morrowind becomes its own little brush model, a
`func_wall`. It renders, it collides, it keeps its identity for doors and
lighting. And Quake's `vis` ignores it completely, because only the world's own
structural walls count. In a Balmora map the world is basically the terrain.
Ninety-four percent of the faces live in buildings that, as far as `vis` is
concerned, do not exist.

- Balmora: 84-89 % of the map counts as visible from an average spot.
- Seyda Neen: 59-76 %.
- The open world with its rocks and trees: 69-85 %.
- Interiors: **100 %.** Every interior is one empty box with all its rooms
  floating inside as `func_wall`s. Stand in a corner of the Mages Guild and the
  engine still walks through all 40,488 faces of the building, every frame.

And the NPCs. Quake draws characters with a depth buffer, not the clever edge
sorting it uses for walls, so a guard standing behind a house costs his full
drawing work even though you'll never see him. The only thing that could skip
him is the visibility data, and the visibility data was looking straight
through the house.

## The fix is embarrassingly Quake

Nothing new in the engine. Put an invisible solid block inside each building,
textured with `skip` so it's never drawn, as part of the world. Now `vis` sees
a wall there and stops looking. Do the same inside the thick walls and floors
between interior rooms, and inside the big rocks out in the wilds. The pretty
building stays exactly as it was; its invisible twin does the hiding.

We'll measure it the boring way, which is the point: visibility share before
and after, then the same view in game with the frame counter on.

## What I'm taking away from this

When something is slow and everyone, including you, has a story about why
it's slow, the story is not the measurement. Read the data the engine actually
uses. Count what you're asking it to draw. And when your gut keeps whispering
"there's *got* to be some culling we're missing", maybe go check, and recheck,
and then check the thing you were sure you'd already checked.

It's now a mandatory rule in [DEVELOPMENT.md](DEVELOPMENT.md); the numbers are
in [Town visibility](performance/TOWN-VISIBILITY.md) and
[TOWN-VIS-OCCLUSION-31](bugs/TOWN-VIS-OCCLUSION-31.md). And the fog? Still
useful. Just no longer doing the whole job alone.

— Horstator

## P.S. (8 October): check, recheck — and then count it the way the engine does

The first invisible-twin prototype came back the next night. The map dutifully
split into more pieces, and the visibility share dropped... and 589 of 590
buildings were still on the engine's to-draw list from every spot we tested.
Quake keeps or drops a separate model as a whole, and anything spread over
more than 16 of those pieces is simply treated as visible from everywhere.
So the buildings themselves have to become part of the world, where Quake
culls face by face, with the invisible twins doing the hiding. Which is, once
again, exactly what Quake has always done. Check, recheck, and count the thing
the engine actually counts.
