# SBB Mobile – design study for Kante

Researched 2026-11-21. Subject: SBB Mobile for iOS/Android, current store version 12.61.0
(released 2026-11-18). Scope: journey planning, results, connection detail, departure
board, map, journey companion. EasyRide, ticket purchase and SwissPass are out of scope.

Images are in [`sbb/`](sbb/), indexed with their URLs in [`sbb/sources.md`](sbb/sources.md).
File names in `code` below refer to that folder.

## How to read the numbers

**Unit.** `pt` means one logical pixel (iOS point, Android dp, CSS px). Horizontal
positions are given for a 390 pt wide screen; `sw` is screen width, `sh` screen height
(844 pt for the percentages).

**Evidence tags.**

| Tag | Meaning | Accuracy |
|---|---|---|
| **[T]** | Token read from SBB's open-source mobile design system (`design_system_flutter`). The app is native, not built from this package, but the screenshots match these values wherever I could check. | exact |
| **[M360]** | Measured on a native Android screenshot, 1080 px = 360 dp (`community-33347-03.jpg`, Jan 2025). | ±0.5 pt |
| **[M]** | Measured on SBB's own screenshots and video frames, scaled so the selected tab circle is 44 pt (which makes those frames 390 pt or 430 pt wide). | ±1–2 pt |
| **[S]** | Seen in a screenshot, not measured. | – |
| **[U]** | From memory, unverified. I found no source that shows it. | – |

"Sampled" colours were read from image pixels. They matched the design-system tokens
exactly in the lossless images, so the token is quoted next to each.

**Versions.** Sources span 2022–2026. Row, card and header anatomy did not change in
that time. What did change is named where it matters: the Trips journey view
(illustration in 2022–23, map plus bottom sheet from 2025), and the CTA inset.

---

## 1. Screen inventory and navigation model

### Tabs

Bottom tab bar with six tabs, in this order [S: every screenshot; App Store description]:

| # | Tab | Content |
|---|---|---|
| 1 | **Plan** | Home. Trip search, touch timetable, map, departure boards. |
| 2 | **Trips** | Saved journeys ("Single Trips") and "Commuting" routes; the live journey companion. |
| 3 | EasyRide | out of scope |
| 4 | Tickets & Travelcards | out of scope |
| 5 | Shop & Services | out of scope |
| 6 | Profile | Settings, notifications, co-passengers. |

There is no separate home or dashboard. The app opens on Plan. The 2022 redesign
removed the old tile home screen and the hamburger menu in favour of this bar
(Unic case study; `pctipp-2022-02.png` shows the old home).

Only the selected tab shows a label. It gets a black 44 pt circle with a white icon,
sitting in a notch that bulges out of the bar's top edge; the other five are bare
outline icons [T, M360]. A small red dot on a tab icon marks new content, for example
a ticket just bought (`video-ticket-05`/`06` frames; Unic).

### Plan tab

The red header holds the title "Plan", the SBB logo at the right, and a segmented
control with three segments: **Timetable | Touch-Timetable | Map**
[S: `yt-departures-04-board.jpg` Sept 2026, `yt-tutorial-08-home-departures.png` 2024,
`video-map-03-stopcard.png` 2023].

- *Timetable*: from/to card, and below it the departure board card(s).
- *Touch-Timetable*: tile grid (section 2).
- *Map*: full-bleed map with a search field (section 5).

The current App Store artwork (`appstore-iphone-01.jpg`) shows the Timetable segment
with the from/to card floating over a live map and a pill beginning "De…" at the
bottom right. The image is tilted and cropped, so I could not confirm whether the map
now sits behind the Timetable segment or how many segments remain. Treat that as
partially verified.

### Flow

```
Plan (Timetable)
 ├─ tap From/To ──► same screen in edit state: "Cancel" replaces the back arrow,
 │                  suggestions list + keyboard            (in place, not a modal)
 │                   └─ both fields filled ──► PUSH "Connections"
 ├─ Touch-Timetable: swipe tile A → tile B ──► PUSH "Connections"
 ├─ Map: tap a stop ──► bottom card "Departure | Destination" ──► fills From/To
 └─ departure board row ──► PUSH "Fahrtinfo" (one vehicle's stop list)

Connections (list)
 ├─ tap date/time row ──► BOTTOM SHEET "Travel date" (wheel + Accept)
 ├─ tap sliders icon ───► FULL-HEIGHT SHEET "Advanced search" (✕ to close)
 ├─ swipe a row left ───► red "Purchase ticket" action
 └─ tap a row ──────────► PUSH "Connection"

Connection (detail)
 ├─ "+ Save journey" ──► saved; button becomes "✓ View journey" ──► Trips tab
 ├─ "Change" row ──────► expands IN PLACE to a station mini-map
 │                        └─ "Open map" ──► FULL-SCREEN SHEET "Change"/"Walk" (✕)
 ├─ tap a ride leg ────► PUSH "Journey information" | "Train formation"
 └─ "Tickets from CHF x" (sticky) ──► PUSH "Ticket options"

Trips ► saved journey ──► "Your journey": map + bottom sheet, swipe between steps
```

Evidence: `video-ticket-*`, `video-push-*`, `video-map-*`, `yt-tutorial-*` frames.

### Back, modals, sheets

- Pushed screens have a back chevron at the left of the red header and a centred
  title naming the screen ("Connections", "Connection", "Journey information",
  "Your journey") [S].
- The tab bar stays visible on every pushed screen, including detail and ticket
  options [S]. It disappears only under bottom sheets and full-screen sheets.
- Bottom sheets (date picker, co-passengers) dim the page with 50 % black [T
  `barrierColor 0x80000000`], have 16 pt top corners, a light 18–20 pt title at the
  left and a 32 pt outlined ✕ at the right, and end in a full-width red "Accept"
  button [S: `yt-tutorial-13-date-picker.png`, `video-commute-02-timepicker.png`].
- Full-screen sheets (Advanced search, transfer map) use the same title + ✕ row and
  leave a strip of the red header visible above them
  [S: `yt-tutorial-10-advanced-search.png`, `community-33347-01.jpg`].
- Editing From/To is not a modal. The header title stays "Plan", the back arrow
  becomes the text "Cancel", and the suggestion list covers the page
  [S: `yt-tutorial-15-station-autocomplete.png`].

---

## 2. Trip search

### From/To card

A white card that overlaps the bottom of the red header by about 22 pt [M360].

