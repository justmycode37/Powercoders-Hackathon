# Transit (transitapp.com) — design study for Kante

Studied version: Transit 6.x (6.0 redesign of August 2025; App Store version 6.3.7 of 2026-11-06).
Researched 2026-11-21 from Transit's own blog and help centre, the App Store listing, one independent review with
real-device screenshots, and 300 recent App Store reviews. Every screenshot cited is in [`transit/`](transit/) and
listed in [`transit/sources.md`](transit/sources.md); file names below refer to that folder.

**How to read the numbers**

- `W` = screen width. Sizes are given as **% of W** and as **pt on a 390-pt-wide phone** (multiply % by 3.9).
  Transit's mock-ups are drawn on a 1 : 2.16 screen (390 × 844 pt class).
- Measured values come from pixel analysis of the cited image (stated per table). They are accurate to about ±1 % of W.
- Font sizes are **derived**, not read from a spec: Transit states that the ETA-card numeral is "60" points
  (blog, 6.0 post). In the same-scale mock-up that numeral has a cap height of 12.2 % W, so every other size is
  scaled from its cap height against that anchor.
- Colours marked *sampled* were read from image pixels. Marketing renders differ from each other (the help-centre
  images are less saturated than the blog images), so treat hex values as indicative.
- **"From memory, unverified"** marks anything I could not confirm in a source I opened. A consolidated list is in §10.

---

## 1. Screen inventory and navigation model

### 1.1 What you see on launch

One screen, no tab bar, no onboarding gate between you and departures (`six-o-09`, `help-howto-01`):

- **Top 44 % of the screen: map** centred on your location (blue dot), with the network's main lines drawn in
  their colours and pins for bikeshare / scooters / carshare.
- **Bottom 56 %: the "Nearby" list** — full-bleed coloured cards, one per nearby line, each with a big countdown.
- **A search bar ("Where to?") straddling the boundary** between map and list.
- **Top-left: your avatar** (an emoji in a pale disc) with a small gear badge → profile and settings.

Transit treats this as untouchable. In 2014 they moved the Nearby list behind a map button and "almost 20 % of
our users stopped using Transit. Literally overnight" (5.0 post). Their stated founding idea: riders mostly know
their route; they want to know *when*, without planning a trip first (4.0 post, METRO interview).

### 1.2 Screen list

| Screen | Reached by | Leaves by |
|---|---|---|
| Home (map + Nearby) | launch | — |
| Search | tap the search bar | X |
| Planner results (timeline) | pick a destination; or tap the favourite shortcut at the right end of the search bar | red X |
| Trip detail | tap a result row | red X / swipe down |
| Route (line) detail | tap a Nearby card; or search a line by name/number | red X / swipe down |
| Full schedule | route detail → swipe the ETA cards to the end → "More departures" | X |
| Stop on a route | route detail → tap a stop in the list (ETA cards then refer to that stop) | — |
| Service alerts for a line | route detail → alert chip, or bell button | X |
| GO (live guidance) | **GO** button on route detail or trip detail; or the AutoGO prompt on home | red X = minimise (trip keeps running) |
| GO minibar | minimising GO; floats over home | tap to reopen |
| GO settings | bell button inside GO | sheet dismiss |
| Vehicle sheet | tap a vehicle marker | tap outside |
| Profile / settings / leaderboards / trip history | avatar on home | X |

### 1.3 Navigation model

- **A stack of full-screen cards over the map, not tabs.** Each deeper screen keeps a map at the top and is closed
  by a round white button with a red ✕ in the top-right corner. On iOS you can also swipe down to go back
  (introduced in 5.0 because the top buttons were out of thumb reach). On Android the system back gesture is used
  (help: GO article).
- **Controls sit low.** The search bar was deliberately moved from the top to the middle of the screen in 5.0
  ("phones have gotten bigger … our thumbs haven't").
- **There is no separate "stop" screen.** A stop is always seen through a line: tap a stop inside a route's stop
  list, or search a place and choose "Show nearby lines" (long-press or "…" on a search result), which moves the
  home screen's reference location there.
- **Map ↔ list coupling on home.** Panning the map re-centres the Nearby list on the panned location; Transit
  turned the search bar purple while you were away from your real location (5.0 post, 2018). *Whether the purple
  state survives in 6.x is unverified.*
- **How the list scrolls over the map** (pull up to cover the map, pull down to reveal it) — *from memory,
  unverified; no source I opened documents it.*

---

## 2. Nearby cards

### 2.1 Anatomy

```
x=0                                                         x=W
┌───────────────────────────────────────────────────────────┐ ─┬─
│◄3.5%►                    · ·  (page dots, if >1 direction) │  │ 3.9% W top padding
│  55            ← line number, heaviest weight, ~44 pt      │  │
│                                                    3 ))    │  │
│  ➜ North       ← direction/headsign, bold ~19 pt   minutes │  │ 29 % W
│                                                   ◄─7.4%──►│  │ (113 pt)
│  Station Saint-Laurent / de Maisonneuve  ← stop, ~15 pt    │  │
│                                                            │  │ 3.3% W bottom padding
└───────────────────────────────────────────────────────────┘ ─┴─
   full-bleed line colour, no radius, no gap; 1–2 px darker hairline between cards
```

Measured on `six-o-09` (6.0 phone, screen 540 px wide):

| Element | Measured | pt @390 |
|---|---|---|
| Card width | 100 % W, edge to edge | 390 |
| Card height (one-line headsign) | 29.1 % W | 113 |
| First card (its top sits under the search bar) | 31.3 % W | 122 |
| Card height in 5.0, for comparison | 26.3 % W | 103 |
| Left padding | 3.5 % W | 14 |
| Line number: cap height / derived font size | 8.9 % W / ≈ 44 pt | — |
| Line number top offset | 3.9 % W | 15 |
| Gap number → direction row, direction → stop row | 2.6 % W each | 10 |
| Direction row: arrow-in-circle icon ⌀ | 4.3 % W | 17 |
| Direction text | bold, ≈ 18–20 pt | — |
| Stop name | regular, ≈ 15 pt | — |
| Bottom padding | 3.3 % W | 13 |
| Countdown numeral: cap height / derived size | 8.1 % W / ≈ 40 pt | — |
| Countdown right edge → screen edge | 7.4 % W | 29 |
| "minutes" label | regular ≈ 10–11 pt, centred under the numeral, 1.7 % W below it | — |
| Real-time waves | two arcs, ≈ 2 % W, at the numeral's top-right shoulder, inside the 7.4 % gutter | ≈ 8 |

**Size ratio to keep:** line number : countdown : direction : stop : unit label ≈ **44 : 40 : 19 : 15 : 11**.
Two elements shout (which line, how many minutes); everything else is at most half their size.

Content rules (`help-howto-01`, `sixcolors-01`):

- **Line identifier, top-left.** A number/short name is set as bare heavy text. Systems whose lines are known by
  a roundel get the roundel instead: a white disc with the letter in the line colour ("A", "B"), or the agency's
  own bullet artwork (Montréal métro "② "). A rail line with a long name gets a mode icon plus a white name tag
  ("🚆 Forest Line", `blog-autogo-prompt`).
- **Direction row.** A filled circle with a right arrow, then the headsign or cardinal direction ("North",
  "Southbound to Forest", "Athens Chapel"). Long headsigns wrap to two lines and the card grows (real device:
  "Oakland Amtrak at Jack London Square", `sixcolors-01`).
- **Stop row.** The name of the *closest stop* of that line in that direction. **No walking distance or walking
  time is shown on the home card** (verified in every home screenshot); the walk time appears only after you open
  the line ("🚶 5 minutes" above the first stop).
- **Countdown, right.** One numeral — the next departure only — with the word "minutes" beneath. Later departures
  are not on the home card; they are one tap away as ETA cards. It keeps counting in minutes past an hour: a real
  device shows "71 minutes" (`sixcolors-01`).
