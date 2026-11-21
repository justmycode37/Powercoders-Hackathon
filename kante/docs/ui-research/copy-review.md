# Kante UI Copy Review

*Scope reviewed: `app/index.html`, `app/public/manifest.webmanifest`, all files under `app/src/**`, `engine/crates/walk/src/steps.rs`, `engine/crates/server/src/{plan,state,api,live}.rs`, `engine/playground/index.html`, and live sample outputs from `localhost:8080`.*

---

## 1. Style Guide & Glossary (One-Page Reference)

### Variety of English
- **Use British / Swiss-European English**, aligned with the English version of the SBB Mobile app and Swiss station signage: *platform*, *sector*, *bay*, *lift*, *pushchair*, *zebra crossing*, *traffic lights*, *underpass*, *footbridge*, *centre*, *favourites*, *metres*, *kilometres*.
- **Keep Swiss proper nouns in their local language** (German, French, Italian, Romansh): *Zürich HB*, *Christoffelunterführung*, *Bubenbergplatz*, *Genève-Aéroport*, *Lugano, Centro*. Do not translate *Bahnhof*, *Platz*, *Strasse*, *Passage*, or *Unterführung*.

### Voice & Tone
- **Calm, direct, action-first.** Assume the reader is standing in a station concourse with one hand on their phone, possibly as a non-native English speaker.
- **Front-load what decides the next action:** put the time, urgency, or platform/bay first; put long Swiss headsigns and secondary context after.
- **Urgency proportional to stakes:** plain, neutral wording for normal timetables and estimates; unmistakable wording when action is required (*Cancelled*, *Platform changed*, *Missed change*, *Get off at the next stop*).
- **No blame, no developer jargon, no internal telemetry.** Never expose raw API terms (`siri-et`, `bad serviceDate`, `edge`, `quay`, `st:8507000`, `Planned in 125 ms`, `within 650 m`).
- **Be plain about uncertainty.** State clearly when a vehicle position is estimated, a walking route is approximate, a platform pin is at stop level, or step-free data comes from OpenStreetMap — in one short phrase, without repeating caveats on every row.

### Capitalisation, Punctuation & Symbols
- **Sentence case everywhere** — headings, buttons, tabs, chips, tags, alerts, and standalone subtitles (*Walking speed*, *Step-free*, *South side of Bubenbergplatz*, *Go* instead of all-caps *GO* unless deliberately treated as a brand button). Exceptions: proper nouns and line codes (*IC 1*, *S3*, *Kante*).
- **Contractions:** use natural, friendly contractions consistently (*I'm on board*, *You're on Bus 10*, *can't*, *doesn't*), rather than mixing *I'm* with stiff *cannot*.
- **Full stops:** omit trailing full stops on single-line labels, headings, chips, list rows, walking steps, and single-sentence notices/alerts. Use full stops on multi-sentence explanatory paragraphs.
- **Dashes & separators:**
  - En dash `–` (no spaces) for ranges: `Sectors A–C`, `2025-12-14 – 2026-12-12`.
  - Em dash ` — ` (with spaces) to separate a caveat or side-of-street clause.
  - Unicode minus `−` (U+2212) visually for negative levels and early times (`−1`, `−2 min`).
  - Middle dot ` · ` (with spaces) as the metadata separator (`6 min · 450 m`).
- **Avoid `′` (prime) for minutes** (reads as "feet" or "prime" to screen readers) and avoid `→` inside raw strings without accessible text (screen readers announce "rightwards arrow"; prefer *to* in accessible labels and prose).

### Numbers, Times, Units & Pluralisation
- **24-hour clock** (`Europe/Zurich`): `08:02`, `14:07`.
- **Durations:**
  - Never display `0 min` for a non-zero duration.
  - Under 1 min: `< 1 min` for walks; exact seconds (`45 s`) where seconds decide whether you make a change.
  - 1–59 min: `6 min`.
  - 60 min and above: `1 h 05 min`, `2 h`.
  - Never use decimal minutes (`3.8 min`).
- **Countdowns:** `now` when `< 60 s` (never `in 0 min`), `in 3 min`, `left` / `departed` when past.
- **Distances:** `m` under 1000 m (`15 m`, `450 m`), `km` from 1000 m (`1.4 km`, `12 km`). Never clamp `0 m` to `10 m`. Always include a space before the unit (`450 m`, `4.7 km/h`).
- **Delays:** `+3 min` / `−2 min` where space allows; `+3` / `−2` in tight columns **only** with `aria-label="3 minutes late"` / `"2 minutes early"`. Round consistently (nearest minute) in both engine alerts and app badges.
- **Pluralise every count properly:** `1 step` / `34 steps`, `1 minute` / `2 minutes`, `Sector B` / `Sectors A–C`, `1 change` / `2 changes`.

### Screen Readers & Accessibility
- **Never put an `aria-label` on a container button that omits critical child information** (such as `QuayCard` hiding sectors, platform changes, and accessibility notes, or `JourneyCard` hiding cancellation/delay alerts).
- **Spell out symbols and signs in `aria-label`:** `Level minus 1`, `Ground level`, `3 minutes late`, `to` instead of `→`.
- **Contextual loading labels:** `Loading departures`, `Loading journeys`, not bare `Loading`.

### Glossary