```
 0        24      46 (text)                                   390
 │ 8│◄─────────────── card 374 wide, r16 ───────────────────►│8 │
 ┌──────────────────────────────────────────────────────────────┐
 │  ◎   Zürich HB                                        ╭───╮  │ 48
 │  │   ──────────────────────────────────────────────── │ ⇅ │  │  swap ⌀44, centred
 │  ◎   Chur                                             ╰───╯  │ 48  on the separator
 │      ───────────────────────────────────────────────┬────────│
 │      Mo. 22.05. │ 09:16 Dep │ ↺                      │   ≡̵   │ 48
 └──────────────────────────────────────────────────────┴───────┘
   16 pad · icon ⌀14 · text at x=46 from card edge · settings cell 48 wide
```

- Rows are 48 pt each [M: 46–50 across three frames]. Two fields + date row = 144–146;
  with a Via row, 192.
- Field text is 16 pt Light, black. Placeholders ("To", "Via") are grey [S].
- Left markers: double-ring circle, 14 pt, for from and to, joined by a 1 pt vertical
  line. Via gets a small hollow dot on that line. When the origin is the device
  position the marker is a blue locate symbol and the text reads "Current location"
  [S: `yt-tutorial-08-home-departures.png`].
- Separators are 1 px, light grey (`#E5E5E5` [T]), and start at the text column, not
  at the card edge.
- **Swap**: an outlined 44 pt circle with up/down arrows, at the right edge, centred
  vertically on the separator between From and To.
- **Via**: hidden by default. It is switched on in Advanced search ("Via – Show via")
  and then appears as a middle row [S: `yt-tutorial-10…`, `yt-tutorial-02…`].
- **Date row** (shown once both fields are filled): date and time in grey 16 pt,
  split by short 1 px vertical rules; `Dep` or `Arr` follows the time; a clock-with-arrow
  icon resets to "now". A full-height rule separates a 48 pt cell holding the sliders
  icon. The icon carries a small red check badge when any non-default option is active
  [S: `yt-tutorial-02-connections.png`].

### Stop entry and suggestions

[S: `yt-tutorial-15-station-autocomplete.png`, `yt-departures-07-autocomplete.jpg`,
`video-map-02-suggestions.png`]

- Both fields stay visible in the card while typing; the active one has a ✕ clear
  button at its right.
- The list sits directly under the card, as one white card with 1 px separators.
- Order: a "Current location" row with the blue locate icon first, set apart; then
  favourites (filled star at right, mode pictogram at left); then recents (clock icon
  at left, outline star at right). Tapping the star toggles the favourite without
  selecting the row.
- Row height 44 pt plus separator [M: 44.7]; text 16 pt Light at x = 48; star 24 pt
  with a 16 pt right inset. Eight rows fit above the keyboard on a 430×932 screen.

### Time picker

Bottom sheet "Travel date" [S: `yt-tutorial-13-date-picker.png`]:

- Two-segment control **Departure | Arrival**, 44 pt high, grey track, white selected
  pill with a 1 px dark outline.
- One wheel with columns date ("Sat 26 Oct", "Today", "Mon 28 Oct"), hour, minute
  (5-minute steps) and AM/PM where the locale uses it. The selected line has a light
  grey band; neighbouring lines fade and shrink.
- Full-width red "Accept" button, 44 pt.
- No calendar grid, and no "earlier / later" buttons inside the sheet.

### Advanced search

Full-height sheet [S: `yt-tutorial-10-advanced-search.png`]. Each setting is a row
with a 16 pt title, a 12 pt grey explanation and a switch at the right; row height
about 72 pt.