- **Optional small glyphs:** wheelchair-status icon before the countdown and after the stop name when
  accessibility info is switched on (`sixcolors-01`); an alert triangle in a disc at the top-right of the line
  number (`help-96-01`; only red and yellow alerts surface on home); a pin badge on the card's top-right corner
  for pinned lines (`help-103-02`).

### 2.2 Real-time versus scheduled

| State | Rendering | Source |
|---|---|---|
| Real-time | numeral at full opacity + "two pulsating waves" at its top-right | help 445, `help-track-01` |
| Scheduled | same numeral "greyed out": a pale tint of the card colour, no waves | `help-track-01` (*sampled:* `#b8c8e8` on `#2858c8`) |
| Cancelled / skipped | not shown on the home card; shown on ETA cards (see §4.2) | `help-track-04…08` |

The only differences are opacity and a 8-pt glyph. Measured contrast of the scheduled numeral is 3.75 : 1 on
blue and **1.98 : 1 on orange** (`six-o-09`) — see §8.

### 2.3 Interaction

- **Tap** → route detail for that line, direction and stop (§4).
- **Swipe the card left/right** → the other direction (or another branch). Page dots at the top-centre of the
  card show how many there are; the card slides horizontally and the incoming one is shown at reduced opacity
  during the drag (`help-howto-02`).
