# Horstator’s musings (25 Oct 2026): “[C]raft, [H]andles, [I]ntent and [M]eaning”

_Last updated with AmiWind v0.0.51 (25 October 2026)._

v0.0.51 is out the door, or about to be: *Let There Be More Inner Light*. Akulakhan's Chamber is no longer a black
hole, and the interiors finally get the light the original gives them. Along the way it made me think about why we
do this at all, and how.

## Why

AmiWind is free. It is open source under the GPL, publicly available, and anyone can build on it. We're not selling
anything: no hidden fees, no catches, no gotchas. You bring your own copy of Morrowind and your own Kickstart ROM,
and the builder turns them into something you can play on an Amiga. If it lightens up someone's day to see
Vvardenfell on a machine from 1992, that's the whole point.

That's also how the Amiga scene began, and we want to stay true to it. The Amiga grew up on sharing: disks swapped by mail,
BBSes and diskmags, Aminet, demo groups releasing their productions for free, and coders who put their source out
there so the next person could learn from it and do better. People made
things for the love of the machine and the joy of showing what it could do, not for profit. AmiWind belongs to that
tradition: made for the love of it, given away, and open for the next person to take further.

And there is passion and artistry in engineering something like this.

## The artisan and the engineer

The difference between an artisan and an engineer is often so visible, and not only in Morrowind. An artisan can
spend a whole lot of human hours on a 700 to 800 triangle door handle that nobody ever really looks at, and it tanks
the performance. Someone purely engineer-minded looks at that and says: throw it away, that's 700 excess vertices.

What we're doing is a third thing. We ask: can we pull this off with 32, maybe 40, and still have it look good?

That isn't throwing the artist's work away, and it isn't keeping all 700 triangles because someone made them. It's
asking what the artist *meant* with that handle, and what the smallest honest form of that meaning is. The original
artists put love into that handle. Discarding it would throw their work away; keeping it whole would make the game
unplayable on the machine we love. Finding the forty triangles that still read as *their* handle is how we honour
them within the limits we chose.

That's the old demoscene spirit, and it was born on this very machine: understand exactly what the eye needs, and
spend every cycle on that.

## What it looks like in practice

- **Compare against the original first, then cut.** A room is judged against what the original shows at the same
  place, not against "good enough".
- **Find the missing input before you turn a knob.** This release's lesson: our interiors were dim for weeks, and we
  kept tuning a brightness setting, when the rooms were simply missing the light the game data gives them from above
  ([interior lighting](INTERIOR_LIGHTING.md#what-this-taught-us-every-light-input-first-then-any-brightness-knob)).
  And there's more of it: the colour of that light, the fog in the Dwemer ruins, the red of a blight storm on the land.
- **Cut where the eye doesn't see the cut.** Reduced meshes are checked for seams before they ship.
- **Keep the record.** Every finding goes into the [bug register](BUGS.md) the day it's found, with its numbers and how
  they were measured. That's what lets us find a cause instead of chasing our own tail, and next it will tell us at
  once when an old, closed bug comes back.

## Next

v0.0.52 starts with the bug register itself, then the rest of the light: colours, interior fog and the weather
outdoors. And somewhere along the way, people in Ald'ruhn will raise an arm against the blight winds.