1. **Via** – "Show via"
2. **Price display** – "Show prices in timetable" (off in the 2024 recording, on in
   SBB's 2023 video)
3. **Means of transport** – "Limit your search to certain means of transport".
   When on, a checkbox tree opens: Train (ICE/TGV/RJ, EC/IC, IR/PE, RE, S/SN/R,
   ARZ/EXT), Bus, Ship, Funicular/Cog railway, Tramway/Underground. Each top-level
   item shows its navy mode pictogram. Checkbox rows are about 46 pt.
4. **Bicycle** – "Transport of bicycles (Switzerland)"

There is no walking-speed or minimum-transfer-time setting in the app; a reviewer
notes it exists only on the website (section 7).

### Touch timetable

[S/M: `appstore-iphone-02.jpg`, `video-ticket-01-touch.png`, `video-ticket-02-touch-swipe.png`,
`appstore-ipad-02.jpg`]

```
 8│◄──────────── grid 374 wide, outer corners r16 ──────────►│8
 ┌─────────────────────────────┬─┬─────────────────────────────┐ ┐
 │                             │3│  ░ map art ░                │ │ 84
 │   photo tile                │ │  Zürich HB ●                │ │
 │   (2 cells tall, 171)       ├─┴─────────────────────────────┤ ┘ gap 3
 │                             │   Bern                        │ 84
 │  Chalet Zermatt             │   Hirschengraben              │
 ├─────────────────────────────┴───────────────────────────────┤
 │  ● Bern                  (full-width tile)                  │ 84
 ├─────────────────────────────┬───────────────────────────────┤
 │  Jan   (photo)              │  Zoo Zürich   (photo)         │ 84
 ├─────────────────────────────┼───────────────────────────────┤
 │  Bümpliz                    │  Liebefeld                    │ 84
 │  Bachmätteli   (plain grey) │  Hessstrasse                  │
 ├─────────────────────────────┼───────────────┬───────────────┤
 │        ⌖                    │      ◎–       │      –◉       │ 83
 │   Current location          │     from      │      to       │
 └─────────────────────────────┴───────────────┴───────────────┘
   powered by ubique                                   ( Edit )
```

- Two columns of 185.5 pt with 3 pt gaps. A cell is 84 pt high. Tiles are 1×1, 1×2
  tall (photo) or 2×1 wide. The grid has rounded outer corners only; inner tile
  corners are square.
- Tile kinds: user photo; automatic "map art" (pale blue-grey street pattern with red
  track lines); plain grey when there is no art. Frequently used stops are added
  automatically; "Edit" lets the user add, remove and attach photos (sbb.ch).
- Label at bottom left with 8 pt padding, 16 pt Bold. Two-line labels put the locality
  in Light above the stop name in Bold. Labels are white on photos, black on map art.
- **Gesture**: press the origin tile, drag to the destination tile, release. A 2 pt
  red line with 10 pt red end dots follows the finger, and a translucent halo marks
  the touch point. Release pushes "Connections" for now-departure. The whole query
  takes one gesture.
- Bottom action row: "Current location" (double width), "from", "to". Dragging from
  "Current location" to a tile plans from the device position. "from"/"to" open text
  entry for a stop that has no tile.
- A 2020 review reports a cap of 16 tiles (section 7). Not rechecked.

"Take me home": I found no screen or text with this name in any 2022–2026 source. In
the current app the equivalent is one drag from "Current location" to a home tile.
Anything more specific about a dedicated button is **[U]**.

---

## 3. Connection list

Screen title "Connections". The search card stays pinned at the top; the list scrolls
under it.

### Date separator

Plain text, e.g. "Monday 22.05.2023", 14–16 pt Light, black, at x = 24, in a band of
about 46 pt between the search card and the first row [M]. It sticks under the search
card while scrolling, and a new one is inserted where the date changes
[S: `yt-tutorial-12-walk-legs.png` shows three in a row, with an empty-day message
"Oops, nothing's moving here."].

### One connection row

A white card, 374 × 112 pt, radius 16, no border, no visible shadow, 8 pt apart
(pitch 118–120 pt) [M: card 111–113, pitch 116–121 in two independent frames].
That is 13 % of screen height per card; 3½ rows are visible on 390×844 with the
two-field search card, 4½ on 430×932.

The card is three text lines of 20 pt each, 10 pt apart, with 16 pt padding all round:
16 + 20 + 10 + 20 + 10 + 20 + 16 = 112.

```
 x: 8  24      44 48        110 118                              ~250       382
    ┌────────────────────────────────────────────────────╮────────────────────┐
    │                                                     ╲  % from CHF 12.20 │ flag 24 high
 L1 │ ▣▣  ┏━━━━━━━┓  Direction Chur                        ╰──────────────────│
    │ 20  ┃ IC  3 ┃                                                           │ y = 26
    │     ┗━60×20━┛                                                           │
 L2 │ 09:38   ●────────────────○───────────────────────────●          10:52   │ y = 56
    │ 16 Bold ↑ dot ⌀10, line 2 pt, hollow dot per change               16 Bold│
 L3 │ Pl. 8   1.⚇⚇⚇ 2.⚇⚇⚇        🚲R              1 h 14 min             [i]  │ y = 86
    └─────────────────────────────────────────────────────────────────────────┘
      ↑16     ↑ bar starts at x = 72 from card edge          ↑ ends 14 pt before
                                                               the arrival time
```

**Line 1 – what you board first.**
- Mode pictogram, 20 × 20 pt: white vehicle on a navy square (`#2D327D` sampled, =
  token `blue`), radius about 2 pt. Train, bus, tram, ship, cable car each have one.
- 4 pt gap, then the line badge, about 60 × 20 pt: white italic "IC 3", "IR 35", "ICE"
  on red (`#EB0000`). Regional products without an official logo are plain bold text
  ("R 4", "B 20", "T 13", "BAT 3100"); some are a red outline on white ("RE33", "S3")
  [S: `yt-tutorial-09-connections-mixed.png`, `appstore-ipad-05.jpg`].
- 8 pt gap, then "Direction Chur" in 16 pt Light. It is truncated with "…" when the
  price flag needs the room [S: `pctipp-2022-04.png`].
- Only the first vehicle is named. Later legs are not listed in the row; the number
  of changes is readable only from the hollow dots on the bar.

**Line 2 – times and bar.**
- Departure time at the left edge and arrival time at the right edge, 16 pt Bold,
  tabular, 42 pt wide each.
- Between them a black 2 pt line with solid 10 pt end dots. Each change is a small
  hollow circle (about 6 pt, 1.5 pt stroke) placed proportionally to elapsed time
  along the bar [S: 0, 1 and 2 changes in `appstore-ipad-02.jpg`]. The bar is always
  black and has no colour per mode.
- When the trip starts or ends with a walk, a walker icon with minutes sits outside
  the times: `🚶5′ 14:32 ●────● 15:58 🚶18′` (12 pt) [S: `yt-tutorial-12-walk-legs.png`].
  The bar then covers only the ride, and the duration below covers everything.

**Line 3 – secondary facts, 16 pt Light.**
- Under the departure time: platform of the first leg, "Pl. 8" in English, "Gl. 32"
  in German, "Bin. 2B" where the operator supplies Italian [S].
- From the bar's start x: expected occupancy per class, "1.⚇⚇⚇ 2.⚇⚇⚇". Three figures;
  one black means low to average, two black means high, three red means very high;
  unfilled figures are light grey (`#BDBDBD` sampled) [S: legend in `appstore-ipad-03.jpg`].
- Then small attribute icons when relevant (bike reservation required, etc.).
- Right-aligned to the bar's end: total duration "1 h 14 min".
- Under the arrival time: a 16 pt red square with a white "i" when a disruption
  message applies to this connection [S: `yt-tutorial-02-connections.png`].

**Price flag (optional).** A tab cut into the top right corner, 24 pt high, with a
slanted left edge. Regular fare: white with a hairline outline, "from CHF **20.50**"
(10 pt Bold caption, 14 pt Bold amount). Supersaver: black fill, white text, leading
"%". With price display off, only a small black "%" tab appears on connections that
have a saver fare [S: `video-ticket-03-connections.png`, `yt-tutorial-02-connections.png`].

**Swipe.** Dragging a row left reveals a red block with white "Purchase ticket",
about 150 pt wide, the full height of the card [S: `video-ticket-04-swipe-row.png`].

**Delay and disruption in the list.** Verified: the red "i" square, and red occupancy
figures. I did not find a screenshot of a list row with a delayed departure or a
changed platform. In the journey view the pattern is scheduled time in black followed
by "ca +4 min" in red (section 4); whether list rows use the same pattern is **[U]**.

**Earlier / later.** I found no screenshot of the control. From memory, pulling the
list down past the top loads earlier connections and reaching the end loads later
ones, with no explicit buttons: **[U]**.

**Loading and empty.** While loading, a red animated bar motif plays in the centre of
the empty list area [S: `yt-tutorial-16-loading.png`]. An empty day shows a centred
two-line message, 16 pt and 14 pt grey.

### Typography in the list

| Element | Size / weight | Colour |
|---|---|---|
| Times | 16 Bold | black |
| Direction, platform, duration | 16 Light | black |
| Date/time in search card | 16 Light | grey (`#838383` sampled; tokens `smoke #8D8D8D` / `granite #686868`) |
| Date separator | 14–16 Light | black |
| Price caption / amount | 10 Bold / 14 Bold | black or white |
| Walk minutes | 12 Light | black |

Emphasis comes from Bold versus Light at one size, not from size steps. Nothing in
a row is larger than 16 pt.

---

## 4. Connection detail

Screen title "Connection". Layout top to bottom: summary card (pinned), one card per
ride leg, a slim row per walk or change, disruption messages, pictogram legend. A red
ticket button floats above the tab bar.

### Summary card

[M: `video-push-02-detail.png`, `yt-tutorial-03-detail.png`]

```
 ┌────────────────────────────────────────────────────────────┐
 │ Montreux → Luzern                         18 Bold           │
 │ 31.10.2024, 2 h 44 min                    14 Light, grey    │
 │ 13:17  ●──○─────────────────────────────●  16:01            │  same bar as the list
 │ ╭───────────────╮                         ╭───╮ ╭───╮        │
 │ │ +  Save journey│                        │ 🗺 │ │ ⋮ │        │  44 pt controls
 │ ╰───────────────╯                         ╰───╯ ╰───╯        │
 └────────────────────────────────────────────────────────────┘   ≈165 pt high
```

- "Save journey" is an outlined pill; after saving it reads "✓ View journey".
- The map button (added by 2024) and the ⋮ menu are 44 pt outlined circles.
- When the page scrolls, the card collapses to the title line only, 55 pt high
  [M360], and stays pinned.

### Ride leg card

Exact positions from the 360 dp screenshot [M360]; horizontal values from the screen's
left edge.

```
 x: 8   24          88  109                                   336  352
    ┌──────────────────────────────────────────────────────────────┐
    │ 11:36         ●   Teufen AR                           Gl. 3  │ y=28   16 Bold
    │               ┃                                              │
    │               ┃   ▣▣ S21                       1.⚇⚇⚇ 2.⚇⚇⚇   │ y=67   product row
    │               ┃   Richtung Trogen                            │ y=90   14–16 Light
    │               ┃   NF                                         │ y=112  12 italic grey
    │               ┃                                              │
    │ 11:52         ●   St. Gallen                          Gl. 12 │ y=148  16 Light*
    └──────────────────────────────────────────────────────────────┘
      card 174 pt high (with one attribute line); gap to next element 14–16
```

- Three fixed columns: time (x = 24), timeline (2 pt black line at x = 88, 10 pt dots),
  station name (x = 109). Platform is right-aligned 24 pt from the screen edge.
- The boarding row is Bold. The alighting row is Light in SBB's 2022–24 frames; the
  2025 Android screenshot shows the arrival time in Bold as well.
- A filled dot marks the trip's first and last stop; a hollow dot marks a stop where
  you change [S: `video-push-02-detail.png`].
- Product row: the same pictogram and badge as in the list; occupancy at the right.
- Then direction, then a line of service attributes as small grey italic codes and
  icons ("FZ BZ FS RZ R", family coach, business zone, low floor "NF").
- A disruption on this leg puts a 16 pt red "i" square in the time column, level with
  the product row [S: `yt-tutorial-03-detail.png`].
- Tapping the card opens "Journey information" for that vehicle.

### Walks and changes

Both are slim outlined rows between leg cards: full card width, 40–44 pt high,
radius 16, 1 px grey outline, page-grey fill (not white).

- **Change**: walker icon at the timeline x, label "Change" at the station-name x,
  chevron at the right [M360]. No minutes are shown on the collapsed row. I found no
  screen that prints the transfer time as text ("7 min Umsteigezeit"); the user has
  to subtract the arrival time from the next departure time.
- **Walk at the start or end**: `5′  🚶  Walk: 315 m  ›`, minutes first, then distance
  in metres. A plain white row with the address or stop name in Bold stands above or
  below it as the walk's other end [S: `yt-tutorial-12-walk-legs.png`].
- **Expanded change** [S/M: `yt-tutorial-04-transfer-map.png`, `community-33347-03.jpg`]:
  the row grows in place into a card holding a station map, inset 16 pt, aspect about
  4:3 (382 × 282 pt on a 430 pt screen), with an "Open map" pill (32 pt high) at the
  bottom right. The chevron turns down. The map shows the route only; no step list.

### Journey information (intermediate stops) and train formation

Pushed screen with a two-segment control in the header: **Journey information |
Train formation** [S: `yt-tutorial-05-journey-info.png`, `yt-tutorial-06-formation.png`].

- Header card: pictogram, badge, train number ("IR 90 1718"), direction, attributes.
- Stop list on the same three-column grid. Each stop shows arrival above departure
  (arrival 14 pt Light grey, departure 14 pt Bold), a hollow dot, the stop name, the
  platform at the right and occupancy from that stop onward. The user's own boarding
  and alighting stops are Bold with solid dots; the others are grey. A stop takes
  about 100 pt, so roughly seven fit on a screen.
- A through-running vehicle is announced inline: "Verkehrt weiter als T 4 49156"
  [S: `yt-departures-05-service.jpg`].
- **Train formation**: "‹ Direction of travel" (or "‹ Direction Genève-Aéroport"), then
  a horizontally scrolling strip. Sector labels ("Sector A", "Sector B") sit above
  with hairlines spanning the coaches they cover. Each coach is an outlined rounded
  box, about 86 × 40 pt, with the class digit at the right and the occupancy figures
  at the left. Under each coach: "NF" (low floor), bicycle, family-coach or restaurant
  icons. A locomotive is a rounded-nose outline; a closed coach carries a red no-entry
  sign [S: `sbbch-sbb-mobile-reisebegleiter-formation-en.jpg`]. A full legend follows.
- The strip does not mark where the user should stand, and it is not drawn against a
  platform diagram.

### Ticket button

"Tickets from CHF 37.50": red pill, 44 pt high, white 16 pt Light text, floating 8 pt
above the tab bar. Inset 8 pt from the screen edges in 2025 [M360], 16 pt in 2022
[M]. Content scrolls underneath it.

### Journey companion (Trips ► Your journey)

The 2025–26 layout [M: `sbbch-app_teaser_nrbg_en.jpg`, `appstore-iphone-05.jpg`]:

```
 ┌──────────────────────────────────────────────────────────────┐
 │ ‹                    Your journey                       <+>   │ red header
 │ ┌──────────────────────────────────────────────────────────┐ │
 │ │ Biel/Bienne → 3604 Thun, Zeltweg 10                  (⋮) │ │ 18 Bold
 │ │ Today, 1 h 18 min                                        │ │ 14 grey
 │ │ 17:24 ●━━━━━━◉─────────○──────────● 18:35  🚶7′          │ │ card 103 pt
 │ └──(★)──(☰)────────────────────────────────────────────────┘ │ ⌀44 buttons hang
 │                                                         (➤)   │   off the card edge
 │          station map, full bleed                        (◈)   │ ⌀44, 55–60 pitch
 │      ○ Platform 7 ◄▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸ ○ Platform 1A-D            │
 │                                   ╭ 🚶⌐ │ -1 │ ⌄ ╮            │ level pill 132×44
 ├──────────────────────── ▬ ───────────────────────────────────┤ handle 32×3
 │ ◤ S3 ◢◤ 🚶 ◢◤ IC 6 ◢◤🚶◢◤ B 1 ◢◤🚶◢                           │ chips 32 high
 │        ▂                                                     │ 12×3 marker
 │ ┌──────────────────────────────────────────────────────────┐ │
 │ │ Change in Bern                                            │ │ 18 Light + Bold
 │ │ Arrival                                         Platform  │ │ 14 grey
 │ │ 18:00                                              1A-D   │ │ 18–20 Bold
 │ ├───────────────────────────(🚶)───────────────────────────┤ │ white ▲ / grey ▼
 │ │ Departure                                       Platform  │ │
 │ │ 18:07                                                 7   │ │ 30 Bold
 │ │ ▣ IC 6  Direction Brig                                    │ │ card 204 pt
 │ └──────────────────────────────────────────────────────────┘ │
 └──────────────────────────────────────────────────────────────┘
```

- **Progress bar**: the travelled part turns grey (`#686868` sampled), and a red dot
  (`#EB0000`) marks the current position.
- **Leg chips**: one arrow-shaped chip per leg, interlocking, 32 pt high. Ride chips
  take the product's colour (navy `#2D327D` for S-Bahn and bus, red for IC) with the
  badge in white. Walk chips are blue (`#0074BF` sampled, = token `sky`) with a walker
  icon. Completed chips fade to a pale tint (`#ABADCB`). A short black bar under the
  strip marks the current step. This is the only place where the app colour-codes
  the legs of a trip.
- **Step cards** are swiped horizontally, one per step; the edges of the neighbours
  peek in. The map re-centres and re-zooms on each step (sbb.ch: "dynamic zoom area").
- The **next action is the largest text on the screen**: departure time and platform
  at 30 pt Bold, against 18–20 pt for the arrival above it.
- A ⌀44 list button under the summary card switches to the list layout of the detail
  screen. In the 2026 reviews this toggle is the single most criticised element
  (section 7).
- The 2022–23 layout had an illustration (platform, train interior, arrival hall) in
  place of the map; it changed with the phase of the trip (`unic-sbb-mobile-unterwegs.jpg`).

### Real-time changes

Verified:

- **Delay**: the scheduled time stays in black and is not struck through; "ca +4 min"
  follows in red at the same size. A small red clock square appears in the summary
  card [S: `video-push-03-journey-delay.png`, `sbbch-…formation-en.jpg`]. Tokens: error
  red is `#C60018` on light and `#FF3838` on dark [T].
- **Bus bay / tram edge**: printed as "Kante F" where a rail platform would be
  "Gl. 2", in the same right-aligned position [S: `unic-sbb-mobile-unterwegs.jpg`,
  `yt-departures-05-service.jpg`].
- **Transfer walk time**: "6′ 🚶" above the departure platform in the change card
  [S: same Unic image].
- **Platform change**: confirmed only as a push notification, "Platform change at
  Zürich HB … Departure now from platform 32." (`sbbch-sbb-mobile_push_en.jpg`). How a
  changed platform is styled inside the app is **[U]**.
- Push notifications cover delay, platform change, cancellation, and prompts to board,
  alight and change (sbb.ch functions page).

---

## 5. Departure board and map

### Departure board

It is a card on the Plan tab, under the from/to card, not a screen of its own
[S/M: `yt-departures-04-board.jpg` 2026, `yt-tutorial-08-home-departures.png` 2024].

```
 ┌──────────────────────────────────────────────────────────────┐
 │ Abfahrtstabelle ab:                                    ╭───╮ │ 14 Light
 │ Zürich, Central in Richtung Zürich, Paradeplatz        │ ✎ │ │ 14–16 Bold, wraps
 │                                                        ╰───╯ │ ⌀44 edit button
 │            Ab      Richtung                                  │ column heads 14 grey
 │ ──────────────────────────────────────────────────────────── │
 │ ▣ T 7      22:01   Zürich, Wollishoferplatz                H │ 44 + 1 px
 │ ▣ T 11     22:04   Zürich Tiefenbrunnen, Bahnhof           F │
 │ ▣ T 16     22:06   Zürich, Laubegg                         B │
 │ ▣ T 4      22:09   Zürich, Bahnhofstrasse/HB               F │
 │ ▣ T 7      22:11   Zürich, Wollishoferplatz                H │
 │                           ● ○                                │ pager dots, red = current
 └──────────────────────────────────────────────────────────────┘
  x: 24 pictogram(20) · 48 line (16 Bold) · 92 time · 144 direction · letter at right −24
```

- Always exactly **five** departures. It does not scroll for more; the user taps a row
  or runs a search.
- Columns: mode pictogram, line in Bold, absolute time (no "in 3 min" countdown),
  direction, and at the far right the **edge letter or platform** as a bare character
  with no "Kante"/"Gl." prefix. A board for a stop without edge data leaves the
  column empty.
- Several boards sit side by side and are swiped horizontally; red pager dots show
  the position.
- The first board can be "Departure board from current location" (nearest stop, all
  directions), switched on by a toggle.
- The round button opens a sheet "Abfahrtstabellen": that toggle, the saved boards
  with a pencil each, "Reihenfolge ändern" (reorder), and a red "Abfahrtstabelle
  hinzufügen" button. A board is defined by *from stop*, an optional *direction stop*
  and the same transport-mode checkbox tree as Advanced search
  [S: `yt-departures-03-filter.jpg`].
- With no boards saved, the area is empty and a ⌀44 "add board" button sits at the
  bottom right [S: `yt-departures-02-home-empty.jpg`].
- Tapping a departure pushes "Fahrtinfo": a header card (pictogram, "T 13 48495",
  direction, attributes) and the stop list with the edge shown per stop ("Kante G").
- I saw no delay shown on a board row in any source. Whether boards show real-time
  deviations is **[U]**.

### Map

[S: `video-map-01`…`07`, `appstore-iphone-01.jpg`, `appstore-ipad-01.jpg`, `sbbch-pride-poi-en.jpg`]

- Base map: very light grey with white roads and pale grey buildings, almost no
  colour. Rail tracks are drawn individually as dark lines, with platforms as pale
  pink-beige strips between them.
- Stops are navy rounded-square pins carrying the mode pictogram, with the stop name
  in navy beneath. At bus and tram stops the individual edges are labelled on the map
  ("Kante A", "Kante C") [S: `video-map-01-maptab.png`]. Mobility services use other
  colours: green for car and bike sharing, blue for parking, pink for shops.
- Controls are a column of ⌀44 white circles at the right: locate (arrow), layers,
  on some screens a filter, and a compass when the map is rotated. Pitch 55–60 pt.
  A small © button sits at the bottom right.
- Search: a white field card at the top, 48–50 pt high, with a magnifier and a small
  floating label "Please enter a stop or a location".
- Tapping a stop turns its pin red and enlarges it, and raises a bottom card: pictogram
  and name (18 pt), "53 km from your current location." (14 pt), a ⌀32 ✕, and two
  outlined pills **Departure** and **Destination** (44 pt high, each half the width)
  that put the stop into From or To [S: `video-map-03-stopcard.png`].
- Address search is supported: "Search for any address to have the best way to get
  there on foot suggested to you" (sbb.ch).

### Walking routes and station interiors

[S/M: `community-33347-01.jpg`, `community-33347-02.jpg`, `sbbch-app_teaser_nrbg_en.jpg`,
`video-map-06-walk.png`, `yt-tutorial-04-transfer-map.png`]

- A walk is drawn as a pale blue band, about 8 pt wide, with solid blue triangles
  (`#0C97F8` sampled) every 10 pt or so, pointing in the walking direction. Outdoor
  walks in the 2023 video are the triangles alone, with no band.
- Route parts on a **different floor** from the one displayed are a grey band with
  dark grey triangles. This is how an underpass is told apart from the platform.
- Start and end are white circles with a 3 pt black ring, labelled "Gleis 11" or
  "Platform 7" in 16 pt Bold with a white halo. The vehicle the user leaves is a
  black teardrop pin with the mode pictogram. The destination of a final walk is a
  larger black teardrop with a white dot.
- **Sector letters** appear on some platforms as navy squares with a white letter
  ("C", "D"). A 2026 reviewer says they are missing on the transfer card's map
  (section 7); the two observations are from different stations and versions.
- **Floor control**: a vertical list at the right, "4 3 2 1 0 -1", one 44 pt cell per
  level, the active level on a grey fill with white text. In addition a pill is
  pinned to the route at the point where the level changes: stairs or escalator icon,
  target level ("-1"), chevron.
- The full-screen map sheet has only a title ("Umsteigen", "Walk") and ✕. There are
  no written directions, no distance or time on the sheet, no exit side, and no
  hint which end of the platform to use.
- Routes come from a network model and can look wrong on the ground. Users document
  a suggested path along tram tracks and through the bus station at St. Gallen, and
  two different routes for the same transfer at different times of day (section 7).

---

## 6. Visual language

### Colour roles

All values below are tokens [T]; the ones marked ✓ were also sampled from screenshots.

| Role | Light | Dark |
|---|---|---|
| Brand / primary, header, CTA, IC-type badges | `#EB0000` ✓ | `#EB0000` ✓ |
| Header segmented track (darker red) | `#C60018` ✓ (video-compressed sample `#B50019`–`#C90016`) | same |
| Error and delay text | `#C60018` | `#FF3838` |
| Page background | `#F6F6F6` ✓ "milk" | `#000000` ✓ |
| Card background | `#FFFFFF` ✓ | `#212121` ✓ (sampled `#202020`) |
| Primary text and icons | `#000000` ✓ | `#FFFFFF` |
| Secondary text and icons | `#686868` ✓ "granite" | `#B7B7B7` "graphite" |
| Separator | `#E5E5E5` "cloud" | `#444444` "iron" |
| Mode pictogram, S-Bahn and bus chips | `#2D327D` ✓ "blue" | same in screenshots |
| Walking (chips, route), selection | `#0074BF` ✓ "sky" | `#128EDE` |
| Success | `#008233` | `#109D47` |
| Warning | `#FCBB00` | `#FFC727` |

Notes:

- Red is used for three things: brand chrome, the primary action, and trouble
  (delay, disruption, very high occupancy). On a detail screen the red header, the
  red ticket button, red IC badges and a red delay all compete.
- The app uses colour for product family and for walking only in the journey chips.
  The list bar and the timeline are black.
- **Dark mode** keeps the red header. Page goes black, cards charcoal, text white.
  The tab bar inverts: the selected circle becomes white with a black icon
  [T; S: `pctipp-2022-01.png`, `pctipp-2022-04.png`]. Illustrations have night versions
  (`unic-sbb-mobile-hoppla.jpg`).

### Typography

- Typeface: **SBB Web**, the railway's own Helvetica-family face, in Light, Roman,
  Bold (plus Thin, UltraLight and two condensed cuts) [T].
- **Body text is Light**, not Regular. Emphasis is Bold. Roman is rare in the app.
- Scale [T], size/line-height: 10/12, 12/16, 14/20, **16/20** (default), 18/24, 24/32,
  30/32.
- Where sizes land in the app [M]: header titles 18 Light white; card titles 18 Bold;
  times, stops, platforms 16 Bold or Light; captions and labels 14 Light grey;
  attribute codes 12 italic grey; the journey view's next departure 30 Bold.
- Digits are tabular in times and platforms [S].
- Abbreviations are part of the look: "Pl.", "Gl.", "Dep", "1 h 14 min", "ca +4 min",
  "5′".

### Iconography

- UI icons: thin single-weight outlines (about 1 pt), 24 pt, black. Used bare or
  inside ⌀44 outlined circles.
- **Mode pictograms**: white vehicle silhouettes on a navy square, 20 pt in rows.
- **Line badges**: the Swiss train-category logos, white italic letters plus number
  on a red rectangle of fixed size, about 60 × 20 pt. Regional lines are bold text
  without a box, or red-outlined boxes.
- **Occupancy**: three small standing figures per class.
- **Markers**: double ring for from/to, solid and hollow dots on bars and timelines,
  red square "i" for disruption, black teardrop pins on the map.

### Spacing, shape, elevation

- Spacing scale 4 / 8 / 12 / 16 / 24 / 32 [T].
- Screen gutter for cards **8**; card padding **16**; text therefore starts at x = 24
  [M360].
- Card radius **16** [M]. Buttons, segments and chips are full pills. Icon buttons are
  circles. Checkboxes are rounded squares of about 4 pt radius.
- Touch targets: 44 pt for buttons, list rows, segments and floor cells [T, M].
- Elevation is nearly flat. Result and leg cards have no border and no visible
  shadow; white on `#F6F6F6` is the only separation. Only the pinned header card and
  floating map controls cast a soft shadow. Header elevation is 0 [T].
- The first card on every screen overlaps the red header by about 22 pt, which ties
  header and content together [M360].
- Tab bar: 81 pt high including the label, above the system inset. Selected circle
  ⌀44, centre 28 pt below the bar's top edge; label centre 68 pt below it. The notch
  around the circle has a 28 pt radius (22 + 6) [T, M360].

### Motion

- Segmented control: the selected pill slides, 200 ms, ease-in-out [T].
- Tab bar: the notch travels and morphs from the old tab to the new one along a
  Bezier "wave", and the circle follows [T: `tab_curves.dart`]. Duration not read.
- Touch timetable: the red line tracks the finger live.
- Result rows follow the finger on a left swipe to reveal the purchase action.
- Journey view: step cards page horizontally and the map animates to each step.
- Loader: red bars streaming to the right, like a passing train.
- Illustrations change with trip phase and with light or dark mode (Unic).
- Screen transitions are the platform defaults as far as the videos show. Haptics
  could not be assessed.

---

## 7. What works and what frustrates

Sources: 241 App Store reviews fetched 2026-11-21 (CH, GB, US feeds; quoted with store,
date and star rating), SBB Community threads, PCtipp, Unic. The CH store rating at fetch time
was 3.06 from 1,182 ratings.

### Works well

- **Facts at a glance.** "You can see all the detail you need at a glance including
  platform numbers which is handy for the quick changes. There are also more in depth
  details such as stops, train configuration so you know where on the platform to
  stand" (GB, 2020-08-20, 5★).
- **Speed, when it behaves.** "Extremely fast route planning with instant price
  information" (GB, 2023-04-28, 5★). "Die performance ist top … ein smoothes Feeling"
  (CH, 2026-05-21, 4★).
- **Touch timetable.** "The touch timetable really makes this app stand out"
  (GB, 2017-03-04, 5★).
- **Departure boards and live journey.** "Fantastic with live maps and departure
  boards for getting between tight connections" (US, 2024-12-31, 5★). "The Saved
  Journey's tab and interactive map that follows your movements and provides
  notifications for your next transfer was extremely clear" (US, 2024-12-17, 5★).
- **Coach classes and sectors.** "Very informative in terms of showing which sections
  to go to for 1st vs 2nd class" (US, 2024-09-23, 5★).
- **Walking is included.** "It even provides walking directions to, from, and between
  stops" (US, 2025-09-05, 5★).
- The 2022 redesign won Gold for usability at Best of Swiss Apps 2022 (Unic).

### Frustrates

1. **Map as the default trip view.** The loudest complaint of 2026: 20 of the 241
   reviews fetched, April to November. "Als Reisender möchte ich wissen, auf welchem
   Gleis ich ankomme und auf welchem Gleis der anbindende Zug fährt" (CH, 2026-07-19,
   2★). "Alle müssen jetzt nochmals klicken um die Reise Liste zu sehen … behaltet die
   letzte Einstellung" (CH, 2026-10-28, 1★). "Ich sehe die Reisedauer … nicht mehr,
   muss die Ansicht wechseln um Tickets zu kaufen und auch Informationen zur
   Auslastung sind erst nach einer weiteren Geste sichtbar" (CH, 2026-05-02, 3★).
   The choice is not remembered between trips (CH, 2026-05-21, 4★). One reviewer
   reports the list back as the default on 2026-09-12; complaints continue through
   November, so the state of this setting in 12.61 is unclear.
