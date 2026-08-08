
Alright.

So,

running through the system,

the GovCon system.

Every day

we upload

SAM notices

and um

USA Spending

.gov information

uh

into our system.

Uh, for the SAM notices, the criteria is

um

construction and facilities, and IT.

Pretty much.

Uh.

So, instead of using the API, the SAM API,

we can really just do a databank.

And then the objective will be

like get a get all the

Total Small Business stuff

from

Well, see that's the thing. I don't know if I should do Total Small Business or

Full and Open

because if I do Full and Open, that means

um

anybody can bid that's just more to add on my plate. So

I guess

I'll do a test. Maybe that maybe that'll

But okay, that's also the problem, though.

Once I do, hm, okay.

All right, so here's my concern.

Well, with the databank, you cannot filter by NAICS codes. You can just

filter by like designation

and some other stuff.

So I can't like filter by

you know, construction, and

uh facilities and IT, and all that stuff, so

maybe what I'll do, hm.

See, that's the other problem, too.

I could end up getting like 150,000 results.

So maybe I just run a few tests

first see how much I get with Total Business set-asides,

probably be somewhere around 2,000.

Full and Open most recent,

maybe

um

set a filter on response date,

see how much I get with that, and then

do a subsequent filter once we actually get it into the system.

And then with the USA Spending,

I think with that one

hm, I'm a see if I documented it already, but

I think with that one

we were trying to

Let me see.

Okay, yeah. So I we're looking for a IDIQ, MATOC,

GWAC vehicles

basically using USA Spending to look at

awards for um

for to target primes.

Um

So we know with the SAM.gov stuff,

the goal is to basically

pipeline is

import

filter

and then from the filter, then we decide

um

you know

which uh

which items we want to triage.

With the USA Spending, I'm not quite sure how that one

is going to work yet.

We're going to have to use some of this data here

to decide how it's going to work.

hm

Yeah, some of this data we already did to to figure out the

sourcing

Oh, it says it right here. Let me see. Pull IDV

vehicles in construction NAICS awards

awarded with in 1 to 3 years

identify multi-award pools

uh

build a subcontracting lead per prime

name UEI UEI vehicle ID

NAICS

for each target prime pull their active SAM.gov solicitations

to extract the

actual scope and trade

oh okay, I see.

All right, so that's the first step. Like it's basically

uh sourcing.

Once we

do the sourcing and then we kind of know the volume

that we're actually dealing with

Then we can move on, then we can figure out a strategy strategy for triage.

So

that's the first step.

All right, so, just making sure that I don't leave anything out. One of the things that we have to figure out is um how like around how many solicitations are being put out a day in the particular areas that we're looking at. And we need to know that information based on um yeah, based on what we pull from SAM, which we could probably do in one one take, you know, just maybe pull like a big chunk. Set the from date, see what's being put out. Um, and then uh USA Spending, too, that that's a little bit more trickier. Um, so yeah.