| Concept | Chosen term | Meaning & usage | Avoid |
|---|---|---|---|
| End-to-end itinerary | **Journey** | A planned door-to-door or stop-to-stop option (`No journeys found`, `Share journey`) | *connection* (ambiguous with transfer), *trip* (use for one vehicle run) |
| Switching vehicles | **Change** | Transferring between vehicles (`1 change`, `Tight change`, `Missed change`, `Extra change time`) | *transfer* (internal/API only), *connection* (`Connection missed`) |
| Single vehicle run | **Trip** / **Service** | One scheduled run of a line (`This trip has ended`, `Trip details`) | *course*, *journey* |
| Rail boarding place | **Platform** | Numbered rail/metro/rack/funicular track (`Platform 7`, `Platform changed`); matches SBB English and *along the platform* | *track* (reserve *tracks* for physical rails in side-of-street text), *quay* |
| Bus/tram numbered stand | **Bay** | Lettered/numbered bus or tram bay (`Bay L`, `Bay K1`) | *stand*, *edge*, *quay*, *boarding point* |
| Boat landing | **Pier** | Boat/ferry landing (`Pier 2`) | *quay*, *dock* |
| General or unsigned stop | **Stop** | Any public transport stop, and any unsigned tram/bus boarding edge | *edge* (never show to users), *boarding point* |
| Major rail hub | **Station** | Rail station; use **Stops and stations** when a list mixes both | Calling street bus stops *stations* |
| Platform section | **Sector** / **Sectors** | Train boarding zone (`Sector B`, `Sectors A–C`) | Mixing singular/plural (`Sectors B`, `sector A-C`) |
| Vertical floor | **Ground level** / **Level −1**, **Level 1** | `0` → *ground level* in prose (`0` on map switcher); no `+` prefix on positive levels | *level 0* in prose, *Level +1*, *street level*, *floor* |
| Departure verb / board | **Leave** (verb) / **Departures** (noun) | `Leave now`, `Leave at`, `Bus 10 leaves in 4 min`, `Departures` | Mixing `Leave now` and `Depart at` in one control |
| Exiting a vehicle | **Get off** | `Get off at Bern`, `I got off` | *alight* |
| Through-service | **Stay on board** | Vehicle continues under another line/number | *Stay seated* (standing passengers) |
| Real-time status | **Live** / **Expected** / **Timetable** | `observed` → *Live*; `predicted` → *Expected* (or *Live*); `timetable` → *Timetable* (`Timetable only`) | *forecast* (sounds like weather), *Timetable times*, *siri-et* |
| User's coordinates | **Location** | `Current location`, `Use my location`, `Waiting for your location…` | *position* (reserve for vehicle/boarding-point positions) |
| Map-chosen coordinates | **Pinned location** | User-dropped pin without a street address | *Dropped pin* (mismatch with app), *this point* |
| Step-free options | **Step-free** / **Fewer stairs** / **Wheelchair accessible** | Accessibility toggles in Options | *Wheelchair rules* |
| Transfer buffer | **Extra change time** | User-configured buffer added to changes (`2 min extra change time`) | *margin*, *slack*, *incl. 2 min margin* |
| Transit modes filter | **Transport types** | Settings section (`Train`, `Tram`, `Bus`, `Boat`, `Cable car & funicular`) | *Means of transport*, *modes* |
| Turn-by-turn walk list | **Directions** / **Walking directions** | Collapsible list on a walk leg (`Directions (10)` / `Hide directions`) | *Step by step (10)* / *Hide steps* (clashes with *34 steps up*) |

---

## 2. Concrete Changes — Web App (`app/`)

Ordered by user impact (highest first).