2. **Transfer maps at big stations confuse.** A community thread calls the transfer
   map at St. Gallen "nur Verwirrung" and asks for three plain facts instead: exit
   side, which track shares the platform, and which way to turn in the underpass.
   Users post routes that run along tram tracks and two different routes for the same
   transfer (community.sbb.ch/d/33347, Jan 2025; images `community-33347-*`). "Bei der
   Umsteigen Karte vermisse ich … die Beschriftung der Sektoren" (CH, 2026-07-01, 4★).
3. **No countdown.** Since the 2022 redesign there is no countdown to departure or
   transfer, "man [muss] selber zählen" (community.sbb.ch/d/7116, June 2022).
4. **Transfer times.** "It's giving me connections where there is 0 minutes changeover
   time – bus arrives at exactly the same time the connection leaves" (GB, 2024-01-03,
   1★). The desired transfer time cannot be set in the app (CH, 2026-07-19, 2★).
5. **Bus stops with the same name.** "Two different stations within one street radius
   can have the same name and not properly indicated in the app map. This causes
   confusion when looking for a tram/bus stop" (GB, 2020-01-10, 3★).
6. **Modes look alike.** "The timetable is confusing to read. Would be helpful to show
   different means of transport in different colours" (GB, 2026-08-19, 1★).