- **Pin** (from the route screen's pin button) → the line "always display[s] at the top … unless you're far
  away", and you can opt into disruption notifications for it (help 103).
- **No in-place expanded state in 6.x.** The "expanded card" is the route detail screen. *Older versions expanded
  the card in place to show the next three departures — from memory, unverified.*

### 2.4 Colour

- **The card surface is the line's own colour, full-bleed.** There is no neutral card chrome at all; the list is
  a stack of colour blocks.
- **Text is white by default; black on light colours.** Yellow lines get black text and a black roundel
  (`appstore-iphone-s2`: NYC "R"; `sixcolors-02`: BART yellow). So a luminance rule exists, but its threshold is
  lenient: white is still used on mid-orange and light blue (*sampled contrast* 2.69 : 1 and 2.89 : 1, `six-o-09`).
- A very subtle top-to-bottom gradient and a hairline separate neighbouring cards.
- A "Show line colors" switch exists under Settings → Accessibility (help 98) for people who want it off.

### 2.5 Grouping, ordering, density

- **One card per line** (not per stop, not per departure). Direction is a property of the card, flipped by swipe.
- Order: pinned lines first; then nearby lines. *The exact sort key (walking distance vs. next departure) is not
  documented in anything I opened — unverified.*
- Other modes use the same slot with a different right-hand side: a bikeshare card has the operator logo, the
  nearest dock and an "Unlock a bike" pill instead of a countdown (`six-o-09`); an agency ticketing card has
  "Buy ticket" (`sixcolors-01`).
- **Density at launch: 3.4 cards** on a 390 × 844 screen (the first three fully, the fourth cut off, which signals
  scrolling). A real device with two-line headsigns shows 3 full cards plus a sliver (`sixcolors-01`).
- Non-subscribers: lines that are not close by are locked (crown marker); a reviewer describes "every visible
  route had a premium crown beside it" (§8).

---

## 3. Map

### 3.1 Home map (`six-o-09`, `help-howto-01`)

- Muted base map (cream land, white streets, pale green parks) so that line colours carry.
- The network's major lines are drawn as 3–4 pt strokes in their colours with small white stop rings — the
  auto-generated "transit map" layer, which can be switched off (help 107).
- **User location:** a solid blue dot (*sampled* `#007aff`) with a white ring, ⌀ ≈ 5 % W; a translucent accuracy
  halo when the fix is poor (help 90).
- Shared-mobility pins: teardrop pins with a white glyph, coloured per operator; a small lightning bolt marks
  electric vehicles.
- Avatar button top-left: ⌀ ≈ 16 % W (62 pt) including its white ring, gear badge ⌀ ≈ 6 % W at its lower right.

### 3.2 Route map (`help-track-03`, `help-howto-04`, `help-track-13`)

- **The whole screen is tinted with the line colour**: the base map is washed towards the line's hue and the
  content area below uses a 3 % tint of it (*sampled* `#fdf7fd` for a purple line).
- **Route line:** thick (≈ 2.5 % W, 10 pt) and saturated from your boarding stop onward in the direction of
  travel; thin and ~40 % opacity for the part before your stop. Stops are white dots on the line.
- **Your walk** from the blue dot to the boarding stop is a row of dark grey dots following the street.
- **Station entrances** (select cities): a rounded square in the line colour with a white "enter" arrow; the
  chosen entrance is larger and has a tooltip with the entrance name; the in-station path to the platform is
  drawn as dots in the line colour (`help-howto-04`, `help-howto-12`).
- **Detours:** the abandoned alignment is dashed with crossed-out stops; new stops are labelled "Temporary stop"
  in amber in the stop list (`help-track-13`).
- Floating round buttons, top-right, stacked: ✕ (red glyph), pin, bell, locate. Each ⌀ 10.3 % W (40 pt), white
  with a soft shadow, centre-to-centre 13.8 % W (54 pt).

### 3.3 Vehicle markers (`help-track-03`, `help-track-09`, `help-track-10`)

```
            ┌─────┐
       ┌────┤ 32s │   ← top-right badge: age of the last position ("32s"),
     ╭─┴──╮ └─────┘      OR a fanned stack of GO riders' emoji avatars
     │ )) │
     │ 🚌 │   ← white disc ⌀ ≈ 14 % W (≈ 55 pt) with soft shadow; vehicle glyph in the line colour;
     ╰─┬──╯      two small arcs above the glyph = "live"
      [●●○]   ← bottom badge: crowding pill, three person-dots (1/2/3 filled)
```

- The glyph depends on the mode (bus, tram, metro, train).
- The top-right badge is the trust signal: either *who* is providing the position (avatars = riders on board
  using GO) or *how stale* it is (seconds since the last agency update).
- Tapping a vehicle opens a small sheet: direction, **"1 stop away"**, "Next stop: School St / Main St", a
  countdown ("2 min"), two tiles ("Open seats", "Accessible"), and the provenance line "Bus 23-343. Updated 30
  seconds ago by Agency and Transit." (`help-track-10`).
- **Animation.** Agency feeds typically refresh every 15–30+ s; a GO rider's phone reports every 1–2 s, and
  Transit replaces the agency position with the crowdsourced one when available (blog 2018, 2025). The countdown
  waves are described as "pulsating". *Easing, interpolation between fixes and heading rotation are not
  documented — unverified.*

### 3.4 Zoom behaviour

- Route screen: framed to include you, your boarding stop and the next vehicle (consistent across all route
  screenshots; *the rule itself is inferred, unverified*).
- GO: "When your stop is near, Transit zooms in" (Six Colors; visible in `sixcolors-01`, third phone).
- The locate button re-centres. In GO it alternates with a "whole route" button (an S-shaped path glyph,
  `help-91-09`).

---

## 4. Line and stop detail

### 4.1 Layout (`six-o-11`, `help-howto-04`)

```
┌──────────────────────────────────────────┐
│ (😎)[4th]                           (✕)  │  leaderboard pill; round buttons ⌀ 10 % W
│                                     (📌) │
│  51        ← line number, ~72 pt,   (🔔) │  cap height 14.8 % W, in the line colour,
│              directly on the map    (➤)  │  no background plate
│                  ·                        │
│          (🚌)  ← vehicle marker           │  MAP, tinted with the line colour
│         ·                                 │  (≈ 45 % of screen height)
│  [● ○]                          ┌──────┐ │  page dots: swipe to change direction
│  ➜ West                         │  GO  │ │  GO: 22.6 % W × 15.5 % W (88 × 61 pt)
│┌─────────┐ ┌─────────┐ ┌───────  └──────┘ │
││   2 ))  │ │  10 ))  │ │  18 ))           │  ETA cards: 32 % W wide, 39 % W tall,
││ minutes │ │ minutes │ │ minutes          │  gap 3.2 % W, left inset 5.4 % W
││  [●●○]  │ │  [●●○]  │ │  [●●○]           │  → 2.75 cards visible
│└───╲╱────┘ └─────────┘ └───────           │  selected card has a pointed bottom edge
│ [★ 4.7] [⌛ 86%] [fare]  →                │  "route dashboard" chips, 11 % W tall, scrollable
│ ┃ 🚶 2 minutes                            │
│ ●  Édouard-Monpetit / Woodbury   9:19 AM  │  stop list on a 6.3 % W spine in the line colour
│ ┃  🚌 [119][368]                          │  connection badges under each stop
│ ┃ ─────────────────────────────           │
│ ●  Station Université-de-Montréal 9:21 AM │
└──────────────────────────────────────────┘
```

| Element | Measured (`six-o-11`) | pt @390 |
|---|---|---|
| Line number cap height → derived size | 14.8 % W → ≈ 72 pt | — |
| GO button | 22.6 % W × 15.5 % W, radius ≈ ⅓ of height | 88 × 61 |
| ETA card, with status row | 32.0 % W × 38.9 % W | 125 × 152 |
| ETA card, without status row (`help-go-04`) | 32.0 % W × 35.8 % W | 125 × 140 |
| ETA card gap / left inset | 3.2 % W / 5.4 % W | 12 / 21 |
| ETA card radius | ≈ 3.5–4 % W (*estimated by eye*) | ≈ 14–16 |
| ETA numeral cap height → size | 12.2 % W → **60 pt** (Transit's stated size; it was 18 pt in 5.0) | — |
| "minutes" under the numeral | ≈ 14 pt regular | — |
| Status row inside card (crowding pill or text pill) | 5 % W tall | 19 |
| Dashboard chip height | ≈ 11 % W | 43 |
| Stop-list spine width | 6.3 % W | 25 |
| Stop name / time | bold ≈ 18 pt dark ink (*sampled* `#1e212d`) / ≈ 14 pt grey | — |
| Stop row height | ≈ 18 % W (one line) to 27 % W (two lines + badges) | 70–105 |

### 4.2 ETA cards — the 6.0 centrepiece

"If Transit has one 'eureka' design idea, it's the big ETAs … so why not put ETAs front and centre when you look
elsewhere in the app?" (6.0 post). The same card is used on route detail, trip detail and GO (`six-o-13`).

- A horizontally scrolling rail of upcoming departures. The **selected** departure is a filled card in the line
  colour with white text, a few points larger than the others, with a shallow downward point on its bottom edge
  that visually attaches it to the content below. **Unselected** cards are white with line-coloured text and a
  soft shadow.
- Tapping another card selects that departure; the stop list times, and a running GO trip, follow the selection
  ("tap a specific departure to chase down a tight connection").
- Everything that qualifies a departure lives *inside* its card (`six-o-12`, `help-track-04…08`):

| Variant | Rendering |
|---|---|
| Real-time | numeral + waves; optional bottom row of small badges: ⚠ alert, crowding pill, ♿ |
| Scheduled | numeral and label at ~50 % tint, grey pill **SCHEDULED** |
| Cancelled | numeral struck through diagonally, pill **CANCELLED** |
| Skips this stop / Likely cancelled | struck-through numeral, pill **SKIPS THIS STOP** / **LIKELY CANCELLED** |
| Last departure | pill **LAST** |
| Different branch or alternative line | a header above the numeral: line chip ("55", "128 Local") or roundel + branch headsign ("E / Heath Street"), separated by a hairline |
| Walk instead | "I'd rather **walk** / 12 minutes" with a walking glyph |
| End of rail | "🕓 **More** departures" → full schedule |

- **Route dashboard chips** under the rail: alert chip first (amber fill, "⚠ Modified service" / "Stop moved"),
  then crowd-sourced rating (★ 4.7), on-time share (⌛ 86 %), fare, "Contactless", holiday service. Chips are a
  12 % tint of the line colour with line-coloured text (*sampled* `#f7e2f6` / `#820c80`, contrast 7.4 : 1).

### 4.3 Stop list

- Starts at your boarding stop (labelled with the walk time "🚶 5 minutes" or "➤ You are here"), continues
  downstream. Each row: stop name (bold), arrival time of the selected departure (right, grey), then a row of
  connection badges — a mode glyph followed by tiny line chips in *their* colours, "+" when truncated.
- Tap a stop: the ETA cards switch to that stop; "tap to see connections" (`help-howto-04`).

### 4.4 Full schedule (`six-o-08`, `help-151-11`)

- The screen background is the solid line colour; the header repeats number, direction and stop in white.
- Times are in white rounded panels, one panel per block of departures, rows ≈ 15 % W (58 pt) tall with hairlines
  (measured on `help-151-11`).
- Past and scheduled times are grey; **real-time rows are bold in the line colour with waves**, and the next
  departure has a small ▸ marker.
- A round floating button (bottom-right) compares real-time and timetable: the row becomes
  "9:19 AM ⟩⟩ scheduled 9:20 AM".
- Schedules are downloaded in the background and work offline (help 90).

### 4.5 Alerts (`appstore-iphone-s4`, help 96)

- Three severities by colour: red (significant disruption / stop closed), yellow (mild / stop moved), neutral
  (upcoming or informational). Only red and yellow reach the home card.
- Alert screen: line-colour background, a row "🔔 Alerts enabled — Mon–Fri: 8 AM to 10 AM, 5 PM to 7 PM", then one
  white card per alert: amber ⚠ + bold title ("Delays"), body, "Posted on …", "Source: MTA".
- Subscription is per line with a weekly time grid (default Mon–Fri 7–9 and 16–19), so alerts arrive only when
  you would actually ride.

---

## 5. Trip planner

### 5.1 Input (`six-o-07`, `help-howto-11`, `help-94-05`)

- Tapping "Where to?" opens the search screen: a brand-green header with a single field "Line or destination"
  and a swap/expand button; below it "Choose on map", then saved places as white cards (icon, name, address, "…"),
  then RECENT. The same field finds lines by number.
- The origin defaults to "Current location" and is only shown once results appear (two stacked fields, 72 % W
  wide × 12.75 % W tall, 2 % W apart, with a rail of start/end glyphs on the left and a swap button on the right).
- **Instant trip:** the right end of the home search bar is a shortcut to the predicted destination (home, work…)
  showing its travel time ("🏠 12 min"); one tap opens results (5.0 post).
- A white pill "Leave now" overlapping the header's bottom edge opens a sheet with a LEAVE AT / ARRIVE BY
  segmented control, a time wheel and a full-width "Find trips" button. Next to it: refresh; far right: red ✕.

### 5.2 Results: a shared timeline, not a list of text rows

```
┌──────────────────────────────────────────┐
│ ➤ │ Current location │                ⇅  │  brand-colour header, 47 % W tall
│ ■ │ Great Theatre    │                   │
│ (Leave now) (⟳)                      (✕) │
│  9:30 AM        9:45 AM        10:00 AM  │  time axis: 15 min = 37 % W  (1 min ≈ 2.5 % W)
│   ┊               ┊               ┊      │  faint vertical gridlines run through all rows
│   ● ● ●[     25      ]● ● ● ●            │  ride = chip in line colour, 10.5 % W tall;
│   Go in 4 min ))            26 min       │  walking/waiting = grey dots
│ ──────────────────────────────────────── │  row pitch ≈ 29 % W (112 pt)
│ ● ●[   B   ]●[   38   ]● ●               │
│ Go now ))              28 min            │  "Go in x min" at the trip's left end,
│ ┌──────────────────────────────────────┐ │  total duration at its right end
│ │ Find more trips                    › │ │
│ └──────────────────────────────────────┘ │
│ OTHER OPTIONS                            │
│ ●[████████ teal bar ████████]● ●         │  walk/bike/ride-hail as thinner bars (4 % W)
│ Bikeshare                    32 min  (≡) │  options button floats bottom-right
└──────────────────────────────────────────┘
```

- **Each itinerary is drawn to scale on a common time axis** (Transit calls them Gantt charts, 4.0 post). A ride
  is a rounded chip whose *length is its duration* and whose colour is the line colour, with the line number or
  roundel centred in white. Walking and waiting are rows of grey dots. Start position = when you must leave.
  Comparison is spatial: a shorter, further-left bar is the better trip.
- Under each bar: **"Go in 4 min"** with the minutes in green and waves when the first leg is real-time ("Go
  now" when you must leave immediately), and the total duration ("26 min") at the bar's right end. A fare chip
  ("$3.50") may follow the bar.
- Interchangeable lines are folded into one row with a small "or Ⓒ" above the chip (`appstore-iphone-s5`);
  identical trips at different times are grouped, with frequency, rather than repeated (4.0 post).
- Sections: transit first; "TRANSIT+" (transit combined with bike or ride-hail); "OTHER OPTIONS" (bike, walk,
  ride-hail with a price range). More results cost a subscription ("More trips", help 324).
- Results use real-time departures and include disruptions; offline they fall back to the schedule (help 90).

### 5.3 Trip detail (`six-o-14`, `help-howto-12`, `help-go-01`)

```
│            MAP: legs as thick coloured lines, mode badge on each leg,           │
│            green origin pin, red destination pin                                │
│                                                       ┌──────┐                  │
│ ┌─────────────────────────────────────────────────────┤  GO  │                  │
│ │ Leave at 9:26 AM                                     └──────┤  summary card:   │
│ │ Arrive at 9:54 AM                                   28 min  │  91 % W, ≈ 34 % W tall
│ │ ▮● ▬▬▬▬▬▬▬▬▬▬▬ ● ▬▬▬▬▬▬▬▬▬▬▬▬ ●▮                            │  bar 3 % W thick  │
│ └─────────────────────────────────────────────────────────────┘                  │
│  ┇  [🚶 2 minutes]                                   [ › ]   walk chip 10.5 % W tall
│  ┇  ┌───────────────────────────────────────────┐                                │
│  ┇  │ ➜  King St / Main St                      │   entrance card (where data exists)
│  ┇  │    Ⓑ Hermia St / 16th St                  │                                │
│  ┇  └───────────────────────────────────────────┘                                │
│  ┇  🚶 1 minute                                      [ › ]   walk to platform    │
│ ┌──────┐ ┌──────┐ ┌─────                                                         │
│ │ 3 )) │ │ 6 )) │ │ 8 ))    ETA cards for THIS leg (pick another departure)      │
│ └──╲╱──┘ └──────┘ └─────                                                         │
│ ┌──────────────────────────────────────────────┐                                 │
│ │ 🚋 Ⓑ                                          │  leg card: solid line colour,   │
│ │ ●  ➜ Puck's Pharmacy                          │  91 % W wide, radius ≈ 4 % W    │
│ │ ┃  Queen St / 12th St             9:29 AM     │                                 │
│ │ ┃  ⌄ 2 more stops before…                     │  collapsed intermediate stops   │
│ │ ●  (alighting stop)               9:41 AM     │                                 │
│ └──────────────────────────────────────────────┘                                 │
```

- **Walking legs are described only by duration**: a tinted chip "🚶 2 minutes" on a dotted vertical connector,
  with a "›" button that expands the walk. No distance, no street-level instruction, no side of the street.
  Where station-entrance data exists the walk is split into "to station" and "to platform" around an entrance
  card naming the entrance and its street corner. For alighting, an **exit card** can name the exit ("Exit NE —
  Flatbush Ave & Livingston St") with the connecting lines' bullets (`appstore-iphone-s6`).
- Tapping the walk chip opens a "Walking time" picker (a rail of minute tiles, the default marked DEFAULT); the
  choice is remembered for that walk and immediately shifts the "Go in…" time (`help-go-09`). A global walking
  speed lives in settings.
- Every transit leg has its own ETA-card rail, so alternatives are compared per leg, in place.

---

## 6. GO — live guidance

GO is "your personal transit companion" (onboarding, `help-howto-13`): a running trip that tells you when to
leave, counts stops, tells you when to get off or change, ends by itself, and meanwhile shares the vehicle's
position with riders downstream.

### 6.1 Starting it — three entry points

1. **From a planned trip:** trip detail → **GO** (`help-go-01`).
2. **From a line:** home card → route screen → **GO**; optionally tap an ETA card to choose the departure; then
   tap **"Set destination"** in the leg card and choose your stop from the stop list (`help-go-03`, `help-go-04`).
   Without a destination GO still tracks and crowdsources; with one it can tell you when to get off.
3. **AutoGO** (2025): on opening the app, Transit guesses which nearby vehicle you are on and shows a floating
   card over the home list — "🚌 **Riding the [12]?** Get notified when your stop is approaching" with a GO
   button (`blog-autogo-prompt`). Over 1 M trips had been started this way by mid-2025 (blog).

Limits: GO can only start for trips leaving within 60 minutes, and not for multimodal trips (help 549).

The GO button is the loudest control in the app: a rounded square in the line colour, 22.6 % W × 15.5 % W,
"GO" in heavy italic white capitals, docked at the right edge above the ETA cards (route screen) or biting into
the top-right corner of the summary card (trip detail).

### 6.2 "I am already on it" — how the app learns your vehicle

- **You never pick a vehicle by ID.** You pick the *line* (or accept AutoGO's guess), tap GO, and "wait a few
  moments and Transit will detect that you're on board. It doesn't matter if the departure listed isn't the one
  you're on" (help 549).
- GO "detects whether you're on a vehicle or walking"; once on board "it dismisses all other scheduled (or
  real-time) departure times" and shows only your trip (help 549).
- The detection is a motion classifier on phone sensors (walking ≈ 2 Hz, riding a train ≈ 5 Hz vibration
  signature) combined with location, last known fix and the timetable; underground it predicts position between
  stations without GPS, on-device, and is right "90 % of the time" (blog 2024).
- The selected departure can be changed by tapping another ETA card "before or after starting GO".

### 6.3 The screen: one sentence, one bar, one card

Every stage uses the same skeleton (`help-go-04`, `help-91-09`):

```
┌──────────────────────────────────────────┐
│            [ 😊 326 ]                (✕) │  riders-helped pill (tap → stats / leaderboard)
│          ┌──────────┐                (🔔)│  ✕ = minimise, 🔔 = GO settings,
│          │ ARRIVE AT│                (⤳) │  third = whole route / recentre
│          │  5:38 )) │                    │  arrival pill: 28 % W wide, time in line colour
│          └──────────┘                    │
│              MAP (line colour wash,      │  map ≈ top 30–40 % of the screen
│              route, vehicle, you)        │
│                                          │
│         Get off in 4 stops               │  HEADLINE: bold ≈ 28–30 pt, centred, dark ink,
│        until School St / 29th St         │  cap height 5.7 % W; sub-line regular ≈ 17 pt
│  ● ● ▬▬▬▬▬▬▬(😎)▬▬▬▬▬▬▬▬▬▬▬ ● ● ▮        │  PROGRESS BAR: 3.1 % W (12 pt) thick, one segment
│                                          │  per leg in its colour, dots for walking,
│ ┌──────────────────────────────────────┐ │  avatar puck ⌀ 8.5 % W (33 pt) = you
│ │ 🚌 38                                 │ │
│ │ ┃  At stop:                           │ │  LEG CARD: solid line colour, 91 % W,
│ │ ●  School St / 41st St      5:27 PM   │ │  radius ≈ 4 % W; current/next stop, collapsed
│ │ ┃  ⌄ 3 more stops to…                 │ │  middle, destination stop with times
│ │ ●  School St / 29th St      5:32 PM   │ │
│ └──────────────────────────────────────┘ │
│  ┇  [🚶 6 minutes]                 [ › ] │  what comes after this leg
└──────────────────────────────────────────┘
```

Measured on `help-go-04` (screen 992 px wide): headline cap height 5.7 % W; progress bar 3.1 % W thick ending
6.25 % W from the right edge; avatar puck ⌀ 8.5 % W; walk chip 10.5 % W tall; ETA cards 32 % W × 35.8 % W; leg
card 91.2 % W wide (4.3 % W side margins); arrival pill 28 % W wide; round buttons ⌀ 10.3 % W.

### 6.4 Stages

Headlines are quoted from screenshots; notification texts from help 549 and the onboarding cards.

| # | Stage | Headline (big) | Sub-line / what else changes | Notification |
|---|---|---|---|---|
| 1 | Before leaving | **"Go in 4 minutes"** / "Leave in 2 minutes" | progress bar empty, puck at the far left; walk chip; ETA-card rail for the first leg (selected + alternatives); leg card shows boarding stop and "⌄ 9 more stops before…" | reminder N minutes before (default 5, editable): "Go in … minutes" |
| 2 | Time to go | **"Leave now"** | same layout | "Leave now"; **"Hurry up!"** if you risk missing it (GO tracks your walking pace against the vehicle) |
| 3 | At the stop | **"Wait for the [38]"** (line chip inline in the sentence) | puck at the start of the leg segment; ETA cards still visible; vehicle approaching on the map with its "32s" badge | — |
| 4 | On board | **"Get off in 7 stops"** | "at Workman Ave / 25th St"; ETA cards disappear; leg card switches to "Next stop: … 3:35 PM" / "At stop: …"; the travelled part of the bar turns pale behind the puck; pill on top now counts riders helped | "5… 4… 3… 2 more stops" |
| 5 | One stop to go | **"Your stop is next!"** | the stop name alone as sub-line; map zooms in | "Your stop is next!" |
| 6 | Arriving | **"This is your stop!"** | puck at the end of the segment | "This is your stop!" |
| 7 | Transfer | (returns to 1–3 for the next leg) | below the finished leg card: dotted connector, walk chip, exit card ("Exit NE …"), then the next leg | "… when it's time … to change lines" |
| 8 | Arrived | — | GO ends by itself; Live Activity dismisses; next app open shows **TRIP SUMMARY** (distance, time, "You've helped 476 riders on this GO trip", button "NICE!") and a rate-my-ride prompt | "You have arrived" |

Wireframes of the stage-specific parts (same skeleton as §6.3):

```
1–2  BEFORE LEAVING                         3  AT THE STOP
     Go in 4 minutes                           Wait for the [38]
 (😎)● ▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬ ● ● ● ▮              ● (😎)▬▬▬▬▬▬▬▬▬▬▬▬▬▬ ● ● ▮
  ┇ [🚶 4 minutes]            [ › ]         ┌──────┐ ┌──────┐ ┌────
 ┌──────┐ ┌──────┐ ┌────                    │ 2 )) │ │ 8 )) │ │ 13
 │ 8 )) │ │ 17)) │ │ 29                     └──╲╱──┘ └──────┘ └────
 └──╲╱──┘ └──────┘ └────                    ┌───────────────────────┐
 ┌───────────────────────────┐              │ 🚌 38                  │
 │ 🚌 25                      │              └───────────────────────┘
 │ ● ➜ Eastbound to Theatre   │
 │ ┃ Main St / Demetrius  9:35│           4  ON BOARD
 │ ┃ ⌄ 4 more stops before…   │              Get off in 5 stops
 │ ○ [ Set destination ]      │              at Lafayette Av / Classon Av
 └───────────────────────────┘              ● ▬▬▬(pale)▬▬(😎)▬▬▬▬▬▬▬▬ ● ▮
                                            ┌───────────────────────┐
5  NEXT STOP                                │ 🚌 B38                 │
     Your stop is next!                     │ ● Next stop:           │
     Nevins St                              │   Lafayette / Carlton  4:11 PM
 ● ▬▬(pale)▬(😎) ● ● ▬▬▬▬▬▬▬▬▬ ● ▮           └───────────────────────┘
 ┌───────────────────────────┐
 │ 🚇 ③  Next stop:           │           6  THIS IS YOUR STOP
 │ ● Nevins St        4:01 PM │              This is your stop!
 └───────────────────────────┘              Broadway / 12th Street
  ┇ [🚶 2 minutes]        [ › ]             ● ● ● ● ▬▬▬▬▬▬▬▬▬▬▬▬▬▬(😎)
 ┌───────────────────────────┐              [⚠ Reduced service] [holiday]
 │ ➜ Exit [NE]   ②③④⑤         │              🚌 12  Next stop: Broadway / 12th
 │   Flatbush Av & Livingston │
 └───────────────────────────┘  ← 7 TRANSFER: walk chip + exit card, then the next leg
```

### 6.5 Notifications, voice, lock screen

- **Principle:** "Instead of sending multiple notifications throughout your trip, your phone will wake only to
  alert you when it's time to take action, like 'Leave now' or 'Get off in 2 stops'" (help 549).
- **GO Settings sheet** (`help-go-08`, bell button): *Send reminder* ("Get a notification [5 minutes] before you
  need to leave", lead time editable inline), *Voice notifications* (speak all notifications), *Headphones only*,
  *Voice* (system TTS voices), *Rate-My-Ride* on/off. First run offers "Use GO without notifications".
- **Lock screen** (`help-go-05`; iOS 16.1+ Live Activity, Android 11+ "Live Notification"):

```
┌──────────────────────────────────────────────┐
│ [38]  2 more stops                           │  line chip (rounded square ≈ 36 pt) + bold ≈ 22 pt
│       until Workman Ave / Pyramus St         │  regular ≈ 15 pt
│ ▮● ▬▬▬▬▬▬▬▬▬ ● ▬▬▬▬▬(😎)▬▬▬ ● ▮              │  same segmented bar (≈ 12 pt) and avatar puck
│ Arrive at 9:54 AM                     9 min  │  footer: arrival left, remaining time right
└──────────────────────────────────────────────┘   ≈ 364 × 138 pt; iOS tints it with the line colour
```

- **Dynamic Island** (`help-go-06`): compact = line chip on the left, "● 2" (stops remaining) on the right;
  expanded = the lock-screen layout. "If you need to get off soon or hurry to catch your ride, the Dynamic Island
  will get larger to catch your attention."
- **Apple Watch** notifications mirror the phone (Six Colors); a watch app shows nearby departures (blog 2019).
- **Haptics:** nothing in the sources describes vibration patterns — *unverified*.
- Screen readers: Live Activities "support VoiceOver and TalkBack"; route names, stops and durations are
  "condensed into clear sentences" (help 98).

### 6.6 Minimising

The red ✕ (or swipe down / Android back) does **not** end the trip; it minimises it. A scrim labelled MINIMIZE
appears during the gesture, and the trip becomes a **minibar** floating above the home list (`help-go-07`):
≈ 91 % W × 34 % W, solid line colour, "🕓 **Go in 4 minutes** ))", "[25] in 8 minutes", the progress bar with the
puck, "Arrive at 9:57 AM … 26 min". Tap to return. Rate-My-Ride questions are suppressed while minimised.

### 6.7 When things go wrong

- **Missed ride or transfer:** "GO will update your itinerary and give you an adjusted ETA. We'll even compare
  arrival times between express routes and local ones, and tell you which to take" (4.0 post); onboarding says GO
  "reacts to missed transfers or unplanned detours — even when the app is closed". The visible mechanism in 6.x
  is that the selected ETA card moves to a later departure and the arrival pill updates. *I found no screenshot
  of a dedicated "you missed it" state — its exact presentation is unverified.*
- A current reviewer experiences this as a defect: "Keeps moving me from the bus I chose to the later bus making
  me late if I'm not consistently paying close attention as the notifications are useless" (App Store CA,
  2026-10-20).
- **Detours:** alert notification; detoured route and temporary stops drawn on the map (§3.2).
- **Bikeshare (6.3.7):** "if your destination dock runs out of slots? We'll reroute you on the fly to a different
  dock" (release notes).
- **Offline:** GO starts from the schedule and still alerts by GPS position (help 90).

### 6.8 Crowdsourcing and the game layer

- While you ride with GO your phone reports the vehicle position every 1–2 s; other riders see that vehicle with
  your emoji avatar on it. In bus-heavy cities GO covers up to 65 % of vehicle trips (blog 2025).
- Opt-in, anonymous, "your exact position is never shared with other riders", stops at the destination; ≈ 5 %
  battery and < 100 kB for a 20-minute trip (help 91).
- Motivation is designed in: a counter of riders helped on the GO screen, per-line monthly leaderboards (rank
  pill "4th" on every route screen), in-app thank-yous from downstream riders, a random emoji + two-word
  nickname per user (custom ones with a subscription). "20 % of Transit riders say they use GO specifically for
  the gamification features" (blog 2025).
- **Rate-My-Ride:** one-tap questions inline between the progress bar and the leg card ("How many open seats do
  you see on this bus?" — "Lots of open seats / Few if any seats / Packed like sardines", BACK / SKIP). The
  answers become the crowding pills and ★ / ⌛ chips others see. 10 M answers a month (blog 2025).
- GO trips can be shared by link; followers see live location, ETA and legs (help 549).

---

## 7. Visual language

### 7.1 Colour

| Role | Light | Dark ("Neon dark mode") |
|---|---|---|
| Line surface (home card, selected ETA card, leg card, schedule background) | the line's own colour, full saturation (*sampled* purple `#781b7d`, orange `#f37e00`, blue `#00a2e1`, red `#e9473f`) | a near-black tint of the same hue (*sampled* `#200828`, `#201000`, `#001820`, `#280808`) |
| Text on line surface | white; black on light colours | the vivid line colour itself (*sampled* `#d018d0`, `#f07800`, `#0098e0`, `#e84038`) |
| Selected ETA card | line colour, white text | "neon": brightened line colour (`#d030d0`), white text |
| Unselected ETA card | white, line-coloured text | mid-dark tint (`#681068`), pale text |
| Detail-screen background | ≈ 3 % tint of the line colour (`#fdf7fd`) | ≈ 15 % (`#280828`) |
| Chips | ≈ 12 % tint, line-coloured text | mid-dark tint, pale text |
| Neutral ink / secondary | `#1e212d` / mid grey | white / grey |
| Brand accent (search bar, planner header, favourites, "Go in x min") | green (*sampled* `#2db266`) | deep green (`#186838`) |
| Status | amber alert chip; red ✕ for close; grey pill for SCHEDULED/CANCELLED | same |
| User location | iOS blue `#007aff` | same |

- Dark mode is not an afterthought: "more than 50 % of our users use Transit in its Dark Mode setting — a number
  which rockets to 75 % once the sun goes down". Backgrounds are "monochromatic midnight tones" produced by "a
  new smart, programmatic colour picker that uses your local agency's route colours as a reference"; the
  algorithm itself has not been published (6.0 post, METRO).
- Because the line colour takes over the whole screen, each line detail and each GO trip has its own colour
  identity; the brand green appears only where no line is in play.

### 7.2 Typography

- **Typeface: Puffin Transit** — a custom cut of Bold Monday's *Puffin* by Pieter van Rosmalen, with plainer
  "3" and "4" and reworked French accents. It replaced *Interstate* (used for over a decade) because Interstate,
  a highway-signage face, was not "evocative of the car-free cities we dream of". Brief: "friendly, round,
  skimmable, charismatic, yet elegantly inconspicuous" (6.0 post).
- **Three jobs, three weights:** heaviest weight for numerals and line numbers; bold for headings, directions
  and stop names in lists; regular for secondary lines. Heavy *italic capitals* are reserved for the game layer
  and GO ("GO", "TRIP SUMMARY", nicknames, rank pills).
- **Scale (pt on 390 W, derived):** route title ≈ 72 · ETA-card numeral 60 · home line number ≈ 44 · home
  countdown ≈ 40 · GO headline ≈ 28–30 · direction on route screen ≈ 24 · home direction ≈ 19 · stop names
  ≈ 15–18 · unit labels ≈ 11–14 · pill labels ≈ 11 bold caps.
- The numerals are wide, with round counters and soft terminals; a single digit at 60 pt fills a third of a
  125-pt card.
- 6.0 "added more whitespace and boosted font sizes" throughout and improved Dynamic Type handling for low-vision
  users (6.0 post, METRO).

### 7.3 Shape and elevation

- Home cards: square, edge to edge. Everything else: generously rounded — floating cards ≈ 4 % W (16 pt) radius,
  chips ≈ 2.5 % W (10 pt), pills fully round, round 40-pt map buttons.
- Soft, wide, low-opacity shadows under white floating elements (returned in 5.0: "shadows have made a comeback").
- Thick strokes: 12-pt progress bars, 10-pt route lines, a 25-pt stop spine. Nothing is hairline except dividers.
- Walking is always dots; riding is always a solid bar. This holds on the map, the planner, the progress bar and
  the lock screen.

### 7.4 Iconography

- Solid, rounded glyphs: mode icons (bus, tram, metro, train) front-on; walking figure; arrow-in-circle for
  direction; warning triangle; hourglass (on-time), star (rating), coins (fare), contactless.
- Wheelchair in the "active" pose with three states: solid = accessible, with "?" = unknown, struck = not
  accessible (blog 2018).
- Crowding: three little person-dots in a pill.
- Real-time: two concentric quarter-arcs.

### 7.5 Motion and play

- Documented: pulsating real-time waves; horizontal card swipe with page dots; the scrim-and-shrink minimise
  gesture; the Dynamic Island growing for urgent steps.
- Playful layer: emoji avatars and generated nicknames, confetti-like avatar clouds, leaderboards with podium,
  a jokey copy voice ("Packed like sardines", "NICE!").
- *Durations, easing curves and marker interpolation are not documented in any source I opened — unverified.*

---

## 8. What works, and what frustrates users

### Works

- **Answer on launch.** Reviewers and Transit agree this is the product: "Transit has always been best as a
  'live' app, the kind you want by your side when you need to know if you've missed the bus" (Six Colors, 2026).
- **Big ETA cards.** "What's new are the big, bright boxes that tell you how long you need to wait … It's also
  easier to scroll a list of stops your vehicle will make, because the list is bigger and bolder" (Six Colors).
- **Get-off guidance.** "It notifies you when its time to get off the bus and leads you to the next stop if
  needed" (App Store CA, 5★, 2026-11-02); "Transit also excels when you're on a train or bus, watching for a
  stop" (Six Colors); Dynamic Island support is called out by name in a 5★ review.
- **Colour and character.** "I really love how intuitive and fun this app is to use with all the colours"
  (App Store CA, 2026-11-16).
- **Questions asked in-screen, not by push** — "which feels like a nice balance" (Six Colors).
- Scale: 4.6★ from 1.04 M ratings (App Store US lookup, 2026-11-21); used by over 20 % of US/Canadian transit
  riders monthly (METRO, company figure).

### Frustrates

I classified the **300 most recent App Store reviews** (US + CA, 2026-09-27 … 11-18; 196 of them ≤ 3★ — the
recent-reviews feed is far more negative than the lifetime 4.6★ average, so read these as *themes*, not rates).
Keyword matches among the 196 low-star reviews:

| Theme | Reviews | Typical complaint |
|---|---|---|
| Wrong or vanishing times ("ghost buses") | 69 | "it says the waiting time is 12 mins but then you see the bus pulling over"; "keeps pushing the time back 1 min at a time"; the countdown jumps to the next bus while the current one is still coming |
| Subscription / paywall | 28 | "You have to pay to see the bus schedules for any line not in your immediate vicinity"; "a huge Royale promotion took up much of the screen, and every visible route had a premium crown beside it" |
| Changes after updates / UI | 29 | mixed with accuracy complaints; iPad layout; "preferences … a little hard to find for the beginner" (Six Colors) |
| GO / notifications | 19 | silent switch to a later bus; GO crash; "I don't use the GO feature because I literally lose my tickets that are on my phone" (battery) |
| Nagging | few | "Terrible quiz at the start. Can't get past without choosing an option"; "Incessantly asks for ratings" |

Other evidence:

- **Paywall on public data.** Pittsburghers for Public Transit: non-paying users "will no longer have access to
  bus departure times if the stop is outside of a few block radius … riders should have access to our public
  data". Search snippets (pages not opened) report RTD Denver and BC Transit ending sponsored subscriptions in
  2025.
- **Trust depends on the feed.** Most 1★ reviews blame the app for agency data. Transit's answer is provenance
  in the UI (waves, "32s" badge, "Updated 30 seconds ago by Agency and Transit", SCHEDULED / LIKELY CANCELLED
  pills) — but on the *home card* the only cue is opacity.
- **Contrast.** *Sampled* ratios: white on orange 2.69 : 1, white on light blue 2.89 : 1, white on the brand
  green 2.74 : 1, scheduled numeral on orange 1.98 : 1. Large numerals need 3 : 1 and small text 4.5 : 1 (WCAG
  AA), so line names, stop names and the "scheduled" state fail on mid-luminance colours.
- **Countdown without a clock time** on the home card ("71 minutes") forces mental arithmetic for long waits.
- **No walking distance or stop position on the card**; walking legs are a bare duration.
- **Cardinal headsigns** ("North", "West") are a North American convention and mean little elsewhere.

---

## 9. Recommendations for Kante

### 9.1 Adopt — ranked

1. **Departures on launch, map above, never behind a tap.** Map in the top ≈ 44 % of the viewport, list below,
   search bar (87 % W × 58 pt, 9-pt overlap onto the list) on the seam within thumb reach.
2. **Full-bleed colour cards with two loud elements.** Card height 29 % W (113 pt), 14-pt left padding; line
   number ≈ 44 pt heaviest weight top-left; countdown ≈ 40 pt right, vertically centred, 29 pt from the edge;
   direction 19 pt bold; stop 15 pt. Keep the 44 : 40 : 19 : 15 : 11 ratio. Target 3.4 cards on first paint.
3. **The ETA-card rail** on line, stop and trip detail: cards 32 % W × 36–39 % W (125 × 140–152 pt), 12-pt gap,
   2.75 visible, 60-pt numerals, selected card filled with the line colour. Put *all* per-departure qualifiers
   inside the card as text pills (delayed, cancelled, skips this stop, last, other branch).
4. **GO's one-sentence screen** for the journey and on-board modes: a single imperative headline (28–30 pt), a
   12-pt segmented progress bar with a position puck, and one solid leg card that shows only "next stop … /
   n more stops … / your stop". Same skeleton for every stage; only the sentence and the card contents change.
5. **Stage machine with fixed sentences:** leave in n min → leave now → wait for [line] → get off in n stops →
   your stop is next → this is your stop → (change) → arrived. Reuse the same sentence for the notification.
6. **Notify only on action** (leave, hurry, 2 stops left, next stop, now), with an editable lead time (default
   5 min) and optional speech / headphones-only.
7. **Minimised-trip bar** floating over the home list (91 % W × ≈ 130 pt): next action, countdown, progress bar,
   arrival time. Closing the guidance screen must never end the trip.
8. **"Riding the 12?" prompt.** When the app opens and the user is moving along a line, offer the on-board mode
   in one tap; otherwise pick the line and let detection settle. Do not ask for a vehicle number.
9. **Timeline results** on a shared time axis (1 min ≈ 2.5 % W; ride chips 41 pt tall in the line colour, dots for
   walking, "Leave in x min" at the left end, duration at the right end, ≈ 112-pt row pitch).
10. **Per-leg alternatives in place:** each leg of a trip carries its own ETA-card rail, so a tight connection
    can be re-chosen without re-planning.
11. **Line-tinted detail screens:** 3 % tint as page background, 12 % for chips, the full colour for the leg card
    and the selected departure; tint the map as well.
12. **Provenance on the vehicle marker:** age of the position in seconds as a badge; tap for "1 stop away / next
    stop / updated 30 s ago by …".
13. **Swipe to flip direction** with page dots on the card — plus a visible affordance (see 9.3).
14. **Dark mode designed per line:** near-black tint of the line hue as surface, vivid line colour as text.
15. **Walk chip with adjustable walking time**, remembered per walk, shifting the "leave" time immediately.

### 9.2 Avoid

- White text on mid-luminance colours and opacity-only "scheduled" states (measured 1.98–2.9 : 1).
- Signalling real-time versus timetable by an 8-pt glyph alone.
- Silently re-binding a running trip to a later departure. Say "You will miss the 14:32 — next one 14:47" and let
  the user confirm or re-plan.
- Countdown-only for long waits. Switch to clock time beyond ≈ 20–30 min, and always show the clock time small.
- Locking nearby or network-wide timetable data, crown markers on cards, upsell banners on the first screen.
- Start-up quizzes, rating prompts, and surveys inside the guidance screen.
- A stack of modal screens that can only be left by ✕: on the web every screen needs a URL and must obey the
  browser back button.
- Settings that matter for routing (walking speed, step-free, modes) buried in a profile screen.

### 9.3 Where Kante can clearly do better

- **The exact place to stand is Kante's headline, and Transit has no equivalent.** Transit names the closest
  stop and, in a few cities, a station entrance. Kante knows the bay / platform edge and the side of the street,
  so:
  - *Home card:* add a bay chip on the stop row — "Bahnhofplatz · **Kante C**" — and the walk ("2 min · 140 m").
    Transit shows neither.
  - *Stage 3 of guidance* becomes the differentiator: headline "**Stand at Kante C**", sub-line "far side of the
    street · 40 m to your left", with a zoomed map of the stop showing the bays and the one to use highlighted.
    Transit's stage 3 only says "Wait for the 38".
  - *Walking legs:* replace the bare "2 minutes" chip with "2 min · 140 m · cross Seestrasse · Kante C on the
    lake side".
  - *Transfers:* "Change: Kante A → Kante D, 90 m, 3 min — you have 5", coloured by margin.
- **Trust on the home card.** Use a text label as well as a glyph for the timetable state, and show delay as a
  delta ("+3").
- **Countdown plus clock:** "4′" large with "14:32" beneath, replacing the word "minutes".
- **Direction as terminus name**, which is what Swiss vehicles display; never cardinal directions.
- **Both directions visible** where space allows (a small secondary countdown for the opposite direction), since
  swipe-to-flip is undiscoverable for new users.
- **Stops as first-class objects** (Transit has only lines): a stop page grouping departures by bay.
- **No account, no gamification** needed for on-board mode: Swiss real-time feeds make crowdsourcing unnecessary,
  which removes the leaderboard, avatars and survey layer entirely and leaves a calmer screen.

### 9.4 A line-colour strategy for Swiss data (no per-line colours in the feed)

Goal: the same bold colour-block feel, with every line keeping one stable colour everywhere, and all text
passing contrast.

**a. Palette.** Thirteen surface colours with a fixed text colour each. Contrast computed for this study
(WCAG 2 relative luminance). "Tint" is the 12 % wash for chips and page backgrounds; "dark" is the dark-mode
surface with its text colour.

| Name | Surface | Text on surface (ratio) | Tint | Dark surface / text (ratio) |
|---|---|---|---|---|
| red | `#C8322B` | white (5.3) | `#F8E6E6` | `#2E1415` / `#E6908C` (7.1) |
| rust | `#B5490A` | white (5.4) | `#F6E9E2` | `#2A180F` / `#F58C4E` (7.1) |
| amber | `#F2B400` | **ink `#14161A`** (9.8) | `#FDF6E0` | `#352B0D` / `#F2B400` (7.5) |
| olive | `#5B7A00` | white (5.0) | `#EBEFE0` | `#1A210D` / `#8CBC00` (7.4) |
| green | `#1B7F3B` | white (5.1) | `#E4F0E7` | `#0F2218` / `#29C25A` (7.1) |
| teal | `#007A78` | white (5.2) | `#E0EFEF` | `#0A2123` / `#00BCB9` (7.1) |
| azure | `#0B72B5` | white (5.1) | `#E2EEF6` | `#0C1F2E` / `#47B0F4` (7.0) |
| blue | `#2456C8` | white (6.5) | `#E5EBF8` | `#101A31` / `#87A5E9` (7.1) |
| indigo | `#4B3FB5` | white (7.8) | `#E9E8F6` | `#17162E` / `#A39CDD` (7.0) |
| violet | `#7B2D9B` | white (7.8) | `#EFE6F3` | `#201329` / `#C891DF` (7.2) |
| magenta | `#B4237A` | white (6.1) | `#F6E5EF` | `#2A1123` / `#E784BF` (7.0) |
| brown | `#7A4A2B` | white (7.4) | `#EFE9E6` | `#201815` / `#D09B79` (7.2) |
| slate | `#3D4A5C` | white (9.0) | `#E8E9EB` | `#15181E` / `#97A5BA` (7.1) |

Every pair is ≥ 4.9 : 1, so even the 15-pt stop name passes AA. Line-coloured text on its own tint is ≥ 4.25 : 1:
use it at ≥ 18 pt bold only, and use ink for small text on tints. Amber text on its tint fails (1.7 : 1) — use ink.
These are a starting set, not Kante's brand colours; shift hues to sit well next to Kante's own accent.

**b. Assignment, in priority order.**

1. **Curated override** `(operator, line) → palette entry or exact colour`, for networks whose riders already
   know their lines by colour (several Swiss city networks print coloured line bullets on their maps — *from
   memory, unverified; build the table from the operators' published network maps*). Snap any official colour to
   pass the contrast rule by darkening it, never by switching text to grey.
2. **Mode default** where colour does not identify the service: long-distance and regional trains (IC, IR, RE, EC
   …) → *slate* with the category as the big label ("IR 36"); boats → *teal*; funiculars and cableways → *brown*;
   night lines → *indigo* with a moon glyph.
3. **Deterministic pick for everything else** (tram, bus, S-Bahn). For numeric lines use
   `index = (n × 5) mod 12` over the twelve non-slate colours in table order (red = 0 … brown = 11) — 5 is
   coprime with 12, so consecutive numbers land far apart on the wheel (1 → teal, 2 → magenta, 3 → olive,
   4 → indigo, 5 → rust, 6 → azure). For non-numeric names use a stable string hash.
4. **De-collision at build time, not at run time.** Build a graph of lines that share a stop (per operator
   network), and where two neighbours got the same index, move the less frequent one to the nearest free index.
   Store the result with the data so a line has the same colour on every device and every day.

**c. Rules of use.**

- Text colour comes from the table, never from a run-time luminance test.
- Timetable-only departures keep full-contrast text; mark them with a clock glyph and a label, not with opacity.
- Mode is carried by a glyph beside the line number, so colour never has to encode mode on its own.
- Offer "plain cards" in accessibility settings (neutral surface, a coloured bar on the left edge).

### 9.5 Brand-specific — must NOT be copied, and what to use instead

| Transit's own | Why it is theirs | Generic way to get the effect |
|---|---|---|
| The name "Transit", its wordmark, and the app icon / notification glyph (green rounded square with a white S-shaped path) | trade marks | Kante's own name and mark |
| **Puffin Transit** typeface (and Interstate before it) | custom, commercially licensed cut made for Transit | any open-licensed, slightly rounded sans with a heavy weight and wide tabular numerals; test numerals at 60 pt first. *Candidates to evaluate (not verified here): Figtree, Outfit, Manrope, Nunito Sans* |
| The brand green (*sampled* `#2DB266`) as primary for search bar and planner header | brand colour | Kante's own accent in the same roles |
| "GO" — the feature name and the heavy-italic "GO" lozenge button | product branding | a plainly labelled primary button ("Start", "Los", "Ich fahre mit") in Kante's style |
| The pointed-bottom ("pennant") selected ETA card | distinctive signature shape | filled card with a border or a small notch-free indicator underneath |
| The two-arc real-time glyph in exactly that form and position | recognisable Transit detail (the *idea* of a live indicator is generic) | a pulsing dot, or Kante's own live mark, plus a text label |
| Emoji avatar + generated nickname, rank pills, "Top Contributors" leaderboards, "riders helped" counters | product identity and game system | none needed; if a position puck is wanted on the progress bar, use a plain dot or the vehicle glyph |
| "Royale" (name, crown), "Rate-My-Ride" (name), "Nearby" as a product term, "Neon Dark Mode" | product names | descriptive labels |
| Copy voice and specific strings ("Packed like sardines", "NICE!") | editorial identity | Kante's own tone; the *functional* sentences ("Get off in 3 stops") are ordinary language |
| Illustrations, mode icon drawings, map style | artwork | own icon set and map style |

Generic and safe to adopt: launch-to-departures layout, full-bleed colour cards, oversized numerals, horizontal
departure cards, timeline results, a segmented progress bar, a single-instruction guidance screen, tinting a
detail screen with the line colour, action-only notifications, a minimised-trip bar.

### 9.6 Notes for a web app

- Live Activities and the Dynamic Island are native-only. The web equivalents to evaluate are: Web Push
  notifications that replace each other by tag, the Screen Wake Lock API for the on-board screen, and the
  Vibration API. *Current browser support (notably on iOS) is from memory, unverified — check before designing
  around them.*
- Swipe-down-to-dismiss conflicts with pull-to-refresh and browser gestures; rely on a visible close control and
  history navigation.

---

## 10. Not verified

Stated in the text as unverified; collected here.

- How the home list scrolls over the map (snap points, whether it can cover the map fully).
- Sort order of Nearby cards beyond "pinned first".
- Whether the search bar still turns purple when the map is panned away from the user (documented for 5.0, 2018).
- In-place card expansion in pre-5.0 versions.
- Vehicle-marker animation (interpolation, heading), all durations and easings, map auto-zoom rules.
- Haptic patterns in GO.
- The presentation of a missed connection (no screenshot found); only the behaviour is described by Transit.
- The dark-mode colour algorithm (announced, not published).
- Corner radii (estimated by eye) and all font sizes other than the stated 60 pt (derived from cap heights).
- Android-specific layout differences beyond the lock-screen notification and back gesture.
- The distance beyond which lines are locked for non-subscribers ("a few block radius" per a third party).
- Which Swiss operators have rider-recognised line colours; browser support for the web APIs in §9.6; the
  suitability of the suggested open-licensed typefaces.
- RTD Denver / BC Transit subscription changes and the Reddit thread: known from search-result snippets only.
- I did not run the app; everything is from published screenshots and text. Marketing mock-ups may differ from
  the shipping app in details; the two real-device screenshots (Six Colors) agree with them on layout.