| # | File & line | Current text / template | Proposed text | Reason |
|---|---|---|---|---|
| 1 | `app/src/lib/lines.ts:60`, `app/src/map/sprites.ts:23` | `track: "Track"`, `edge: "Edge"` (`TRACK`, `EDGE`) | `track: "Platform"`, `edge: "Stop"` (`PLATFORM`, `STOP`) | Eliminates opaque transit jargon *"edge"* and aligns rail terminology with SBB English and *"along the platform"*. |
| 2 | `app/src/lib/time.ts:77-83` (`dur`) | `Math.round(s / 60)` → returns `"0 min"` for `1–29 s` | Return `"< 1 min"` for `0 < s < 60` (and add `durExact(s)` returning `"45 s"` for spare/missed times under 60 s) | Fixes absurd `"Change: walk 0 min to Track 5"`, `"0 min to spare"`, and `"Connection missed by 0 min"`. |
| 3 | `app/src/screens/results.tsx:204` (`firstAction`) | `s < 45 ? ... : s < 3600*3 ? \`${verb} in ${clock(Math.floor(s/60)*60)...}\`` | Use `s < 60 ? \`${verb} now\` : ...` and unify `verb = "Leave"` (`Leave now`, `Leave in 4 min`, `Leave at 08:02`) | Fixes `"Leave in 0 min"` / `"Departs in 0 min"` shown between 45 s and 59 s before departure, and unifies verb choice. |
| 4 | `app/src/screens/journey.tsx:318-320`, `app/src/screens/go.tsx:265` | `{dur(Math.floor(sp.s / 60) * 60)} to spare` + `incl. {m} min margin` / `— under your {m} min margin` | Under 60 s: `{sp.s} s to spare`; else `{dur(Math.floor(sp.s / 60) * 60)} to spare`. Show sub-note only when under buffer: `— less than your {m} min extra change time` | Fixes `"0 min to spare"` contradicting `"Tight change: 45 s to spare"`, removes `"incl."` abbreviation and `"margin"` jargon. |
| 5 | `app/src/screens/go.tsx:319-323` | `then: {next.steps[0].text...}` | Pick first step where `s.kind !== "depart"`: `Next: {firstActionStep.text}` | `steps[0]` is always the `Depart` step, so Go currently shows useless `"then: head south"` or `"then: start"`. |
| 6 | `app/src/screens/go.tsx:202-208` | When `ph.ride.cancelled`: still shows `head = "Board Bus 10 → …"` and countdown `departs 09:06 · in 2:10` | Override `head = \`Cancelled — ${lineTitle(ph.ride.line)}\``, hide countdown, and show a `Find another journey` button | Prevents telling a hurried traveller to board a cancelled vehicle. |
| 7 | `app/src/ui/quaycard.tsx:108` | `aria-label={\`${noun} ${q.label}, ${q.stationName}. Show on map\`}` | Remove overriding `aria-label` on `<button class="stand">` (or make `Show on map` a separate button / include full card text) | Overriding `aria-label` hides sectors, street side, level, platform-change alerts, and accessibility info from screen readers, and prints `"Edge , Bern…"` when unsigned. |
| 8 | `app/src/screens/journey.tsx:373` & `app/src/lib/geo.ts:61-64` | `StepRow` shows `metres(s.distM)` next to `s.text`; `metres()` clamps `< 10` to `"10 m"` | Omit distance in `step-meta` when already stated in `s.text` (or remove distance from `s.text`); fix `metres(m)` to return `"0 m"` for `0` and 1 m/5 m rounding under 20 m | Fixes contradictory rows like `"Walk 1 m along the platform | 10 m"` and `"Walk 65 m | 70 m"`, plus `"0 min on foot, 10 m"` on zero-walk journeys. |
| 9 | `app/src/screens/sheets.tsx:240` | `${mode === "dep" ? "Depart" : "Arrive"} ${dayLabel(t, now).toLowerCase()} ${hm(t)}` | Only lowercase `Today`/`Tomorrow`/`Yesterday`; keep `Mon 23 Nov` capitalised; use `Leave` / `Arrive by`: e.g. `Leave today at 08:30`, `Arrive by Mon 23 Nov, 08:30` | Fixes `"Depart mon 23 nov 08:30"` broken capitalisation and unifies *Leave* vs *Depart*. |
| 10 | `app/src/screens/sheets.tsx:185-189` | `live data from ${meta.data.realtime.source}` and `Map ${meta.data.attribution.join(" · ")}` | `Live delays active` (or `Timetable only — live delays off`), and remove leading `"Map "` before `attribution` | Fixes `"Map Timetable and real-time data: opentransportdata.swiss"` typo and stops leaking `"siri-et"`. |
| 11 | `app/src/screens/search.tsx:169` | `({ rail: "Train", tram: "Tram", bus: "Bus", boat: "Boat" })[m] ?? m` | Use `modeName(m)` from `lib/lines.ts` | Fixes raw lowercase API strings (`cableway`, `funicular`, `ondemand`, `rack`, `metro`) shown in search results. |
| 12 | `app/src/screens/results.tsx:66` | `aria-label={\`From ${name(q.from, "?")} to ${name(q.to, "?")}. Change\`}` | Handle `q.onboard`: `From on board ${obLeg ? lineTitle(obLeg.line) : ""} to ${name(q.to, "destination")}. Change` | Fixes screen readers announcing `"From ? to Ostermundigen, Rüti. Change"` when planning on board. |
| 13 | `app/src/screens/sheets.tsx:48` | `Changes are re-planned at once: slower walking needs longer changes and may pick other connections.` | `Journeys update right away: a slower pace allows more time to change and may suggest different routes.` | Eliminates double meaning of *"changes"* in one sentence and replaces *"connections"*. |
| 14 | `app/src/ui/quaycard.tsx:60` | `Sectors {sectors(q.sectors)}` | `{q.sectors.length === 1 ? "Sector" : "Sectors"} {sectors(q.sectors)}` | Fixes `"Sectors B"` plural error for single-letter sectors. |
| 15 | `app/src/ui/quaycard.tsx:81` | `Changed today — planned was {noun.toLowerCase()} {props.planned}` | `{props.planned ? \`Changed today (normally ${noun.toLowerCase()} ${props.planned})\` : "Changed today"}` | Fixes awkward German-calque syntax (*"planned was…"*) and empty-label dangling text. |
| 16 | `app/src/ui/quaycard.tsx:29-34` | `Exact position of this ${noun.toLowerCase()} is not known — the map shows the stop` / `Boarding point not known — the map shows the stop` | `Exact ${q.noun === "edge" ? "waiting spot" : noun.toLowerCase() + " location"} unknown — map pin shows the stop` / `Exact platform or bay unknown — map pin shows the stop` | Removes *"this edge"* and *"boarding point"* jargon; states uncertainty plainly. |
| 17 | `app/src/ui/quaycard.tsx:57, 74` | `{q.side.text}` / `"Boarding point"` / `Vehicle leaves towards <b>{towards}</b>` | Capitalise `q.side.text` (`South side of Bubenbergplatz`); omit fallback `"Boarding point"`; `Next stop: <b>{towards}</b>` (or `Leaves towards <b>{towards}</b>`) | Fixes lowercase standalone sentence, removes jargon, makes direction-of-travel instantly clear. |
| 18 | `app/src/ui/quaycard.tsx:46-49` | Unsigned sign shows `"Heading"` + rotated arrow with no accessible text | Add `aria-label={\`Heading ${compass(bearing)}\`}` on arrow wrapper; when no bearing, show `"Stop"` | Makes unsigned direction sign accessible to screen readers and removes `"Edge"`. |
| 19 | `app/src/screens/results.tsx:114-116` | `<Notice kind="warning"><Icon name="offline" /> {p.error ? \`${p.error} — showing the last answer from ${hm(p.at)}\` : "Updating…"}</Notice>` | When `!p.error`: calm `info` status `"Updating journeys…"` (no offline icon); when `p.error`: `"${p.error} — showing saved journeys from ${hm(p.at)}"` | Stops flashing an offline warning icon during normal background refresh; replaces robotic `"last answer"`. |
| 20 | `app/src/screens/results.tsx:130-132` | `title="No connections found"` / `Try another time, a longer walking distance, or more modes in the options.` | `title={stepFreeActive ? "No step-free journeys found" : "No journeys found"}` / contextual hint mentioning stairs/escalators when step-free is on, and *"transport types"* instead of *"modes"* | Helps step-free users understand why no route appeared; fixes terminology (*connections*, *modes*). |
| 21 | `app/src/screens/results.tsx:146` | `{Math.round(p.res.walkOnly.walkM / 10) * 10} m at {kmh} km/h · arrive {hm(…)}` | `{metres(p.res.walkOnly.walkM)} at {kmh} km/h · arrive {hm(…)}` | Prevents `"2450 m"` instead of `"2.5 km"` on longer direct walks. |
| 22 | `app/src/screens/results.tsx:154` | `Planned in {ms} ms · live data applied` / `· timetable only` | `{p.res.realtime ? "Live delays included" : "Timetable only — no live updates"}` | Removes developer latency telemetry (`Planned in 125 ms`) from user-facing UI. |
| 23 | `app/src/screens/results.tsx:243` | `JourneyCard` `aria-label` omits delay and alerts | Append delay (`3 min late`) and worst alert (`Cancelled`, `Tight change…`) to `aria-label` | Ensures screen-reader users hear cancellations, missed changes, and delays in the results list. |
| 24 | `app/src/screens/journey.tsx:77, 84-86`, `app/src/screens/go.tsx:101` | `Connection` / `This connection is no longer on offer` / `Show current connections` | `Journey` / `This journey is no longer available` / `Show current journeys` | Replaces supermarket phrasing (*"on offer"*) and standardises *Journey*. |
| 25 | `app/src/screens/journey.tsx:218` | `You have arrived` (bottom of static journey preview when last leg is a ride) | `{last.to.quay.stationName}` with `<small>Destination</small>` (matching `PlaceRow`) | Static journey preview for a future trip shouldn't tell the user *"You have arrived"*. |
| 26 | `app/src/screens/journey.tsx:342` | `Hide steps` / `Step by step ({steps.length})` | `Hide directions` / `Walking directions ({steps.length})` | Stops *"steps"* meaning both walking instructions and stair steps (*34 steps up*) on the same card. |
| 27 | `app/src/screens/journey.tsx:263-264` | `${leg.stairsUp} steps up` / `${leg.stairsDown} steps down` | `${leg.stairsUp} ${leg.stairsUp === 1 ? "step" : "steps"} up` (and down) | Fixes `"1 steps up"` pluralisation bug. |
| 28 | `app/src/screens/journey.tsx:294, 297-298` | `aria-label="Walk 0 min, 10 m..."` when `same`; `Change: walk 6 min to Bay L` | When `same`: `aria-label={\`Change at the same ${noun}. Show on map\`}`; otherwise `Walk ${dur(leg.durationS)} to ${target}` (or `Change to ${target} · ${dur(leg.durationS)} walk`) | Fixes broken `aria-label` on same-platform changes and awkward `"Change: walk"` phrasing. |
| 29 | `app/src/screens/journey.tsx:411`, `app/src/screens/station.tsx:197` | `observed: "live"`, `predicted: "forecast"`, `timetable: "timetable"` / `"timetable only"` | `observed: "Live"`, `predicted: "Expected"`, `timetable: "Timetable"` (consistent on both screens) | Replaces weather-like *"forecast"* and aligns `journey.tsx` and `station.tsx`. |
| 30 | `app/src/screens/journey.tsx:468-469` | `Stay seated — the vehicle continues as …` / `Runs about every …; times are indicative` | `Stay on board — the vehicle continues as …` / `Runs about every …; times are approximate` | Works for standing riders; replaces formal *"indicative"* with plain *"approximate"*. |
| 31 | `app/src/screens/journey.tsx:473` | `{stops} {stops === 1 ? "stop" : "stops"} · {dur(rideS)}` (counts only intermediate stops) | `{stops + 1} stops · {dur(rideS)}` (or `{stops} intermediate ${stops === 1 ? "stop" : "stops"} · {dur(rideS)}`) | Matches `Go` and `onboard-card`, which count the alighting stop too. |
| 32 | `app/src/screens/journey.tsx:140, 192, 506` | `from on board` / `Whole journey on the map` / `then 6 min walk to Bay L` | `On board` / `Show full journey` / `Then a 6 min walk to Bay L` | Fixes grammar (*"from on board"*, missing article *"a"*) and tightens button label. |
| 33 | `app/src/screens/journey.tsx:369-371` | `{levelShort(s.level!)} → {levelShort(s.toLevel!)}` | Add `aria-label={\`From ${levelSpoken(s.level!)} to ${levelSpoken(s.toLevel!)}\`}` | Screen readers otherwise read `"0 rightwards arrow minus 1"` with no word *"level"*. |
| 34 | `app/src/screens/go.tsx:215, 229` | `countLabel = \`${stationName} in\``; `sub = \`${line} → ${headsign} · arrives ${hm}\`` | `countLabel = "Arrive in"`; put stop in `head` (`Get off at ${stationName}` / `Stay on to ${stationName} · ${left} stops`); `sub = \`Arrives ${hm} · ${line} to ${headsign}\`` | Prevents long Swiss station/headsign names from overflowing the narrow countdown column or truncating the arrival time. |
| 35 | `app/src/screens/go.tsx:145, 137, 206, 220` | Always renders `Coming up` (even on Arrived); `auto`; `departs 09:06 · in`; `Arrived 09:26` (even in preview) | Hide `Coming up` when `list.slice(idx + 1)` is empty; `Auto` (or `Following`); `leaves in` (with `Leaves 09:06` in `sub`); `Arrive 09:26` when `now < j.arr` | Removes empty heading on arrival, cleans up clipped labels, fixes past tense during preview. |
| 36 | `app/src/screens/home.tsx:107-119` | `geoStatus === "asking"` shows subtext *"Use your position…"* ; `"unavailable"` shows heading *"Departures around you"* ; mixes *position*/*location* | Match heading + subtext for all 4 states (`idle`, `asking`, `denied`, `unavailable`); use *location* consistently; mention right-click on desktop | Fixes contradictory copy while locating and when GPS is unavailable. |
| 37 | `app/src/screens/home.tsx:192`, `app/src/screens/station.tsx:90` | `No departures in the next hours` / `Nothing leaves from here in the next hours` | `No upcoming departures` / `No departures from this ${noun} in the next few hours` | Fixes Germanism *"in the next hours"*. |
| 38 | `app/src/screens/home.tsx:211` | ``in ${first} minutes`` (in `LineCard` `aria-label`) | ``in ${first} ${first === 1 ? "minute" : "minutes"}`` (and use `at ${hm(l.next[0])}` when `first >= 60`; include quay if labelled) | Fixes `"in 1 minutes"` pluralisation bug and aligns spoken time with visual clock time. |
| 39 | `app/src/screens/home.tsx:127, 133` | `offline · showing saved` (shown on any `q.error`); `No stops within 650 m` | Distinguish offline (`Offline · saved departures`) from server error (`Couldn't refresh · showing saved`); `No stops nearby` | Honest error reporting and removes arbitrary internal 650 m radius. |
| 40 | `app/src/screens/station.tsx:16, 80, 89, 97, 245` | `chipLabel` lowercase `"south"`, `aria-label="Edge south"`; `Edge at this station`; `Timetable times`; `Service day 2026-11-23` | Capitalise (`South side`), `aria-label="Stop, south side"`; `Selected ${noun}`; `Timetable only — no live updates`; `Timetable for ${dayLabel(…)}` | Fixes lowercase chips, `"Edge"` jargon, awkward `"Timetable times"`, and transit-feed jargon `"Service day"`. |
| 41 | `app/src/screens/station.tsx:199-214` | When `t.cancelled`: still shows `prog.text` (`Between Bern and Olten`) and `"Position is an estimate…"` | Suppress vehicle position text and estimate note when `t.cancelled` is true | Avoids claiming a cancelled train is currently running between stations. |
| 42 | `app/src/screens/sheets.tsx:44` | `{Math.round(300 / (p.kmh / 3.6) / 6) / 10} min / 300 m` (e.g. `3.8 min / 300 m`) | `~${Math.round(1000 / (p.kmh / 3.6) / 60)} min / km` (e.g. `13 min / km`) or `3 min 50 s / 300 m` | Eliminates hard-to-parse decimal minutes (`3.8 min`). |
| 43 | `app/src/screens/sheets.tsx:130-157, 75, 81` | `Wheelchair rules`; `Means of transport`; `Less longest single walk` (`aria-label`); missing OSM caveat | `Wheelchair accessible` (+ OSM data note under Accessibility); `Transport types`; `Decrease ${label}` / `Increase ${label}` | Removes internal jargon, fixes broken stepper `aria-label` grammar, adds honest OSM caveat. |
| 44 | `app/src/screens/sheets.tsx:213, 219, 236` | `Leave now` / `Depart at` / `Arrive by`; `Tonight 20:00` chip stays `"Tonight 20:00"` after 20:00 even though it sets tomorrow | `Leave now` / `Leave at` / `Arrive by`; label chip `Tomorrow 20:00` (or hide) when past 20:00 | Fixes wrong date label on quick chip after 20:00 and unifies *Leave*. |
| 45 | `app/src/screens/sheets.tsx:254-314, 331, 347, 379-383` | `This point` / `Directions to here` / `No stop within 400 m` / `Go there` / `my position` / `Not where you want to test?` | `Map location` / `Directions here` / `Start from here` / `No stops nearby` / `Directions` / `my location` / `Want to check another area?` | Removes prototype wording (*"test"*), aligns *location* vs *position*, tightens map actions. |
| 46 | `app/src/screens/onboard.tsx:38, 63, 106` | `Which vehicle are you in?`; `Without your position Kante cannot tell…`; repeats `open a departure, then “I'm on this one”` on every row | `Which vehicle are you on?`; `Without your location, Kante can't tell which vehicle you're on…`; move instruction once under `Or pick from a nearby stop` | Natural preposition for trains/buses, consistent *location* + contractions, removes 4× repeated helper text. |
| 47 | `app/src/ui/bits.tsx:33, 40, 55, 88` | `QuayChip` lowercase `"south side"`; `planned=""` reads `"instead of "`; `Skeleton` `"Loading"`; `Delay` has no `aria-label` | Capitalise `"South side"`; guard `planned !== ""`; contextual `Skeleton` label; add `aria-label="3 minutes late"` to `Delay` | Screen-reader clarity and prevents broken `"instead of "` / unitless `"+3"`. |
| 48 | `app/src/lib/lines.ts:72` | ``Level ${level < 0 ? "−" + -level : "+" + level}`` (`Level +1`) | ``Level ${level < 0 ? "−" + -level : level}`` (`Level 1`) | Matches `steps.rs`, `journey.tsx:251`, and map switcher (`1`, `0`, `−1`). |
| 49 | `app/src/screens/search.tsx:75, 132, 194, 247, 289` | `Needs your position`; `Station, address or place`; `Stations`; `choose the point on the map`; `Use this point` | `Location permission needed`; `Stop, station or address`; `Stops and stations`; `choose a location on the map`; `Use this location` | Aligns vocabulary (*location*, *stop*, *station*) and drops vague *"point"*. |
| 50 | `app/src/lib/time.ts:91` | `return "gone";` | `return "left";` (or `"departed"`) | Calmer, clearer departure-board status than abrupt `"gone"`. |
| 51 | `app/index.html:8, 31`, `app/public/manifest.webmanifest:4` | `the exact bay, track and sector`; `Kante needs JavaScript.` | `the exact bay, platform and sector`; `Kante needs JavaScript to run. Please enable it in your browser settings.` | Aligns metadata with *Platform* and gives a helpful `<noscript>` message. |

*Low-priority note on `engine/playground/index.html` (debug page):* uses `"Track"` / `"Edge"` (line 87), `′` for delay minutes (`+3′`, line 253), `"level boarding"` vs `"Step-free boarding"` (line 249), and `"Boarding point"` — if kept as a developer tool, updating `NOUN` (line 87) and delay unit (line 253) keeps test screenshots consistent with the app.

---

## 3. Concrete Changes — Engine (`engine/`)

Ordered by user impact (highest first).

| # | File & line | Current text / template | Proposed text | Reason |
|---|---|---|---|---|
| 1 | `engine/crates/server/src/plan.rs:366` | `format!("{} {} is cancelled", r.line.category, r.line.name)` | `format!("{} is cancelled", line_title(&r.line))` (e.g. `IC 8 is cancelled`, `Bus 10 is cancelled`) | Currently outputs doubled/raw codes like **`IC IC8 is cancelled`**, **`ICE ICE is cancelled`**, **`B 10 is cancelled`**. |
| 2 | `engine/crates/server/src/plan.rs:371` | `format!("{} is running about {} min late", if name.is_empty() { cat } else { name }, dep_delay_s / 60)` | `format!("{} is {} min late", line_title(&r.line), (dep_delay_s + 30) / 60)` (e.g. `Bus 10 is 4 min late`) | Currently outputs bare **`10 is running about 3 min late`** (missing *Bus*/*Tram*) and truncates minutes instead of rounding like the app. |
| 3 | `engine/crates/server/src/plan.rs:378` | `format!("Boarding point changed: now {} (planned {})", label, planned)` | `format!("{} changed at {}: now {} {} (was {})", cap(noun), station, noun, label, planned)` (see Section 4 for empty-label fallback) | Replaces *"Boarding point"* jargon, adds which station changed, and guards empty labels. |
| 4 | `engine/crates/server/src/state.rs:345-357` | `noun`: `"track"` for rail, `"edge"` for unsigned stops | `"platform"` for rail (when labelled), `"stop"` instead of `"edge"` (keep internal `precision` for map rendering, never emit `"edge"` as display noun) | Removes `"edge"` from all API-generated sentences and aligns rail with SBB English (*Platform*). |
| 5 | `engine/crates/server/src/plan.rs:346, 348, 354, 359` | `"This change is no longer possible…"` / `"Tight change: {} s to spare…"` / `"Shorter than the official minimum change time here ({} min)"` / `"Walking time for this change is estimated…"` | Include the station name and human time format (e.g. `Missed change at Bern due to delays`, `Tight change at Bern: 45 s to spare`, `Shorter than the official 6 min change time at Bern`) | Alerts appear at the top of the journey card where *"here"* and *"this change"* are ambiguous on multi-change trips; fixes `0 s` / `75 s` formatting. |
| 6 | `engine/crates/walk/src/steps.rs:501` | `" at the signals"` | `" at the traffic lights"` | *"Signals"* means railway signals in a Swiss rail app and confuses non-native speakers. |
| 7 | `engine/crates/walk/src/steps.rs:548-555` | `"Go up to street level (connection not mapped in detail)"` / `"Change floor here (connection not mapped in detail)"` | `"Go up to ground level (stairs or lift not mapped)"` / `"Change levels here (stairs or lift not mapped)"` | Stops overloading *"connection"* (3rd meaning!) and standardises *ground level* and *level* (not *floor*/*street level*). |
| 8 | `engine/crates/walk/src/steps.rs:448, 580` | `to level 0` / `on level 0` | `to ground level` (for `l == 0`), `to level −1`, `to level 1` | Matches `journey.tsx` and immediately tells non-European travellers what level 0 means. |
| 9 | `engine/crates/server/src/plan.rs:144-157` | `"Arrive at the stop {st}"` / `"Arrive at edge {l}"` / `", sector {sec}"` (always singular, ASCII `-`) | `"Arrive at {st}"` / `"Arrive at {noun} {l}"` / singular `", sector B"` vs plural `", sectors A–C"` (en dash) | Fixes `"Arrive at the stop…"`, removes `"edge"`, fixes sector singular/plural and en dash. |
| 10 | `engine/crates/walk/src/steps.rs:357, 456-494` | Keeps 1–2 m trailing `"Walk 1 m along the platform"`; repeats `"along Bogenschützenstrasse"` on consecutive steps; never converts ≥ 1000 m to `km` | Fold trailing platform stubs `< 5 m` into the previous step or drop them; use `"continue … along {name}"` when street name repeats; switch `fmt_dist` to `km` at `1000 m` | Eliminates noisy `"Walk 1 m along the platform"` on nearly every Bern route and awkward repeated street names. |
| 11 | `engine/crates/walk/src/steps.rs:568` | `"Go through the entrance into the building"` / `"Go through the entrance into the underpass"` | `"Enter the building"` / `"Enter the underpass"` | Cuts 4 redundant words (`"Go through the entrance"`) that slow down scanning. |
| 12 | `engine/crates/walk/src/steps.rs:526` | `"Take the ramp beside the stairs down to level −1 (45 m)"` | `"Take the ramp down to level −1 (beside the stairs, 45 m)"` | Keeps the critical direction (*down to level −1*) right after *Take the ramp*. |
| 13 | `engine/crates/server/src/plan.rs:485` | `format!("On board {} → {}", name_or_cat, headsign)` | `format!("On board {} to {}", line_title(&badge), headsign)` | Fixes missing mode (`"On board 10 → …"` → `"On board Bus 10 to …"`) and screen-reader arrow. |
| 14 | `engine/crates/server/src/plan.rs:187` | `format!("Walk about {} m to {}", leg.distance_m, b.name)` | Round to nearest 10 m (or `km` ≥ 1000 m): `format!("Walk about {} to {} (no mapped footpath)", fmt_dist_approx(d), b.name)` | Fixes false precision (`"Walk about 237 m"`) and states honestly why it's approximate. |
| 15 | `engine/crates/server/src/state.rs:433` | `"Dropped pin"` | `"Pinned location"` | Matches `app/src/plan.ts:29, 31` so map pins don't change name after a server round-trip. |
| 16 | `engine/crates/server/src/plan.rs:442, 464-472, 508, 520` & `state.rs:409, 426, 429` & `api.rs:305-360` | Lowercase / developer error strings (`"coordinate outside the supported area"`, `"no public transport stop within walking distance of the destination"`, `"that trip has already finished"`, `"unknown station st:…"`, `"bad serviceDate"`) | User-facing sentence-case errors (see Section 4 & Section 5), e.g. `"Outside Switzerland. Kante covers Switzerland and border areas."`, `"This trip has already finished."` | `client.ts:38` renders `j.error` verbatim in UI banners. |

---

## 4. Corrected Sentence Templates

### 4.1 Helper: Human Line Title (Engine — shared by alerts & on-board place name)
Mirror `app/src/lib/lines.ts:lineTitle` in Rust:
- If `line.name` is empty: mode display name (`Train`, `Tram`, `Bus`, `Metro`, `Boat`, `Funicular`, `Cable car`, `Lift`, `On-demand bus`, `Service`).
- If `mode` is `Rail` or `RackRail`: `line.name` as-is (`IC 1`, `IR 35`, `S3`, `RE 37`). *(Do NOT prepend `line.category`, which causes `IC IC8`.)*
- Otherwise (`Bus`, `Tram`, `Boat`, `Metro`, etc.): `"{Mode} {line.name}"` (`Bus 10`, `Tram 15`, `Boat 2`).

### 4.2 Helper: Level & Distance Formatting (`steps.rs` & `plan.rs`)
- **Level in prose (`fmt_level_phrase`):**
  - `0` → `"ground level"`
  - `-2` → `"level −1"`, `-3` → `"level −1.5"`, `2` → `"level 1"` (Unicode minus `−`, never `+1`).
- **Distance (`fmt_dist`):**
  - `< 20 m`: round to 1 m (`14 m`).
  - `20–99 m`: round to 5 m (`65 m`).
  - `100–949 m`: round to 10 m (`240 m`).
  - `>= 950 m`: kilometres (`1.0 km`, `1.4 km`; whole km from `10 km`).
- **Sectors (`fmt_sectors`):**
  - Single character (e.g. `"B"`): `"sector B"` (card tag: `"Sector B"`).
  - Range or multiple (e.g. `"A-C"`, `"AB"`): replace `-` with `–` → `"sectors A–C"` (card tag: `"Sectors A–C"`).

### 4.3 Walking Instructions (`engine/crates/walk/src/steps.rs`)

| Step case | Condition | Proposed template | Example |
|---|---|---|---|
| **Depart** | Non-ground level + heading | `Start on {level_phrase}, heading {compass}` | `Start on level −1, heading east` |
| | Non-ground level, no heading | `Start on {level_phrase}` | `Start on level −1` |
| | Ground/unknown level + heading | `Head {compass}` | `Head south` |
| | Zero-distance / no heading | *(omit Depart step, or merge into Arrive)* | *(no standalone `"Start"` step)* |
| **Turn prefix** | 35°–59° / 60°–135° / >135° | `Bear {dir} and {base}` / `Turn {dir} and {base}` / `Turn sharply {dir} and {base}` | `Turn sharply right and walk 25 m along the platform` |
| **Walk (named)** | Same street/passage as previous step | `Continue {dist} {prep} {name}` *(with turn: `Turn left and continue 45 m along Bogenschützenstrasse`)* | `Turn left and continue 45 m along Bogenschützenstrasse` |
| | Tunnel or indoor | `Walk {dist} through {name}` | `Bear right and walk 150 m through Christoffelunterführung` |
| | Open area / square | `Walk {dist} across {name}` | `Walk 50 m across Welle` |
| | Street / footway | `Walk {dist} along {name}` | `Turn right and walk 100 m along Schanzenstrasse` |
| **Walk (unnamed)** | Tunnel (foot / road) | `Walk {dist} through the underpass` / `through the tunnel` | `Turn right and walk 75 m through the underpass` |
| | Bridge (foot / road) | `Walk {dist} across the footbridge` / `across the bridge` | `Walk 40 m across the footbridge` |
| | Open area / square | `Walk {dist} across the square` | `Walk 80 m across the square` |
| | Indoor corridor | `Walk {dist} through the passage` *(or `through the concourse` if area)* | `Turn right and walk 100 m through the passage` |
| | Road | `Walk {dist} along the road` | `Walk 45 m along the road` |
| | Plain footway | `Walk {dist}` | `Walk 35 m` |
| | + unmapped level jump suffix | append ` on {level_phrase}` | `Walk 35 m on level −1` |
| **Platform** | `< 5 m` directly before Arrive | *(fold into previous step / omit)* | *(no `"Walk 1 m along the platform"`)* |
| | Otherwise | `Walk {dist} along the platform` | `Walk 110 m along the platform` |
| **Crossing** | Named + signals | `Cross {street} at the traffic lights` | `Turn left and cross Schanzenstrasse at the traffic lights` |
| | Named + zebra | `Cross {street} at the zebra crossing` | `Cross Bundesplatz at the zebra crossing` |
| | Named, unmarked | `Cross {street}` | `Turn right and cross Bubenbergplatz` |
| | Unnamed + signals / zebra / plain | `Cross the street at the traffic lights` / `at the zebra crossing` / `Cross the street` | `Turn left and cross the street at the traffic lights` |
| **Stairs** | Direction + target level + steps | `Take the stairs{ up| down}{ to {level_phrase}}{ (1 step)| ({n} steps)}` | `Take the stairs up to ground level (34 steps)` |
| | Unknown direction or level | Omit unknown part cleanly | `Take the stairs up (30 steps)` / `Take the stairs (12 steps)` |
| **Ramp** | Standalone | `Take the ramp{ up| down}{ to {level_phrase}}{ ({dist})}` *(dist if ≥ 10 m)* | `Take the ramp down to level −1 (45 m)` |
| | Beside stairs | `Take the ramp{ up| down}{ to {level_phrase}} (beside the stairs{, {dist}})` | `Take the ramp down to level −1 (beside the stairs, 45 m)` |
| **Escalator** | Direction + target level | `Take the escalator{ up| down}{ to {level_phrase}}` | `Take the escalator up to ground level` |
| **Moving walkway** | Any | `Take the moving walkway ({dist})` | `Take the moving walkway (80 m)` |
| **Lift** | Known target level | `Take the lift{ up| down} to {level_phrase}` | `Take the lift up to level 1` |
| | Unknown target level | `Take the lift` | `Take the lift` |
| **Unmapped level change** | Up / down / unknown | `Go up to {level_phrase} (stairs or lift not mapped)` / `Go down to {level_phrase} (stairs or lift not mapped)` / `Change levels here (stairs or lift not mapped)` | `Go down to level −1 (stairs or lift not mapped)` |
| **Enter / Exit** | Building or underpass | `Enter the building` / `Enter the underpass` / `Exit the building` / `Exit the underpass` | `Turn right and enter the building` |
| **Arrive (to quay)** | Labelled (`platform`, `bay`, `pier`) | `Arrive at {station_prefix}{noun} {label}{, {sector_phrase}}{ — {side}}{ ({level_phrase})}` *(include `{station}, ` when walking to a different stop name; omit level if 0)* | `Arrive at bay L — south side of Bubenbergplatz` / `Arrive at platform 3, sectors A–B` / `Arrive at Bern, Hirschengraben, bay C — east side of Hirschengraben` |
| | Unsigned or station-level stop | `Arrive at {station}{ — {side}}{ ({level_phrase})}` | `Arrive at Zürich, Bahnhofstrasse/HB — east side of Bahnhofstrasse` |
| **Arrive (non-quay)** | Named destination (not *Pinned location*) | `Arrive at {name}{ on {level_phrase}}` | `Arrive at Bundesplatz 3` |
| | Unnamed / pinned destination | `Arrive at your destination{ on {level_phrase}}` | `Arrive at your destination on level 2` |
| **Approximate walk (fallback)** | No walkable path in graph | `Walk about {fmt_dist(d)} to {to_name} (no mapped footpath)` | `Walk about 240 m to Bern (no mapped footpath)` |

*(Note for UI `StepRow`: because distance is already embedded in `Walk …` / `Ramp …`, hide `s.distM` in the right-hand column when `s.text` contains a distance, or remove the distance from `s.text` consistently — never show two different rounded numbers on the same row.)*

### 4.4 Journey Alerts (`engine/crates/server/src/plan.rs`)

| Alert | Severity | Proposed template | Example |
|---|---|---|---|
| **Missed change** | `severe` | `Missed change at {station} due to delays` | `Missed change at Bern due to delays` |
| **Tight change (0 s)** | `warning` | `Tight change at {station}: no spare time after walking` | `Tight change at Bern: no spare time after walking` |
| **Tight change (1–59 s)** | `warning` | `Tight change at {station}: {spare} s to spare` | `Tight change at Bern: 45 s to spare` |
| **Tight change (60–89 s)** | `warning` | `Tight change at {station}: 1 min {rem} s to spare` *(if `rem == 0`: `1 min to spare`)* | `Tight change at Bern: 1 min 15 s to spare` |
| **Shorter than official minimum** | `info` | `Shorter than the official {min} min change time at {station}` | `Shorter than the official 6 min change time at Bern` |
| **Unmapped transfer walk** | `info` | `Walking time at {station} is estimated (no mapped footpath)` | `Walking time at Olten is estimated (no mapped footpath)` |
| **Cancelled service** | `severe` | `{line_title} is cancelled` | `IC 8 is cancelled` / `Bus 10 is cancelled` |
| **Delayed service (≥ 3 min)** | `info` | `{line_title} is {rounded_min} min late` | `Bus 10 is 4 min late` / `IC 1 is 5 min late` |
| **Platform / bay changed** | `warning` | If both labels known: `{Noun} changed at {station}: now {noun} {new} (was {old})`; if `old` empty: `{Noun} changed at {station}: now {noun} {new}`; if `new` empty: `{Noun} changed at {station} — check station displays` | `Platform changed at Bern: now platform 5 (was 7)` |

---

## 5. Missing States & Proposed Wording

| State | Where it occurs | Current behaviour | Proposed wording |
|---|---|---|---|
| **Timetable-only mode (no API key / feed off)** | Home, Results, Station, Options (`meta.realtime.enabled === false`) | Silent on Home & Options; tiny footnote on Results | **Banner / chip (quiet `info`):** `Timetable only — live delays and platform changes aren't available` · **Options footer:** `Timetable only (live data off)` |
| **Live feed stale or failing** | `meta.realtime.error` set or `updatedAt` > 5 min old | Ignored; UI still claims live data is on | **Quiet `warning` notice:** `Live updates are delayed — showing timetable times` |
| **No step-free / wheelchair route found** | `Results` when `stairs === "never"` or `wheelchair === true` | Generic *"No connections found — Try another time, a longer walking distance, or more modes"* | **Title:** `No step-free journeys found` (or `No wheelchair-accessible journeys found`) · **Body:** `Try another time, increase the maximum walk, or allow stairs and escalators in Options.` + action button `Open options` |
| **Step-free user given an approximate walk** | `Journey` when `leg.approximate && (stairs === "never" || wheelchair)` | Only shows small `estimated` tag | **Warning note on walk leg:** `Footpath not mapped — step-free access couldn't be verified here` |
| **Outside Switzerland / coverage area** | `Home` (GPS abroad), `Pick`, `Plan` (`state.rs:429`) | `No stops within 650 m` or lowercase `coordinate outside the supported area` | **API error:** `Outside Switzerland. Kante covers Switzerland and border areas.` · **Home empty state (when outside bbox):** `Outside Kante's coverage area` / `Kante covers public transport in Switzerland. Move the map to Switzerland or search for a Swiss stop.` |
| **Outside detailed walking coverage** | `Options` / `Journey` when outside `meta.walkBbox` | No explanation when walks fall back to straight lines | **Note on walk leg:** `Detailed indoor and walking map isn't available here — walking time is estimated.` |
| **Offline during background refresh** | `Station`, `Trip`, `Onboard` when cached data exists and refresh fails | Refresh error is silently hidden when `data` is already present | **Subtle status pill:** `Offline — showing times from {hm(at)}` (and distinguish server errors: `Couldn't refresh — showing times from {hm(at)}`) |
| **Location denied / unavailable / locating** | `Home`, `Results`, `Onboard`, `LocateSheet` | Broken branches on Home (`asking`/`unavailable`), dead button on `LocateSheet` when denied, no desktop right-click hint | **Locating:** `Finding your location…` / `Wait a moment, or search for a stop instead.` · **Denied:** `Location access is blocked` / `Allow location in your browser settings, or long-press the map (right-click on desktop) and choose “I'm here”.` · **Unavailable:** `Couldn't find your location` / `Check your device's location settings, or long-press the map and choose “I'm here”.` |
| **Trip already finished (on-board)** | `plan.rs:472`, `Trip`, `Home` on-board banner | Raw `"that trip has already finished"`; disabled `"I'm on this one"` button with no explanation | **API error:** `This trip has already finished.` · **Trip header (when done):** `This trip has ended` (hide disabled button or show subtle note `Trip ended at {hm(arr)}`) |
| **Cancelled or missed leg during live guidance** | `Go` screen (`go.tsx`) | Still says `"Board Bus 10"` with countdown; no recovery button | **Card:** `Cancelled — Bus 10` (or `You may have missed Bus 10`) · **Primary CTA:** `Find next journey` (re-plans from current stop/location) |
| **Search loading / Station bay filter loading** | `Search` (`search.tsx`), `Station` (`station.tsx`) | No visible feedback while results or quay departures load | **Search:** subtle inline `Searching…` / skeleton rows · **Station bay switch:** inline `Loading departures…` (`aria-live="polite"`) |
| **Same start and destination chosen** | `Search` (`search.tsx:31-32`) | Silently clears the other field | **Toast:** `Start and destination can't be the same` |
| **First-time empty search** | `Search` (no saved places, no recents) | Only two quick rows, blank space below | **Subtle hint:** `Search for any stop, station, address or place in Switzerland.` |

---

## 6. Top Ten Changes to Make First

1. **Fix doubled/raw line names in engine alerts and on-board labels** (`engine/crates/server/src/plan.rs:366, 371, 485`) — stops showing `"IC IC8 is cancelled"`, `"B 10 is cancelled"`, `"10 is running about 3 min late"`, and `"On board 10 → …"` by sharing a single human line-title formatter and rounding delay minutes consistently.
2. **Eliminate `"edge"` jargon and unify `"Track"` → `"Platform"`** (`engine/crates/server/src/state.rs:345-357`, `plan.rs:144-157, 378`, `app/src/lib/lines.ts:60`, `app/src/map/sprites.ts:23`, `app/src/ui/quaycard.tsx`) — removes `"Exact position of this edge is not known"`, `"Change at the same edge"`, `"Boarding point changed"`, and aligns rail wording with SBB English (*Platform*) and *"along the platform"*.
3. **Fix all `0 min` and `10 m` rounding contradictions** (`app/src/lib/time.ts:77-83`, `app/src/lib/geo.ts:61-64`, `app/src/screens/results.tsx:204`, `app/src/screens/journey.tsx:318, 373`, `app/src/screens/go.tsx:265`) — eliminates `"Leave in 0 min"`, `"0 min to spare"`, `"Change: walk 0 min"`, `"0 min on foot, 10 m"`, and `"Walk 1 m | 10 m"` on the same row.
4. **Fix `Go` screen's `"then: head south"` preview, cancelled-vehicle countdown, and long-name truncation** (`app/src/screens/go.tsx:202-229, 319-323`) — skip `Depart` steps in the post-ride preview, stop counting down to a cancelled vehicle (offer *Find next journey*), and stop Swiss station names from overflowing or truncating the arrival time.
5. **Add station context to journey alerts and clean up walking instructions** (`engine/crates/server/src/plan.rs:346-380`, `engine/crates/walk/src/steps.rs:357, 448, 501, 548-568`) — include station names in transfer/platform alerts, change *"at the signals"* → *"at the traffic lights"*, *"level 0"* → *"ground level"*, *"(connection not mapped in detail)"* → *"(stairs or lift not mapped)"*, and drop 1–2 m platform stubs.
6. **Fix `QuayCard` screen-reader erasure and grammar bugs** (`app/src/ui/quaycard.tsx:60, 74, 81, 108`, `app/src/ui/bits.tsx:88`) — stop `aria-label` on `<button class="stand">` from hiding sectors, platform changes, and accessibility status; fix `"Sectors B"` and `"planned was track 7"`; add `aria-label` to `Delay`.
7. **Fix `TimeSheet` capitalisation, verb mismatch, and after-20:00 chip bug** (`app/src/screens/sheets.tsx:213, 219, 236, 240`) — stops `"Depart mon 23 nov 08:30"`, unifies `Leave now` / `Leave at` / `Arrive by`, and fixes `"Tonight 20:00"` after 20:00.
8. **Fix `SettingsSheet` attribution typo, `"siri-et"` leak, double-meaning `"Changes"`, and missing OSM caveat** (`app/src/screens/sheets.tsx:48, 131-149, 185-189`) — fixes `"Map Timetable and real-time data…"`, removes `"siri-et"`, rewrites the confusing speed hint, renames `"Wheelchair rules"` → `"Wheelchair accessible"`, and adds a one-line OpenStreetMap caveat.
9. **Fix `Search` raw mode names, `Results` step-free empty state, and `Updating…` offline-warning alarm** (`app/src/screens/search.tsx:169`, `app/src/screens/results.tsx:114-116, 130-132, 154`) — use `modeName()` for cableways/funiculars, add a dedicated *"No step-free journeys found"* state, stop showing an offline warning icon during normal refresh, and remove `"Planned in 125 ms"`.
10. **Standardise vocabulary (`Journey` vs `Change`, `Location` vs `Position`, `Live` vs `Expected` vs `Timetable`, `Directions` vs stair `steps`) and fix pluralisation/Germanisms across screens** (`home.tsx`, `journey.tsx`, `station.tsx`, `onboard.tsx`, `sheets.tsx`) — eliminates `"on offer"`, `"in the next hours"`, `"Timetable times"`, `"forecast"`, `"in 1 minutes"`, `"1 steps up"`, and `"from on board"`.