7. **Cancellation wording.** Visitors read "cancellation" as "no service" when a
   replacement bus was running (GB, 2026-05-11, 3★).
8. **Live map disagrees with the delay.** The vehicle keeps moving on the map as if
   on time while the text shows a delay (US, 2026-09-30, 4★). "Ghost" buses and trams
   are shown with a live position but do not exist (CH, 2026-10-17, 1★).
9. **Walking from the current position.** A user is sent on a 20-minute walk while a
   station five minutes away is ignored (CH, 2025-09-11, 1★).
10. **Reliability after updates.** In October–November 2026 several users report the
    results list freezing: connections appear, then nothing can be scrolled or tapped
    (CH, 2026-11-18; CH, 2026-10-04; both 1★).
11. **Too much in one app.** PCtipp (2022) found the app "ein wenig überladen". "Wenn
    man die Funktion … nach langer Suche … gefunden hat, ist die Benutzerführung gut"
    (CH, 2026-11-04, 2★).
12. **Departure board from current location has no mode filter**, unlike a saved
    board (CH, 2025-11-15, 4★).

From the screenshots, not from reviews:

- The list row names only the first vehicle. A trip of IR + bus + tram looks the same
  as IR + IR + IR apart from the number of dots.
- Transfer minutes are never printed. Walk minutes are, but only on first and last
  walks ("5′") and in the journey view ("6′").
- Collapsed "Change" rows hide everything about the transfer.
- Intermediate stops cost a second screen and about 100 pt each.
- The departure board shows five rows and absolute times only.

---

## 8. Recommendations for Kante

### Adopt (ranked)

| # | Pattern | Build it like this |
|---|---|---|
| 1 | **Three-line result row with fixed columns** | Card 112 pt: 16 padding, three 20 pt lines, 10 pt gaps; cards 8 pt apart, radius 16, white on `#F6F6F6`-like grey, no border. Times 16 Bold at both edges, everything else 16 Light. Platform under the departure time, duration right-aligned to the bar end, status icon under the arrival time. |
| 2 | **Proportional time bar** | 2 pt line, 10 pt end dots, a marker per change placed by elapsed time. Bar starts 72 pt from the card edge and ends 14 pt before the arrival time. |
| 3 | **Same grid for list, detail and stop list** | Time at x = 24, timeline at x = 88, names at x = 109, platform right-aligned at −24. Boarding row Bold, alighting row Light. |
| 4 | **Platform or bay always in the same place, right-aligned, Bold** | "Gl. 2" and "Kante F" share one slot in rows, leg cards, change cards and board rows. |
| 5 | **Next action is the biggest text** | In the live view, next departure time and platform at 30 Bold against 16–18 elsewhere. |
| 6 | **Delay as an addition, not a replacement** | Scheduled time unchanged, "+4 min" after it in the error colour at the same size. No strikethrough. |
| 7 | **Leg chips** | Arrow-shaped, interlocking, 32 pt high, coloured per leg, walk legs in their own colour, finished legs faded, marker under the current one. |
| 8 | **Search card overlapping the header** | Rows of 48 pt; from/to markers joined by a line; swap as a ⌀44 circle centred on the separator; date row "Mo. 22.05. │ 09:16 Dep │ now" with a settings cell and a badge when filters are active. |
| 9 | **Suggestion list** | Current location first, favourites, then recents; 44 pt rows; star toggle at the right that does not select the row. |
| 10 | **Departure board as a home card** | Saved boards defined by stop + optional direction + mode filter; 44 pt rows; pictogram, line Bold, time, direction, bay letter at the far right; swipe between boards. |
| 11 | **Floor-aware walking route** | Band with direction triangles; the part on another level in grey; a level pill pinned to the route where the level changes; a vertical level list at the edge. |
| 12 | **Stop card on the map** | Tap a stop → card with name, distance and two half-width pills "Departure" / "Destination". |
| 13 | **Drag from tile to tile** | One gesture creates a query. Worth offering for the user's top 6–8 places; 84 pt cells, 3 pt gaps, label bottom-left. |
| 14 | **Sticky primary action above the tab bar** | 44 pt pill, 8 pt inset, content scrolls beneath. In Kante this is "Start" or "Go", not a ticket. |
| 15 | **Small rules** | 8 pt gutter, 16 pt padding, 16 pt radius, 44 pt targets, body in a light weight with Bold for facts, sheets with title-left and ✕-right, 200 ms ease-in-out for segment changes. |

### Avoid

- **A map as the default or only view of a trip.** Default to the list; remember the
  user's last choice per app, not per trip.
- **Collapsed transfers with no numbers.** Always print the transfer time and the two
  platforms on the row itself.
- **Naming only the first vehicle in a result row.** Show every leg's badge in order.
- **One colour for every mode** in the bar and timeline.
- **Red for brand, action and alarm at once.** Keep the alarm colour for alarms.
- **Absolute times only on a departure board.** Add minutes-to-go.
- **Five-row boards that cannot grow.**
- **A second screen for intermediate stops** at 100 pt per stop.
- **Six tabs** with unlabelled icons. Kante has no shop; three or four labelled tabs
  are enough.
- **Wheel-only date picking.** Add "now", "+15 min", "tonight", "tomorrow morning"
  shortcuts and earlier/later buttons on the list itself.
- **Routes drawn straight from a network model without a sanity check**, and a map
  that shows a vehicle on time while the text says delayed.

### Where Kante can clearly do better

Each item answers a documented complaint in section 7.

1. **"Where exactly to stand" as text first, map second.** For every boarding:
   platform or bay, sector, and position along it ("Kante F, front third",
   "Gl. 7, sector B–C"). SBB shows a formation strip and sector letters but never
   states where the user should stand.
2. **A transfer card that answers the three questions users ask**: which side to exit,
   whether the next track shares the same platform, and which way to go in the
   underpass, plus walk minutes against minutes available ("4 min walk, 7 min to
   change").
3. **Countdowns.** "Leaves in 6 min" on boards and on the next leg; "3 min spare" on
   transfers, coloured by slack.
4. **Bay letters on the map and in every list**, large enough to read, and same-name
   stops told apart by bay and by street side.
5. **Legs visible in the row**: badges in sequence with the bar segmented and coloured
   by mode, walking as a dashed segment with its minutes.
6. **Adjustable walking pace and minimum transfer time** in the search options.
7. **Intermediate stops inline**: expand a leg in place, 28–32 pt per stop.
8. **Replacement services stated plainly**: "Train replaced by bus EV 12 from Kante C",
   never a bare "cancelled".
9. **Honest live state**: one source of truth for the delay text and the map vehicle;
   mark a vehicle with no live signal as scheduled-only.
10. **Speed and resilience**: results must stay scrollable while prices, occupancy or
    live data are still loading.

### Brand-specific – do not copy

| SBB element | Why | Generic alternative for Kante |
|---|---|---|
| SBB logo (double arrow with cross) in the header | Registered trademark. | Kante's own mark, or no logo in the header. |
| SBB red `#EB0000` as chrome plus the station-clock motif | Core brand identity; the clock design is separately licensed (sold as Mondaine). | Kante's own primary colour; a neutral or dark header. Keep a distinct alarm red that is not the brand colour. |
| Typeface **SBB Web** | Proprietary. The design-system README says the font is "licensed separately under more restrictive terms" than the MIT code. I did not read the NOTICE file itself. | Inter, IBM Plex Sans or the system font, in weights 300/400 and 700, with tabular figures. |
| SBB pictogram set (navy mode squares, occupancy figures, attribute icons) | SBB's own artwork. The repository is Apache-2.0, which does not grant trademark rights, and the set is recognisably SBB. | Draw Kante's own mode icons, or use an open set (Material Symbols, OSM/Maki transit icons), on Kante's own shape and colour. |
| Train-category logos (IC, IR, ICE, EC, RE italic lettering on red) | Product marks of SBB and other railways. | Plain text badges: rounded rectangle, bold upright "IC 3", coloured by product family or, for local lines, by the operator's published line colour. |
| Illustrations (people on platforms and in trains, the display-board error screen) | Commissioned artwork. | Kante's own illustration style, or none. |
| Tab bar with the travelling circular notch | Not a trademark, but it is SBB Mobile's signature shape. | A standard labelled tab bar. |
| The name "Touch-Fahrplan / touch timetable", "EasyRide", "SwissPass" | Product names. | Describe the feature ("drag between places"). |

The layout patterns themselves (three-line rows, proportional bar, timeline grid,
overlapping card, leg chips, stop card) are generic and safe to reuse with Kante's
own colours, type and icons.

---

## Not verified

- Earlier/later paging gesture in the connection list.
- How a delayed departure or changed platform looks in a list row or leg card
  (only the journey view and a push notification were seen).
- Whether departure boards show real-time deviations.
- The exact November 2026 Plan layout (map behind the Timetable segment; the "De…"
  pill) – seen only in tilted, cropped store artwork.
- "Take me home" as a named feature.
- Platform differences between iOS and Android beyond what the screenshots show.
- Motion durations other than the segmented control; haptics.
- The current tile limit of the touch timetable.
- The text of the SBB Web font licence (only the README's summary was read).
- Font sizes are inferred from glyph heights and SBB's published scale; individual
  values may be off by one step (for example 14 vs 16).
- Google Play rating: the page's markup was ambiguous, so it is not quoted.
