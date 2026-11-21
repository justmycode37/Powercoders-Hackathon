# Google Maps on mobile: design study for Kante

Research date: 2026-11-21. Scope: Google Maps for Android and iOS as documented between Nov 2023 and Nov 2026, with the focus on public transport, walking and indoor use.

This is a study of layout and interaction patterns. It is not a branding reference: section 10.4 lists what must not be copied.

## 0. How to read this document

**Evidence.** Every screenshot referred to is in `google-maps/` and is listed with its URL in `google-maps/sources.md`. File names are given in `code` so a claim can be checked against the image.

**Confidence labels.**

- *Verified*: seen in a screenshot in the folder, or stated on an official Google page that was read.
- *Material spec*: a default from the Material 3 component source, not a measurement of Maps.
- *From memory, unverified*: not found in any source looked at. Treat as a hypothesis.

**Units.** Measurements are in dp, which equal CSS px for a web app. Each screenshot's pixel scale was calibrated against Material sizes visible in the same image (40dp small FAB, 56dp FAB, 64x32dp navigation indicator, 32dp chip). The scales are in `sources.md`. Expect an error of about ±1dp on small items and ±2% on sheet heights. Percentages are of full screen height or width including the status bar.

**Reference frame.** Wireframes use a 412 x 915dp portrait phone, the logical size of the Pixel screenshots.

**Versions.** The app changed three times in the study period, and the screenshots span all three:

| Period | Change | Source |
|---|---|---|
| Feb–Jul 2024 | Full-screen pages replaced by sheets over the map; mode switcher moved from the top into the sheet; close button top-right | 9to5Google, Feb 7, May 3 and Jul 14 2024 |
| Jul 2024 | Bottom bar reduced from five tabs to three (Explore, You, Contribute) | 9to5Google, Jul 31 2024 |
| Mar–Sep 2025 | iPhone gets the same sheets; summary line gets a large stacked duration and "Arrive hh:mm"; primary colour moves from blue to teal; place actions dock to the bottom; transit trips can be minimised | 9to5Google Mar 7, Mar 31, Sep 17 2025; Android Authority Sep 26 2025 |

Where layouts differ between periods, both are described and the newer one is marked "current".

---

## 1. Screen inventory and navigation model

### 1.1 The model in one sentence

One map fills the screen at all times; everything else is a rounded sheet rising from the bottom or a floating card at the top, and the user closes a sheet with an X in its top-right corner (*verified*: "drops most fullscreen UIs in favor of sheet-based layouts … You close these sheets for place listings with a new 'x' button in the top-right, or by swiping back from the left/right edge", 9to5Google Jul 14 2024).

### 1.2 Inventory

| # | Screen | Container | Top of screen | Bottom of screen | Evidence |
|---|---|---|---|---|---|
| 1 | Home (Explore) | Map + peeking sheet | Search bar pill, category chip row | "Latest in the area" sheet peek, three-tab bar | `aa-2025-09-pt-directions-new-7.jpg`, `9to5-2023-11-google-maps-new-color-1.jpg` |
| 2 | Search entry | Full screen | Text field with back arrow | Keyboard | 9to5Google text only: "That initial UI for entering your destination … is unchanged and still a fullscreen page". Layout *from memory, unverified* |
| 3 | Category results | Map + list sheet | Search bar with query | List sheet with filter chips | `play-2026-11-search-results-list.jpg` |
| 4 | Place | Map + sheet, three detents | Search bar showing the place name with X; hidden when expanded | Sheet; action row docked (current) | `9to5-2024-07-google-maps-android-redesign-1.jpg`, `-2.jpg`, `9to5-2025-09-google-maps-m3-expressive-1.jpg`, `-2.jpg` |
| 5 | Directions overview | Map + floating card + sheet | From/to card | Sheet with mode tabs, summary, actions | `9to5-2024-07-google-maps-android-redesign-4.jpg` |
| 6 | Transit route list | Same sheet, taller | From/to card | Sheet at half height with route rows | `9to5-2024-02-google-maps-directions-search-redesign-3.jpg`, `play-2026-11-transit-route-options.jpg` |
| 7 | Transit route detail | Sheet, expanded | Sliver of map; sheet header with leg chain | Fixed bar: actions, arrival time, duration | `aa-2025-09-pt-directions-old.jpg` |
| 8 | Transit trip in progress | Route detail sheet or minimised strip | Normal home or map | Coloured status strip under everything | `aa-2025-09-pt-directions-new-1.jpg`, `-new-2.jpg`, `-new-7.jpg` |
| 9 | Walking or driving navigation | Map + banner + sheet | Manoeuvre banner | Sheet with time, distance, ETA | `aa-2025-09-walking-directions-options-new-add-report-1.jpg` |
| 10 | Live View (now "Lens in Maps") | Full-screen camera | Back, title, overflow | Clipped mini-map or instruction card | `google-2020-live-view-transit-frame75.jpg`, `google-2021-indoor-live-view-frame75.jpg` |
| 11 | Trip options | Full screen | X + centred title | n/a | `aa-2023-12-transit-route-settings.png` |
| 12 | Layers ("Map type") | Modal sheet with scrim | n/a | Sheet with tile grid | `play-2026-11-map-type-layers.jpg` |

So only three things are full screen: text entry (2), trip options (11) and the camera view (10).

### 1.3 Back behaviour

- X in the sheet's top-right closes that sheet and returns to the previous state (*verified*, 9to5Google).
- Edge swipe (system back) does the same (*verified*, same source).
- On iPhone the X replaced a back button at the left of the search bar: "This should aid reachability and one-handed usage, while this behavior also matches Apple Maps" (*verified*, 9to5Google Mar 7 2025).
- The Material bottom sheet docs describe back handling per state: back is intercepted when the sheet is expanded or half-expanded (*Material spec*). Whether Maps collapses one detent per back press or closes the sheet outright is *unverified*.
- Trip options uses an X on the left and a centred title, because it is a modal task rather than a sheet (`aa-2023-12-transit-route-settings.png`).

### 1.4 Floating controls and how they move

Positions measured on `9to5-2023-11-google-maps-new-color-1.jpg` (home) and `9to5-2024-07-google-maps-android-redesign-4.jpg` (directions).

| Control | Size | Position | Moves with sheet? |
|---|---|---|---|
| Search bar | 48dp high, full pill, 12dp side margins | Top, about 12dp below the status bar | No. Replaced by the from/to card in directions; covered when a sheet is fully expanded |
| Category chips | 36dp high pills, 12dp below the search bar | Horizontal scroll, first chip at 12dp, row bleeds off the right edge | No |
| Context chip ("See nearby attractions", "Other trip options") | 32dp high, centred | 19dp below the search bar | No |
| Layers button | 40dp circle | Right edge, 16dp margin, about 20dp below the chip row (17dp below the from/to card in directions) | No |
| Search-along-route button | 40dp circle | Directly under layers, 13dp gap | No |
| Compass | About 40dp circle | Under layers, shown only when the map is rotated (`aa-2025-09-pt-directions-new-7.jpg`) | No |
| Indoor level picker | About 44dp wide pill | Left edge, mid-height (section 6.4) | No |
| Location button | 56dp circle | Right, 16dp margin | Yes: its bottom edge stays 16dp above the sheet's top edge (measured at the 29% and 50% detents) |
| Directions button (home only) | 56dp rounded square, radius about 16dp, primary colour | Under the location button, 24dp gap, about 20dp above the bar or sheet | Yes |
| Street View thumbnail | About 90 x 52dp, white 3dp border | Bottom-left, 16dp margin, same baseline as the location button | Yes |

When a sheet reaches its expanded detent, all bottom-anchored controls are covered by it rather than pushed off the top (`9to5-2024-07-google-maps-android-redesign-2.jpg` shows only a sliver of map).

On iPhone the location button shows an arrow glyph instead of a crosshair; everything else matches (`9to5-2025-03-google-maps-iphone-sheet-redesign-3.jpg`).

---

## 2. The bottom sheet

### 2.1 What Material specifies

From the Material Components bottom sheet docs and resource files (*Material spec*):

| Property | Default |
|---|---|
| Top corner radius | 28dp ("extra large" shape) |
| Container colour | surface container low |
| Elevation | level 1 (1dp), for both standard and modal |
| Drag handle | 32 x 4dp, colour on-surface-variant, inside a 48 x 48dp touch target; 20dp padding below |
| Max width | 640dp (centred on wider screens) |
| States | hidden, collapsed (peek), half-expanded, expanded, plus dragging and settling |
| Half-expanded ratio | 0.5 of the parent height, only when "fit to contents" is off |
| Peek height | automatic; minimum 64dp |
| Expanded offset | 0dp from the top |
| Fling threshold | 500 px/s ("significant velocity"): a faster fling moves to the next state in the fling direction; `skipCollapsed` controls whether a downward fling can bypass the peek |
| Nested scrolling | The sheet is draggable from its scrolling child by default (`draggableOnNestedScroll = true`): content scrolls only once the sheet is expanded, and dragging down at scroll offset zero drags the sheet |
| Standard vs modal | Modal has a scrim and is hideable; standard has no scrim and is not hideable |

### 2.2 What Maps actually does

Measured on the screenshots:

| Property | Maps | Evidence |
|---|---|---|
| Top corner radius | 28dp. Fitted to the corner profile at five points | `9to5-2024-07-google-maps-android-redesign-1.jpg` |
| Handle | 40 x 4dp, mid grey (sampled `#C9C9C9`), centred, 8dp below the top edge. Wider than the Material 32dp | `…redesign-4.jpg` |
| Scrim | None on standard sheets: the map stays fully lit and interactive above the sheet. Scrim only on modal sheets (layers, report) | `…redesign-1.jpg`, `aa-2025-09-walking-directions-options-new-add-report-2.jpg` |
| Elevation | Soft shadow on the top edge only, no outline | all |
| Header | Title left; one to three 32dp circular tonal buttons right (options, share, save, close) with 16dp gaps and a 20dp right margin | `…redesign-4.jpg` |
| Sticky header | When content scrolls under it, the header keeps its place and gains a hairline shadow | `aa-2025-09-pt-directions-old.jpg` |
| Sticky footer | Primary actions pinned at the bottom of the sheet over the content, separated by a hairline shadow | `9to5-2024-07-google-maps-android-redesign-5.jpg` |

**Detents measured** (sheet height as a share of the screen):

| Sheet | Low | Middle | Expanded |
|---|---|---|---|
| Home "Latest in the area" | About 100dp visible above the 64dp tab bar (handle + one title row) | *unverified* | *unverified* |
| Place | 14% (about 130dp): handle, title, one action row. `9to5-2025-09-google-maps-m3-expressive-1.jpg` | 50.1%. `…redesign-1.jpg` | Top edge 54dp from the top of the screen (94%). `…redesign-2.jpg` |
| Directions overview | 29% (265dp): handle, title, mode tabs, summary, actions. Content-fitted, so walking is 27% | n/a | Top edge at 54dp. `…redesign-5.jpg` |
| Transit route list | n/a | About 50%. `…search-redesign-3.jpg` | *unverified*, presumably as above |
| Transit route detail | About 13% during a trip: leg chain + action bar. `aa-2025-09-pt-directions-new-2.jpg` | *unverified* | Top edge at about 7.5% of the height. `aa-2025-09-pt-directions-old.jpg` |

Three observations follow from the table:

1. The middle detent is exactly half the screen, the Material default.
2. The low detent is not a fixed height. It is sized to a whole content group, so nothing is cut mid-row.
3. The expanded detent never reaches the top. The top edge stops level with the top of the search bar (54dp), leaving the status bar and a sliver of map visible, which is what tells the user the map is still there.

**Map camera padding** (*verified* from static frames; animation not observable):

- The fitted route always lies inside the unobscured rectangle between the top card and the sheet. In `…redesign-4.jpg` the route spans 39% to 69% of the height between a card ending at 16% and a sheet starting at 71%. In `…search-redesign-3.jpg`, with the sheet at 50%, the route has been refitted into 19% to 48%.
- So the camera is refitted when the sheet settles at a different detent, with padding of roughly 24–40dp inside the free rectangle.
- A selected place pin sits at the centre of the free area above the sheet (`…redesign-1.jpg`: pin at 28% with the sheet starting at 50%).
- Whether the camera follows the sheet continuously during the drag or animates once on settle is *unverified*.

**Scroll hand-off and snap physics as Maps behaves**: *unverified*. Screenshots cannot show them. The Material defaults in 2.1 are the best available description, and they match *from memory* behaviour: drag anywhere on the sheet to move it; content scrolls only at the expanded detent; pulling down at scroll-top collapses to the middle detent; a fast fling skips a detent.

---

## 3. Search and autocomplete

### 3.1 The search bar (*verified*)

`9to5-2023-11-google-maps-new-color-1.jpg`, `aa-2025-09-pt-directions-new-7.jpg`:

- White pill, 48dp high, full corner radius, 12dp side margins, soft shadow, no outline. (Material's own search bar token is 56dp high with level 3 elevation and 16dp margins; Maps is more compact.)
- Left to right: brand mark (24dp), placeholder "Search here" at about 16sp in grey, microphone icon, camera-search icon, account avatar (30dp circle with a coloured ring).
- After a selection the same pill shows the place name at about 16sp in near-black, truncated with an ellipsis, and a single X on the right (`…redesign-1.jpg`).

### 3.2 Category chips (*verified*)

- One horizontally scrolling row 12dp under the bar. Each chip: 36dp high, full pill, white with a shadow, 18dp icon, label at about 12–14sp medium, 8dp between chips.
- 2023 order: Restaurants, Coffee, Parking, Hotels. 2025 order starts with a personal shortcut: Home, Restaurants, Apparel, Shopping. In 2026 an "Ask Maps" chip with an outline leads the row (`play-2026-11-map-type-layers.jpg`).
- Tapping a chip runs a category search and opens the results list sheet with filter chips ("Sort by", "Open now", "Price"), each an outlined 32dp chip with a dropdown caret (`play-2026-11-search-results-list.jpg`).

### 3.3 Autocomplete list (*from memory, unverified* unless marked)

No screenshot of the suggestion list was found. What is established:

- Tapping the bar opens a full-screen page (*verified*, 9to5Google Jul 14 2024).
- The page starts with the user's recent activity, "in case you wanted to repeat a recent destination" (*verified*, Android Authority teardown article, Aug 22 2025).

From memory:

```
┌──────────────────────────────────────────┐
│ ←  Search here                    🎤     │  field row, 56dp
├──────────────────────────────────────────┤
│ [⌂ Home] [💼 Work] [⋯ More]              │  shortcut chips
├──────────────────────────────────────────┤
│ 🕘  Zürich HB                          ↖ │  recent: clock icon
│     Bahnhofplatz, Zürich                 │
│ 📍  Zürich Flughafen                   ↖ │  suggestion: pin icon,
│ 4 km  Kloten                             │  distance under the icon
│ 🚉  Zürich Stadelhofen                 ↖ │  station: transit icon
│     Train station · Zürich               │
└──────────────────────────────────────────┘
```

- Row height about 64dp. Leading icon in a 40dp column, with the distance from the user in small grey text under it. Primary text 16sp with the typed part in regular weight and the completion in bold. Secondary text 14sp grey. A trailing arrow copies the suggestion into the field without submitting.
- In the directions context the first rows are "Your location" (blue dot icon) and "Choose on map". "Choose on map" shows a fixed pin at the screen centre over a draggable map with an OK button.

### 3.4 Field behaviour in directions (*verified*)

- "Your location" is rendered in the link colour with a blue dot, to distinguish it from a typed place (`aa-2025-09-pt-directions-new-3.jpg`).
- "To start navigation, your starting point must be your location. Otherwise, you get a preview of the route instead" (Google Maps Help, answer 144339). That is why the primary button reads "Preview" in some screenshots and "Start" in others.

---

## 4. Directions for transit

### 4.1 From/to card (*verified*, `…redesign-4.jpg`)

```
        20dp                                   20dp
        ┌────────────────────────────────────────┐  ┐
        │ ◯  Golden Gate Bridge, Golden Ga…   ⋮  │  │ 48dp
        │ ┊  ──────────────────────────────      │  │ 96dp, radius 16dp
        │ 📍 Terminal 1                       ⇅  │  │ 48dp
        └────────────────────────────────────────┘  ┘
```

- White card, 16dp radius, shadow, 20dp side margins, top edge 54dp from the top of the screen.
- Left column: hollow ring for the origin, three small dots as a connector, red pin for the destination.
- A hairline divider between the rows, inset to start at the text.
- Right column: overflow menu (⋮) on the origin row, swap (⇅) on the destination row.
- Tapping a row opens the full-screen search entry for that field.
- There is no back arrow on the card: the sheet's X exits directions.

### 4.2 Mode tabs with durations (*verified*)

- A scrollable tab row inside the sheet, under the title: Drive, Transit, Walk, Ride, Bike (the order shifts by region; two-wheeler and flight exist in some markets).
- Each tab is a 20dp icon plus the duration for that mode ("40 min", "1 hr 22", "7 hr"), about 12–14sp. Hours and minutes are abbreviated to keep five tabs nearly visible; the fifth is cut off to signal scrolling.
- Row height 48dp. The selected tab is in the primary colour with an indicator 3dp thick, about 60dp wide (the tab's content width), with rounded top corners. A full-width hairline sits under the row.
- The sheet title names the selected mode ("Drive", "Walk", "Public transport") at about 20sp.
- Pre-2024 the modes were tonal pill chips in the header; the tab form replaced it when the row moved into the sheet (`…directions-old-1.jpg` vs `…redesign-4.jpg`).

This row is the strongest idea on the screen: the user compares all modes before choosing one, without a tap.

### 4.3 Time and options controls

Three generations, all *verified*:

| Version | Row under the tabs | Evidence |
|---|---|---|
| 2023 | "Depart at 8:18 AM ▾" outlined chip left; "Options" outlined chip with a tune icon right | `…directions-old-3.jpg` |
| 2024 | Refresh icon; "Depart at 8:14 AM ▾" outlined chip (about 32dp high, 8dp radius). A sliders button appears in the sheet header instead of the "Options" chip | `…search-redesign-3.jpg` |
| 2026 (current) | Refresh icon; three filled grey chips with carets: "Leave now ▾", "Modes ▾", "Filter by ▾" | `play-2026-11-transit-route-options.jpg` |

The time chip opens a picker with Leave now / Depart at / Arrive by / Last available (*from memory, unverified*: only "Depart at" and "Leave now" appear in the screenshots).

Trip options, full screen (*verified*, `aa-2023-12-transit-route-settings.png`):

- "Preferred modes" with the caption "Modes you'd like prioritized in your results": Train, Tram, Subway, Bus, each a row with a 24dp icon and a switch.
- "Route options": a radio list of Best route, Fewer transfers, Less walking, Wheelchair accessible ("Avoid stairs and prefer elevators"), Lowest cost.
- "Mixed modes" with the caption "Modes you combine with public transport": Drive, Ride services, each a switch.

Google's own description of the filters: "customize your route with handy filters that let you select what type of transit you want to take, or if you want a route with less walking" (Google blog, Nov 15 2023).

### 4.4 Anatomy of one route option

**2024 layout** (*verified*, `…search-redesign-3.jpg`, `aa-2023-12-transit-options.png`). Row pitch 104dp, 20dp side padding, hairline dividers inset on both sides.

```
┌──────────────────────────────────────────────────┐
│ 🚌[28] › [ba][Red-S╱Yellow-S] › 🚃 › 🚶₆   1 hr 9 min │  line 1
│ 8:23 AM – 9:32 AM                          $12.65 │  line 2
│ in 5 min (on time), 13 min (early) from Golden…   │  line 3
└──────────────────────────────────────────────────┘
```

- Line 1, left: the leg chain. Each leg is a 20dp mode icon followed by a line badge; legs are separated by a small grey chevron. A walking leg is a pedestrian icon with its minutes as a subscript ("🚶₆"). Line 1, right: total duration, about 16sp medium, near-black.
- Line 2, left: departure and arrival clock times joined by an en dash, about 14sp. Right: fare in grey.
- Line 3: the next departures and the boarding stop, about 12sp grey: "in 5 min (on time), 13 min (early) from Golden Gate Bridge/Parking Lot". Variants seen: "Every 2 min from Corentin Cariou" for frequency services, and "Scheduled at 7:29 PM, 7:34 PM from Porte de la Villette" when there is no live data.
- An optional fourth line carries a warning with an amber triangle: "Modified schedule".

**Current layout** (*verified*, `play-2026-11-transit-route-options.jpg`, `9to5-2025-03-google-maps-directions-redesign-1.jpg`):

```
┌──────────────────────────────────────────────────┐
│ 25    9:45–10:10 AM                        $3.25 │
│ min   [🚶 4 min] › (G) › (C)                     │
│       Every 8 min from Classon Av                │
└──────────────────────────────────────────────────┘
```

- The duration moves to a left column, stacked: the number at about 28sp, "min" under it at about 16sp. In the driving summary it is coloured by traffic.
- The time range becomes the bold first line; the fare stays top-right.
- The walking leg becomes a small grey chip with icon and "4 min" instead of a subscript.
- The frequency or next-departure line is coloured as live status (green here).

**Line badges** (*verified*):

- A rounded rectangle about 20dp high with a 4dp radius, filled with the agency's line colour, the line name in bold at about 12sp in white or black for contrast. Subway bullets are drawn as circles where the agency does so (New York "G", "C"). Paris adds the agency's mode logo (M in a ring, RER box) before the badge.
- Alternative lines that serve the same leg share one badge split by a diagonal slash: "Red-S╱Yellow-S", "101╱130╱150". When they do not fit, the last segment is "…".

**Live status colouring** (*verified*, Google Maps Help, answer 6142130): green = on schedule and updating in real time; orange = early; red = delayed; black = not updating in real time; a caution triangle = construction or other delays. Only the time is coloured; the qualifier follows in grey brackets. Sampled: green `#1C7434`, orange `#8C5C14`, red `#CC2C24`.

**Accessibility and price notes**: fare right-aligned on the second line. No wheelchair mark appears on route rows in any screenshot; accessibility is a filter (4.3) and a per-vehicle chip in the detail (5.2).

### 4.5 The list as a whole

- A section label "Public transport" preceded the list before 2024; it is now the sheet title.
- Sort order is Google's "best route" ranking "based on key factors, like ETA, number of transfers and the length of your trip" (Google blog, Nov 15 2023). The list is not sorted by departure time, and there is no earlier/later paging control in any screenshot.
- While the list is shown, the map draws the first option (`…search-redesign-3.jpg`).

---

## 5. Route detail

### 5.1 Structure (*verified*, `aa-2025-09-pt-directions-old.jpg`, scale 2.0 px/dp)

```
 0      32        65                                     429  449dp
 │       │         │                                       │   │
 ┌───────────────────────────────────────────────────────────┐
 │                        ▬▬▬▬ handle                        │
 │ 🚶₁₈ › [RER][A] › (M)[6] › 🚶₁₀                      ( ✕ ) │ header 60dp, sticky
 ├───────────────────────────────────────────────────────────┤
 │       ●                                                   │ grey dots 9dp, pitch 18dp
 │      (M)  Charles de Gaulle – Étoile                    › │ ~18sp
 │      ┃┃   Follow signs for M6 Nation                      │ ~14sp grey
 │      ┃┃   [6] Nation                                      │ badge 38x20dp + headsign
 │      ┃┃   Every 4 min                                     │ grey
 │      ┃┃   ─────────────────────────────────────────────   │
 │      ┃┃   [icon] Buy tickets                            › │ row 48dp
 │      ┃┃   ─────────────────────────────────────────────   │
 │      ┃┃   What's it like on board?                        │
 │      ┃┃   [♿ Accessible ▾] [👥 Crowded ▾] [🛡 Monitored   │ chips 32dp
 │      ┃┃   ─────────────────────────────────────────────   │
 │      ┃┃   Boarding position for fastest exit              │
 │      ┃┃   [Rear][     ][     )                            │ 53x20dp segments
 │      ┃┃   ─────────────────────────────────────────────   │
 │      ┃┃   ⌄  Ride 5 stops (7 min)                         │ row 56dp, expands
 │      ┃┃   ─────────────────────────────────────────────   │
 │      ┃┃   Bir-Hakeim                                      │
 │      (○)  Exit via 2                                      │
 │       ●                                                   │
 │       ●   ─────────────────────────────────────────────   │
 │      🚶   Walk 10 min (600 m)                           › │ row 56dp
 │       ●   ─────────────────────────────────────────────   │
 │      📍   Eiffel Tower                           4:26 PM  │
 │           Av. Gustave Eiffel, 75007 Paris                 │
 │ Cost: €2.50                                               │
 ├───────────────────────────────────────────────────────────┤
 │ [✕ Exit] [🔖 Save]            Arrive at 4:26 PM · 55 min  │ fixed bar, pills 40dp
 └───────────────────────────────────────────────────────────┘
```

**The rail.**

- Centre line 32dp from the left edge. Content starts at 65dp. Right margin 20dp.
- A ride leg is a solid bar about 16–18dp wide in the line's colour with fully rounded ends. It runs from the boarding stop to the alighting stop.
- Boarding node: the agency's mode logo in a white circle of about 24dp, overlapping the top of the bar.
- Alighting node: a white disc inset in the rounded bottom end of the bar.
- A walking leg is a column of grey dots, 9dp diameter at 18dp pitch, with a pedestrian icon on the rail at the walk row.
- The destination node is a pin. The origin node is a blue dot for the current location (`google-2020-live-view-transit-frame15.jpg`).
- During a trip, a marker shows the rider's position on the rail: a blue circle of about 24dp with a white chevron and a white ring (`aa-2025-09-pt-directions-new-1.jpg`).

**Dividers.** Hairlines start at the content edge (65dp), never crossing the rail, so the rail reads as one continuous object.

**Bottom bar.** Fixed, with a hairline shadow. Left: tonal pill buttons 40dp high. Before a trip: "Pin" or "Save"; during a trip: "Exit"/"End" plus "Save". Right: "Arrive at 4:26 PM · " in grey 14sp, then the total duration at about 18sp medium.

### 5.2 Content blocks of one ride leg, in order (*verified*)

| Block | Content | Evidence |
|---|---|---|
| Entrance hint | "Enter via York St", plain text line above the boarding block | `google-au-2021-instation-directions-mobile.webp` |
| Boarding stop | Stop name about 18sp; trailing chevron (target not confirmed, presumably the station sheet); time right-aligned ("12:05 pm", number large, am/pm small underneath) | Sydney image, `…new-1.jpg` |
| Transfer hint | "Follow signs for M6 Nation", grey 14sp, directly under the stop name | `aa-2025-09-pt-directions-old.jpg` |
| Line + headsign | Badge then the destination shown on the vehicle ("Nation", "Parramatta Via Central") | both |
| Status + platform | "Scheduled · Platform 5" (grey), or "Every 4 min · ~~8:07 PM~~" with the superseded time struck through | Sydney image; `…new-1.jpg` |
| Tickets | A row with the agency app icon, "Buy tickets", chevron | `…old.jpg` |
| On-board conditions | Heading "What's it like on board?" then a scrolling row of 32dp chips: Accessible, Crowded/Not crowded, Monitored, Temperature. Chips with a caret let the rider report; chips with "+" add a report | both |
| Boarding position | Heading "Boarding position for fastest exit"; a train drawn as joined segments, the recommended one filled in dark teal and labelled ("Rear", or the car number "6"); caption "6 car train" | `…old.jpg`, `…new-1.jpg` |
| Alternatives | "Also every 4 min" or "Also at 1:30 PM & 2:15 PM" with a chevron; opens other departures. "tap More departures and review all available departure times" (Help, answer 6142130) | `…new-1.jpg` |
| Alerts | A card with an amber border and a pale amber fill: bold amber title, "+1 alert", two lines of body with ellipsis | Sydney image |
| Intermediate stops | Collapsed row "⌄ Ride 5 stops (7 min)"; expands in place to list the stops along the bar | both |
| Alighting stop | Stop name, arrival time right-aligned, live crowding ("Live: As busy as it gets", magenta people icon), then "Follow signs for Way Out: Lawson St (Left) and Gibbons St (Right)" and "Exit via Gibbons St" | Sydney image |

A walking leg is one row: icon, "Walk 10 min (600 m)", chevron. The chevron opens the turn list for that leg. A "Live View" chip can sit under it (`google-2020-live-view-transit-frame15.jpg`). An "Also by" strip under a long walk offers car and ride-hail tiles with times and prices (same frame).

### 5.3 The map for a transit route (*verified*)

`…search-redesign-3.jpg`, `aa-2025-09-pt-directions-new-2.jpg`, `aa-2023-12-transit-enter-station.jpg`, `-exit-station.jpg`:

| Element | Rendering |
|---|---|
| Ride leg | Solid polyline in the agency line colour, about 6dp wide, with a thin darker casing |
| Line label on the map | The same badge as in the list, placed on the line mid-leg ("28" on orange, "Yellow-S" on yellow, "4" on magenta) |
| Board, alight and transfer stops | White disc of about 12dp with a 2dp dark ring |
| Intermediate stops | Small white dots with a thin dark ring on the line, each with its name in bold dark text and a white halo ("Étienne Marcel", "Réaumur - Sébastopol") |
| Walking leg | Round blue dots, about 5dp at 10dp pitch |
| Alternative walking routes | The same dots in grey; white time callouts |
| In-station or uncertain path | Smaller grey dots (`aa-2023-12-transit-exit-station.jpg`, from the platform marker to the exit) |
| Origin | Grey disc with a darker ring, or the blue dot |
| Destination | Red pin; a small white disc marks the exact end of the path under it |
| Station entrance or exit | A 20dp green rounded-square icon showing an arrow entering a door, placed on the entrance; next to it a white label card with two lines, "Enter station" in bold and "via 2. Av. Corentin Cariou" in regular |
| Time callout | Rounded rectangle with a pointer; selected = deep blue fill (sampled `#061ED2`) with white text; alternatives = white fill with grey text. Holds the duration and, when relevant, the fare |
| Unrelated transit lines | The base map's transit layer stays visible underneath in thin agency colours |
| Camera | Fitted to the whole trip inside the free rectangle (section 2.2); when a step is tapped, zoomed to that step with the callout label visible |

Google's statement of intent: "you'll also see exactly where the station entrances and exits are, what side of the street they're on, and a clear walking route to and from it" in "over 80 cities" (Google blog, Nov 15 2023).

### 5.4 Trip in progress (*verified*, Android Authority Sep 26 2025)

- "Start" turns the detail into a live trip. Since Sept 2025 the trip can be minimised and the whole app used normally: "search, browse, and reroute without cancelling or restarting their current journey".
- While minimised, a status strip is attached under the bottom bar across the full width, about 50dp high: primary colour fill with white text, "Get off at Strasbourg - Saint-Denis · 2 stops · 2 min" and a chevron. Tapping it restores the trip.
- With no position fix the strip turns black and reads "GPS lost · Ride to Strasbourg - Saint-Denis", with "GPS lost" in pink.
- An "Other trip options" pill floats at the top of the map; it opens a reroute chooser where each alternative has its own "Start" button (`…new-3.jpg`).
- Entering a new destination mid-trip offers reroute options before the change is accepted.
- The 2017 baseline: "departure times, ETAs and a notification that tell you when to transfer or get off" (Google blog).

---

## 6. Walking guidance and indoor

### 6.1 Walking overview (*verified*, `…redesign-6.jpg`, `9to5-2025-03-google-maps-directions-redesign-2.jpg`)

- The route is drawn as blue dots; up to two alternatives as grey dots, each with a time callout.
- Summary: duration, distance, elevation gain and loss with up and down arrows ("↑ 840 ft ↓ 978 ft"), "via CA-1 N". The current version adds a flatness word ("Mostly flat") and a "Stairs" badge with a blue stairs icon when the route includes them.
- Steps list rows (shared with driving, `…redesign-5.jpg`): 24dp manoeuvre arrow in a 56dp column, instruction at about 16sp, an optional Street View thumbnail on the right (about 64 x 38dp), then a distance rule: the leg length in grey followed by a hairline to the right edge ("3.9 mi ─────").

### 6.2 Walking navigation (*verified*, `aa-2025-09-walking-directions-options-new-add-report-1.jpg`)

```
┌──────────────────────────────────────────┐
│  ┌────────────────────────────────────┐  │
│  │ ↰   0 m                       (🎤) │  │ banner: 8dp margins, 122dp high
│  │     toward [D992] Bd Charles       │  │ with a two-line road name,
│  │     de Gaulle / Bd du H…           │  │ radius ~16dp, grey #62626A
│  └────────────────────────────────────┘  │
│                 map                      │
├──────────────────────────────────────────┤
│ ( ✕ )        2 hr 53 min          ( ⑂ ) │ sheet: 56dp circle buttons
│              12 km · 6:23 PM             │
│ ⚠  Add a report                    [New] │ rows 75dp, hairline between
│ 👥 Share trip progress                   │
│ 🔍 Search along route                    │
│ ☰  Directions                            │
│ 🖼  Show satellite map              (  ○) │
│ ⚙  Settings                              │
└──────────────────────────────────────────┘
```

- Banner: a rounded card across the top. Arrow glyph at 32dp on the left; distance to the manoeuvre at about 20sp; the road name at about 24sp bold, two lines, with route shields inline. A white circular voice button of about 44dp on the right. Walking uses a neutral grey banner (sampled `#62626A`); driving uses dark teal (sampled `#02625E`, `play-2026-11-navigation.jpg`).
- Bottom sheet, collapsed: a 56dp outlined circle with X on the left (end navigation), remaining time centred and bold with distance and arrival time under it, a 56dp circle on the right for alternative routes. Pulling it up reveals an action list with 75dp rows: a 24dp icon, a label of about 18sp and a hairline that starts at the label.
- "Add a report" opens a modal sheet with a scrim and a two-column grid of large tiles (icon in a coloured disc + label), captioned "Only tap if it's safe to do so" (`…add-report-2.jpg`).

A known gap, as of Dec 2023: within a transit trip "Any associated walking is treated as dots on the map, period. There's no turn-by-turn navigation, the map doesn't flip while I walk" (Android Authority, Dec 20 2023). The Sept 2025 overhaul addressed minimising and rerouting; whether transit walking legs now get the banner is *unverified*.

### 6.3 The blue dot (*verified* in part)

- "The blue dot shows your location on the map. When Google Maps isn't sure about your location, a light blue circle shows around the blue dot … The smaller the circle, the more certain the app is" (Google Maps Help, answer 2839911).
- "If the blue dot isn't visible or is gray, Maps can't find your current location. Instead, Maps shows the last location you visited" (same page).
- The dot is drawn with a white ring and a soft shadow (`play-2026-11-transit-route-options.jpg`).
- The heading indicator is a translucent blue fan from the dot that narrows as compass confidence improves: *from memory, unverified* (the help page read does not describe it).
- In the Live View mini-map and in navigation the dot becomes a blue arrowhead (`google-2020-live-view-transit-frame75.jpg`).

### 6.4 Indoor level picker (*verified*, `aa-2025-09-pt-directions-new-7.jpg`, `-new-5.jpg`)

```
 0   15        59dp
 │    │          │
      ┌──────────┐ ─┐
      │   (0)    │  │ selected: 40dp tinted disc
      │          │  │ 48dp per level
      │   -1     │  │
      │          │  │
      │   -2     │  │ ~44dp wide white pill, full radius,
      │          │  │ soft shadow, scrolls vertically
      │   -3     │  │
      │          │  │
      │   -4     │ ─┘ last row cut off = scroll hint
      └──────────┘
```

- Position in the app: left edge, 15dp margin, vertically in the middle of the free map area (between the chip row and the sheet). It keeps that place whether or not a sheet is open.
- Google's documentation disagrees with itself on position, which shows it is not a fixed convention: the consumer Help page says "In the bottom left, choose between levels and floors"; the Android SDK default is "near the center right-hand edge of the screen"; the iOS SDK default is "near the bottom right".
- Look: one white vertical pill. Level labels are the building's own names (0, -1, -2), about 14sp medium, centred, 48dp per row. The selected level has a 40dp tinted disc (sampled `#AADEEA` in light; a dark teal disc in dark theme) and a darker label. Highest level on top.
- Size: about 4.5 rows are visible; the half row signals that the pill scrolls.
- Behaviour: appears only when the map is zoomed in far enough that a building's floor plan is shown ("Zoom in to the map until you see a floor plan", Help). "When two or more indoor maps are visible the level picker will apply to the building that is currently in focus, which is typically the one nearest the center of the screen. Each building has a default level which will be selected when the picker is first displayed" (Android SDK docs). Selecting a level swaps the floor plan and the POIs for that level; the outdoor map stays.
- Limitation noted by a reviewer in Zürich HB: "The layered view is also only available at a certain zoom level, so you can't see the whole station at once in the level-exploring view" (Six Colors, Sept 2024).

### 6.5 Routes across levels

- On the 2D map, Google does not draw a per-level route inside stations. The in-station part is a run of grey dots plus the entrance marker (5.3). Level changes are expressed only as text in the timeline: "Follow signs for…", "Exit via…", "Platform 5".
- Reviewer, Zürich HB: "Google doesn't offer any walking directions inside of the train station either … you can see which subterranean level track 33 is on … But it won't route you to anything" and there are "no labels for tracks of any kind" (Six Colors, Sept 2024).
- Level changes are shown properly only in the camera view. Indoor Live View shows a blue sign "Go down one level" with three stacked white chevrons pointing down, and a bottom card with a down arrow, "Go down one level to Floor 2", the distance ("15 ft") right-aligned, and the destination ("Gate E27", address, terminal) below (`google-2021-indoor-live-view-frame75.jpg`). Google lists "the nearest elevator and escalators, your gate, platform, baggage claim, check-in counters, ticket office, restrooms, ATMs" as targets (Google blog, Mar 30 2021). The same post says it "starts rolling out in the coming months in select airports, malls, and transit stations in Tokyo and Zurich".

### 6.6 Live View, now "Lens in Maps" (*verified*)

- Full-screen camera. Top: a 32dp dark circle with a back arrow, a centred title in white with a subtitle, an overflow circle.
- Overlays: a blue sign with the street name in white, three large white chevrons with a blue outline pointing along the path, a "This way" pill with a compass disc when the user faces the wrong way.
- Bottom quarter outdoors: a map clipped to a dome shape showing the blue arrowhead and the dotted route.
- Entry points: a "Live View" chip under a walking leg in the transit timeline; a "Live" button above the location button on the map (`9to5-2024-07-google-maps-android-redesign-3.jpg`).
- Gesture: "When you tilt your device, you can switch between Lens in Maps and the 2D map view. The tilt feature is on by default" (Help, answer 9332056).
- Google's own advice is to use it only at decision points: "when you start your journey, reach a turn, or you're about to arrive" (same page).

---

## 7. Stop and station sheet

Evidence here is thinner than elsewhere. No screenshot of a station's departures list was found.

**Verified:**

- A station is an ordinary place sheet. "Search for the station or tap it on the map" to get its departures (Help, answer 6142130).
- "Some transit stations show real-time departures while others show a schedule of departures" (same page).
- Colour semantics are the same as in the route list (4.4), including black for scheduled-only.
- "When it's available, you can find crowd level information under the name of the station" (same page). In the timeline this reads "Live: As busy as it gets" with a magenta people icon.
- A large station gets a "Directory" tab listing its shops (Six Colors, Sept 2024; a "Directory" chip is visible in `9to5-2024-05-google-maps-redesign-new-5.jpg`).
- A departure board search is being added in 2026: strings "Search destination", "Search destination or line", sheet title "From %1$s", a "Clear destination filter" control and the empty state "No departures heading to %1$s right now" (NerdsChalk APK teardown, Nov 2026; rollout unconfirmed).
- On the map, stations are labelled with the agency's mode symbol next to the name in bold dark text; bus stops are small blue rounded-square icons with a bus glyph (`aa-2023-12-transit-exit-station.jpg`).
- A large interchange is one place with one sheet. Reviewer: "there's no directory of the train station as a total entity, and no labels for tracks of any kind" (Six Colors).

**From memory, unverified:**

```
┌──────────────────────────────────────────┐
│ Zürich HB                      (↗) ( ✕ ) │
│ Train station · ♿                        │
│ [◆ Directions] [▲ Start] [🔖 Save]       │
│ Overview │ Departures │ Directory │ …    │
├──────────────────────────────────────────┤
│ [All] [S-Bahn] [IC] [Tram] [Bus]         │  mode or line filter chips
│ Trains                                   │  grouped by mode
│ [S8]  Pfäffikon SZ               3 min   │  badge · headsign · time
│       Platform 43/44 · On time           │  platform + coloured status
│ [IC1] Genève-Aéroport           12:32    │
│       Platform 7 · Scheduled             │
└──────────────────────────────────────────┘
```

- Departures are grouped by mode and then by line, each line showing its next two or three times, rather than as one chronological board.
- Tapping a departure opens the vehicle's stop sequence.

---

## 8. Visual language

### 8.1 Colour roles

All hex values are sampled from JPEG screenshots unless noted, so expect a few units of error.

**Interface, light theme:**

| Role | 2024 and earlier (blue) | Current (teal, 2025–26) |
|---|---|---|
| Primary: filled button, selected tab, links, directions FAB | `#1A72E9` | `#027A8A` |
| Primary container: tonal buttons, selected navigation indicator | `#D3E3FD` | `#D2F6FE` (indicator sampled `#C0E9F4`) |
| On primary container: active icon and label | `#0656CE` | `#024D58` |
| Grouped row container (place details) | none (hairlines) | `#EEF6F6` |
| Sheet and card surface | `#FFFFFF` | `#FFFFFF` |
| Bottom bar surface | pale blue-grey | `#EEF4F6` |
| Circular header buttons, neutral chips | `#F2F2F2` | same |
| Primary text | `#1C1C1C` | same |
| Secondary text | `#747474` | same |
| Hairline divider | about `#DADCE0` | removed inside containers |
| Drag handle | `#C9C9C9` | same |
| Navigation banner | n/a | walking `#62626A`, driving `#02625E` |

**Status** (meaning from Google Help):

| Meaning | Colour |
|---|---|
| On time, live; fast traffic | green `#1C7434` (large durations `#0C7C34`) |
| Early; medium traffic | orange `#8C5C14` for small text, `#DC6C04` for large durations |
| Delayed; heavy traffic | red `#CC2C24` (durations `#AC3424`) |
| Scheduled only | the normal text colour |
| Warning, modified schedule | amber triangle; alert card with amber border and pale amber fill |
| Live crowding | magenta people icon and label |

**Map, light theme** (2023 palette):

| Feature | Colour |
|---|---|
| Land | `#F6F6F6` |
| Water | `#8EDAEE` |
| Parks | `#C2F2D6` |
| Roads | blue-grey `#DADEE6`; motorways darker blue-grey |
| Selected route (driving) | `#0E4AFE` with a darker casing |
| Selected callout | `#061ED2` |
| Transit legs | the agency's line colour |
| Level picker selection | `#AADEEA` |

The palette change was widely criticised when it shipped: "Everything is washed out and pale … Has this been tested with people who have aging eyesight?" (top comment, 9to5Google Nov 29 2023).

**Dark theme** (`aa-2025-09-pt-directions-new-1.jpg`, `-new-5.jpg`):

- Sheet surface near-black (`#121216`) with a lighter elevated tone (`#323232`) for chips and round buttons.
- Primary text `#F4F4F4`, secondary `#9C9CA4`.
- Map: navy land `#1A2A3E`, lighter slate-blue blocks `#323E6E`, white labels.
- Line colours and the teal strip (`#027A8A`) are unchanged; line bars keep full saturation on the dark surface.
- Tonal buttons invert to a dark teal fill with pale text; the destructive "End" pill is pale pink in dark and solid red with white text in light.

### 8.2 Typography

The typeface is Google Sans / Google Sans Text, a proprietary face. Sizes were estimated from glyph heights; the ratios are more reliable than the absolute values.

| Role | Size | Weight | Ratio to caption |
|---|---|---|---|
| Stacked duration (current summary) | about 28sp number, 16sp unit | regular | 2.3 |
| Navigation banner road name | about 24sp | bold | 2.0 |
| Sheet title, place name | about 20sp (Material title-large is 22sp) | regular | 1.65 |
| Stop name in timeline, summary duration | about 18sp | regular or medium | 1.5 |
| Field text, list primary, route duration | about 16sp | regular or medium | 1.3 |
| Secondary lines, hints, time range | about 14sp | regular | 1.15 |
| Tab, chip and button labels | about 12–14sp | medium | 1.0–1.15 |
| Navigation bar labels, third line of a route row | about 12sp | medium | 1.0 |

Habits worth noting:

- Weight is used sparingly. Titles are regular, not bold; emphasis comes from size and colour.
- Durations are abbreviated ("1 hr 22", "1h 38", "6h 41m") and never wrap.
- In "12:05 pm" the digits are large and the period marker is small on a second line.
- Map labels carry a white halo. Station names are bold dark text; POI labels take their category colour.

### 8.3 Shape

| Element | Radius |
|---|---|
| Sheets (top corners) | 28dp |
| From/to card, navigation banner | 16dp |
| Search bar, buttons, home chips, level picker | full pill |
| Filter and dropdown chips | 8dp (Material chip default) |
| FABs: location, layers | circle; directions FAB is a rounded square of about 16dp radius |
| Grouped row containers (current) | about 20dp on the outer corners of a group, about 4dp between rows inside a group |
| Photos | about 12dp |
| Line badges | about 4dp, or the agency's own bullet shape |
| Map callouts | about 6dp with a pointer |

### 8.4 Elevation

- Three levels only: map; floating controls and sheets (soft, diffuse shadow, no outline); modal sheets (scrim of about 30–40% black over everything).
- Sticky header and footer inside a sheet get a hairline shadow only while content is scrolled beneath them.
- The current design replaces most hairline dividers with tonal containers (`9to5-2025-09-google-maps-m3-expressive-2.jpg`).

### 8.5 Iconography

- Material Symbols, outlined style, 24dp in rows and 20dp in tabs and chips. Mode icons are filled in the leg chain to read at small size.
- Manoeuvre arrows are heavier custom glyphs.
- The origin is always a hollow ring, the destination always a pin, both on the map and in the from/to card and timeline. The same shapes in three places is what links list and map.

### 8.6 Bars

- Bottom bar: 64dp high plus the gesture inset, three destinations, 24dp icons, 12sp labels, active indicator pill 64 x 32dp. "It's also not a tall Material 3 bar" (9to5Google Jul 31 2024); Material later made 64dp the standard height itself.
- Maps does not use Android dynamic colour: "The app still doesn't leverage Dynamic Color" (9to5Google Sep 17 2025). The palette is fixed.

---

## 9. What works and what frustrates, for public transport

### 9.1 Works well

1. **Map context is never lost.** Sheets with three detents keep the map visible in every state short of full expansion (9to5Google: "helps preserve context").
2. **All modes compared at once.** Tab labels carry each mode's duration (4.2).
3. **The leg chain.** One line of badges and walk subscripts summarises a trip and is reused as the detail header and as the collapsed trip bar.
4. **Agency line colours everywhere.** Badge, timeline bar and map polyline share one colour, so the three views are obviously the same thing.
5. **Live status by colour with a text qualifier.** The meaning does not depend on colour alone ("(delayed)").
6. **Entrance and exit by name.** "Enter via York St", "Exit via 2", plus a labelled entrance marker on the map.
7. **Boarding position.** A car diagram for the fastest exit; available on Zurich S-Bahn since Sept 2025 (IamExpat, Sep 27 2025).
8. **Trips survive browsing.** The Sept 2025 status strip: "commuters and public transit riders are no longer treated like second-class citizens" (Android Authority).
9. **Reachability.** Mode tabs and close button within thumb reach: "The mode transportation switcher has been moved to the bottom for improved reach" (9to5Google, Mar 7 2025).
10. **Several live departures.** "Google Maps shows several different trains' expected arrival times in real time", where Apple Maps shows two (Tom's Guide).

### 9.2 Frustrates

| Problem | Source |
|---|---|
| **In-station time is not counted.** "Google Maps doesn't calculate how long it takes to enter the station and get to the train track, or exit it. Some stations are huge and require a few minutes of walking — time that isn't calculated or shown" | Android Authority, Dec 2023 |
| **No vertical circulation.** "There is no info on escalators, stairs, or lifts, and no indicators for more accessible exits or correspondences" | same |
| **Walking legs are just dots.** No turn-by-turn, no map rotation, and "I have no idea if the walk is manageable or if it's pure uphill or downhill before picking it" | same |
| **A large station is one blob.** No routing inside Zürich HB, no track labels, and the level view only at high zoom | Six Colors, Sept 2024 |
| **Exit information is easy to miss.** "Google Maps does offer some information on which exit to use, but it's in small text and not really ideal" | Tom's Guide |
| **Platform is the only stop detail.** "Google does at least display the platform, so one point for doing the bare minimum". SBB Mobile adds sectors, car classes and "walking directions for changing trains, complete with diagrams of the platforms and passages" | Six Colors |
| **Wrong vehicle shown for shared corridors.** With alternative lines on one leg, "I only see the stops of the bus or tram that Maps thinks I took" | Android Authority, Dec 2023 |
| **Skips the imminent departure.** "Even if I was already at the station and the next bus was scheduled in four minutes … I'd see the 10-minute bus as the default" | same |
| **No transfer feasibility signal.** Nothing in any screenshot shows transfer slack or risk; a transfer is a text hint between two legs | observation, all timeline screenshots |
| **Filters are buried and feel minor.** The reviewer did not notice them for weeks | Android Authority, Dec 2023 |
| **Low-contrast map.** Pale palette, roads hard to see when zoomed out | 9to5Google comments, Nov 2023 |
| **Feature coverage is patchy.** Entrances in "over 80 cities"; boarding position only on some Zurich S-Bahn journeys, so it "has quite a way to go until it becomes a real competitor to local apps like SBB" | Google blog; IamExpat |
| **Wheelchair routes carry a disclaimer.** "Use caution – wheelchair-accessible directions may not always reflect real-world conditions" as a banner across the timeline | `google-au-2021-instation-directions-mobile.webp` |

The claim in the brief that Google uses one averaged point for a large interchange is consistent with the Zürich HB review (one place, no tracks, no internal routing), but no source read states how the stop coordinate is chosen. Treat the averaging itself as *unverified*.

---

## 10. Recommendations for Kante

### 10.1 Adopt, ranked

| # | Pattern | Build it like this |
|---|---|---|
| 1 | **Map always present; sheets, not pages** | One map layer. Full-screen only for text entry and the camera. |
| 2 | **Three-detent sheet** | Top radius 28px; handle 40 x 4px, 8px from the top, inside a 48px-high touch zone. Low detent = fitted to one whole content group (about 130px for a place, about 265px for a trip summary). Middle = 50% of the viewport. Expanded = top edge 54px below the top, never flush. No scrim. Fling over about 500px/s moves one detent in the fling direction. Content scrolls only at the expanded detent; pulling down at scroll-top drags the sheet. |
| 3 | **Camera padding follows the sheet** | On settle, refit the route or centre the pin in the rectangle between the top card and the sheet's top edge, with 24–40px of inner padding. |
| 4 | **Close in the sheet's top-right** | 32px circular tonal button, 20px right margin, 16px between header buttons; browser back does the same. |
| 5 | **Mode tabs with durations inside the sheet** | 48px row, icon 20px + abbreviated duration, 3px indicator with rounded top, last tab cut off to signal scroll. For Kante: Transit, Walk, Bike, perhaps Transit+Bike. |
| 6 | **Leg chain as the unit of identity** | Mode icon 20px + line badge (20px high, 4px radius, operator colour, bold 12px label, contrast-checked text colour); chevron separators; walk leg as a chip "🚶 4 min". Reuse it in the row, the detail header and the collapsed trip bar. |
| 7 | **Route row, current form** | Left column: stacked duration (28px number over 16px unit). Right: bold time range, leg chain, live line "in 3 min from Bern, Hirschengraben" with only the time coloured and the qualifier in brackets. Fare top-right. Row about 104px. |
| 8 | **Vertical timeline** | Rail centre 32px from the left; ride bar 16px wide in line colour with round ends; boarding node = mode symbol in a 24px white disc; alighting node = white disc in the bar end; walk = grey dots 9px at 18px pitch; content from 65px; dividers start at the content edge. |
| 9 | **Named entrance and exit, plus sign text** | "Enter via …", "Follow signs for …", "Exit via …" as their own lines; a labelled entrance marker on the map with a two-line callout card. |
| 10 | **Boarding position diagram** | Segmented train, recommended segment filled and labelled, caption with train length. Kante can use Swiss sector letters and formation data. |
| 11 | **Fixed bottom action bar in the detail** | 40px pills left, "Arrive 16:26 · 55 min" right. |
| 12 | **Minimisable trip with a status strip** | Full-width strip about 50px under the main UI: "Get off at X · 2 stops · 2 min"; a distinct state for lost position. |
| 13 | **Floating control placement** | Search pill 48px high with 12px margins; chip row 36px high, 12px below; layers 40px circle top-right at 16px; location 56px circle bottom-right, kept 16px above the sheet edge. |
| 14 | **Level picker** | Left edge, 15px margin, vertical pill about 44px wide, 48px per level, 40px tinted disc on the selected level, building's own level names, scrolls with a cut-off row. |
| 15 | **Status semantics** | Green on time, orange early, red delayed, neutral for scheduled-only, always with a word. |
| 16 | **Origin ring and destination pin shapes repeated** | The same two shapes in the from/to card, the timeline and the map. Use Kante's own marker art. |

### 10.2 Avoid

1. **Text-only level changes.** Do not reduce an in-station route to "Follow signs for…".
2. **Small grey exit text.** The exit name is a primary fact; give it the weight of a stop name.
3. **A station as a single point.** Never route to or from the centroid of an interchange.
4. **Zero-time transfers.** Do not present a transfer without its walking time and slack.
5. **A level view that disappears when zoomed out.**
6. **An opaque "best route" order with no paging.** Swiss users expect chronological connections with earlier and later.
7. **Category chips and commerce in the transport flow.** "Buy tickets" rows, ads and "Also consider" cards interrupt the timeline.
8. **A pale base map.** Keep road and platform contrast high.
9. **A page-wide accuracy disclaimer** in place of reliable accessibility data.
10. **Report-on-board chips** ("What's it like on board?") unless Kante has the data volume to make them meaningful.

### 10.3 Where Kante can clearly do better

| Area | Google today | Kante opportunity |
|---|---|---|
| Where to stand | Platform number; boarding position on a few lines | Exact bay, platform edge and sector on the map and in the timeline, for every stop that has the data |
| In-station walking | Grey dots and text; AR only in a few buildings | A real indoor route drawn per level, with stairs, escalators and lifts as explicit steps and the time each takes |
| Level switching | Manual picker; route not level-aware | Picker auto-follows the current step; steps on other levels drawn dimmed; a level chip on each step ("Level -1 → 0, escalator") |
| Whole-station view | Level view only at high zoom | Keep the selected level at any zoom, with an "all levels" overview |
| Transfer feasibility | None | Walking time vs. available time on every transfer, coloured with the same status semantics ("4 min walk · 7 min to change") |
| Walking legs in a transit trip | Dots, no guidance (as of 2023) | The same turn banner and heading-up map as standalone walking |
| Shared corridors | Shows one line's stops | Show "any of 6, 7, 8" and resolve to the boarded vehicle |
| Result order | Ranked, no paging | Chronological with earlier/later, plus a "fastest" marker |
| Station departures | One list per place; filter only now arriving | Grouped by platform or bay and direction, since that is what a rider at the stop needs |
| Stop detail | Platform only | Sectors, car classes, low-floor boarding positions |

### 10.4 Brand boundary

**Do not copy (Google-specific):**

- The Google wordmark and the "Google Maps" watermark on the map.
- The multicolour Maps pin mark in the search bar, and the red teardrop destination pin with the dark dot as drawn by Google.
- Google Sans, Google Sans Text and Product Sans. They are proprietary typefaces.
- Google's four-colour set (blue, red, yellow, green) and its exact app palettes: the blue `#1A73E8` family and the current teal `#027A8A` with `#D2F6FE`.
- The base-map style: its exact land, water, park and road colours and its POI pin set.
- Pegman, the Street View thumbnail treatment, and Google's 3D navigation vehicle.
- Product names and their marks: Live View, Lens in Maps, Immersive View, Ask Maps, Gemini spark icon.
- The AR overlay artwork (blue street sign, white chevrons).
- The on-board report chips and "Latest in the area" feed as named features.

**Fine to use (generic Material and common transport patterns):**

- Bottom sheets with detents, drag handles and sticky headers and footers.
- Search bar pill, filter chips, tabs with an underline indicator, FABs, a three-item bottom bar with a pill indicator.
- The Material shape scale (4, 8, 12, 16, 28px, full) and elevation levels.
- Material Symbols icons, which are Apache 2.0 licensed; Kante may still prefer its own set for mode icons.
- Tonal containers in place of dividers.
- Vertical trip timelines, leg chains, line badges, dotted walking paths and time callouts. These predate Google and are used by SBB Mobile, Transit, Citymapper and others.
- Operator line colours and line names. They belong to the operators and come from the timetable data, so they should be shown as supplied.
- Green, orange and red status semantics, with Kante's own hues.
- A blue dot with an accuracy circle. It is an industry convention; pick Kante's own blue and ring.

---

## 11. Wireframes of the key screens

Frame: 412 x 915dp. Vertical positions are dp from the top.

### 11.1 Home, sheet at the low detent

```
  0 ┌──────────────────────────────────────────┐
    │ 9:30                             ▾ ▮ 81% │ status bar ~37
 49 │ ╭──────────────────────────────────────╮ │
    │ │ ◆  Search here            🎤  ◎  (●) │ │ 48 high, margins 12, pill
 97 │ ╰──────────────────────────────────────╯ │
109 │ ╭──────╮╭────────────╮╭─────────╮╭────── │ chips 36 high, gap 8,
145 │ ╰ Home ╯╰ Restaurants╯╰ Apparel ╯╰ Shop  │ row bleeds off right
    │                                     ╭──╮ │
165 │                                     │◇ │ │ layers 40, right 16
    │                                     ╰──╯ │
    │ ╭───╮                                    │
    │ │ 0 │                                    │ level picker: left 15,
    │ │-1 │            M A P                   │ only over indoor plans
    │ │-2 │                                    │
    │ ╰───╯                               ╭──╮ │
575 │                                     │⊕ │ │ location 56
631 │                                     ╰──╯ │ 24 gap
655 │                                     ╔══╗ │ directions 56,
711 │                                     ╚══╝ │ rounded square
727 │ ╭──────────────────────────────────────╮ │ 16 gap; sheet radius 28
    │ │              ▬▬▬▬                    │ │ handle 40x4, 8 from top
    │ │ Latest in the area ⓘ          ☁ 11° │ │ peek ≈100
827 │ ├──────────────────────────────────────┤ │
    │ │  (📍)          🔖           ⊕        │ │ bar 64: icon 24,
    │ │ Explore        You       Contribute  │ │ indicator 64x32, label 12sp
891 │ ╰──────────────────────────────────────╯ │
915 └────────────── ▬▬▬▬▬▬ ────────────────────┘ gesture inset 24
```

### 11.2 Place sheet at the middle detent (50%)

```
  0 ┌──────────────────────────────────────────┐
 54 │ ╭──────────────────────────────────────╮ │
    │ │ Zürich HB, Bahnhofplatz, Zür…      ✕ │ │ 48 high
102 │ ╰──────────────────────────────────────╯ │
121 │          ╭───────────────────────╮       │ context chip 32 high
153 │          ╰ See nearby attractions╯       │
    │                                          │
    │                  📍  pin centred in the  │
    │                      free area (~28%)    │
    │ ┌────┐                                   │ thumbnail 90x52
457 │ ╭──────────────────────────────────────╮ │ sheet top = 50%, radius 28
465 │ │              ▬▬▬▬                    │ │
    │ │ Zürich HB                 (↗)  (✕)  │ │ title ~20sp; buttons 32,
    │ │ Train station · ♿                    │ │ gap 16, right margin 20
    │ │ ╭───────────╮╭───────╮╭──────╮╭───── │ │ action pills 40 high,
    │ │ ╰◆Directions╯╰▲ Start╯╰🔖 Save╯╰     │ │ first filled, left 16
    │ │ ┌────────────────────┐ ┌──────────── │ │
    │ │ │      photo         │ │   photo     │ │ carousel, gap 8,
    │ │ │                    │ │             │ │ radius ~12
915 └─┴─┴────────────────────┴─┴─────────────┴─┘
```

Current variant: the action pills leave the scroll and dock at the bottom edge of the sheet at every detent; tabs sit above the photos.

### 11.3 Sheet expanded (any content)

```
  0 ┌──────────────────────────────────────────┐
    │ 9:30       map sliver        ▾ ▮ 81%     │ map stays visible
 54 │ ╭──────────────────────────────────────╮ │ top edge at 54, never 0
 62 │ │              ▬▬▬▬                    │ │
    │ │ Title                     (↗)  (✕)  │ │ sticky header
    │ │ Overview │ Reviews │ Photos │ About  │ │ tabs 48, indicator 3
    │ ├──────────────────────────────────────┤ │
    │ │                                      │ │
    │ │   content scrolls here only          │ │ pull down at scroll-top
    │ │                                      │ │ → back to 50%
    │ ├──────────────────────────────────────┤ │ hairline shadow
851 │ │ ╭─────────╮ ╭──────╮                 │ │ sticky footer,
891 │ │ ╰ Primary ╯ ╰ Other╯                 │ │ pills 40 high
915 └─┴──────────────────────────────────────┴─┘
```

### 11.4 Transit route options

```
  0 ┌──────────────────────────────────────────┐
 54 │   ╭──────────────────────────────────╮   │ from/to card: margins 20,
    │   │ ◯  Your location              ⋮  │   │ 2 rows x 48, radius 16
    │   │ ┊  ───────────────────────       │   │
150 │   │ 📍 Bern, Bundesplatz          ⇅  │   │
    │   ╰──────────────────────────────────╯   │
167 │                                     ╭──╮ │ layers 40
    │        ○━━[9]━━○                    ╰──╯ │ route fitted between
    │               ┃         ╭───────╮        │ card and sheet:
    │               ○·····📍  │ 25 min│        │ line colour, white stop
    │                         ╰───────╯   ╭──╮ │ discs, dotted walk,
385 │                                     │⊕ │ │ callout
441 │                                     ╰──╯ │ location 56, 16 above sheet
457 │ ╭──────────────────────────────────────╮ │ sheet at 50%
    │ │              ▬▬▬▬                    │ │
    │ │ Public transport          (≡)  (✕)  │ │ title ~20sp, buttons 32
    │ │ 🚗 28 min  🚆 25 min  🚶 1h 38  🚲 3  │ │ tabs 48 high,
    │ │            ▔▔▔▔▔▔▔▔▔                 │ │ indicator 3 x ~60
    │ ├──────────────────────────────────────┤ │
    │ │ ↻ ╭───────────╮╭───────╮╭─────────╮  │ │ chips 32 high, radius 8
    │ │   ╰Leave now ▾╯╰Modes ▾╯╰Filter by▾╯ │ │
    │ │                                      │ │
    │ │ 25   9:45–10:10                 3.20 │ │ row ≈104 high, padding 20
    │ │ min  [🚶 4 min] › [9] › [12]         │ │ duration 28sp over 16sp
    │ │      in 3 min from Hirschengraben    │ │ time coloured by status
    │ │ ──────────────────────────────────── │ │ divider inset 20
    │ │ 30   9:52–10:22                 3.20 │ │
915 └─┴──────────────────────────────────────┴─┘
```

### 11.5 Route detail timeline

See the measured drawing in section 5.1. Key numbers again, for a 412dp frame:

```
 0        32          65                              392  412
 │         │           │                                │   │
 │      rail centre    content start          right margin 20
 │
 │   ride bar 16 wide, line colour, round ends
 │   boarding node: mode symbol in a 24 white disc
 │   alighting node: white disc inside the bar end
 │   walk: grey dots 9, pitch 18
 │
 │   header (leg chain + ✕) ............ 60 high, sticky
 │   stop name ......................... ~18sp
 │   hint lines ........................ ~14sp grey
 │   badge ............................. 38 x 20, radius 4
 │   chip row .......................... 32 high
 │   boarding segment .................. 53 x 20 each
 │   "Ride 5 stops (7 min)" row ........ 56 high
 │   walk row .......................... 56 high
 │   bottom bar ........................ pills 40 high
```

### 11.6 Indoor level switcher in context

```
  0 ┌──────────────────────────────────────────┐
 49 │ ╭──────────────────────────────────────╮ │ search bar
 97 │ ╰──────────────────────────────────────╯ │
109 │ ╭──────╮╭────────────╮╭─────────╮        │ chips
    │ ╰──────╯╰────────────╯╰─────────╯   ╭──╮ │ layers 40
    │                                     ╰──╯ │
    │                                     ╭──╮ │ compass (when rotated)
    │   ┌─────────────────────────┐       ╰──╯ │
    │   │  station floor plan,    │            │
480 │╭────╮ level 0: shops,       │            │ picker: left 15,
    ││(0) │ passages, platform    │            │ ~44 wide, 48 per level,
    ││ -1 │ edges                 │            │ selected = 40 tinted disc
    ││ -2 │                       │            │
    ││ -3 │  ·····📍              │            │ ≈4.5 rows visible,
696 │╰────╯───────────────────────┘       ╭──╮ │ scrolls
    │ ┌────┐                              │⊕ │ │
    │ └────┘                              ╰──╯ │
727 │ ╭──────────────────────────────────────╮ │ sheet (any detent ≤ 50%)
915 └─┴──────────────────────────────────────┴─┘
```

Rules: shown only when a floor plan is on screen; applies to the building nearest the screen centre; opens on that building's default level; highest level at the top.

---

## 12. Not verified

- The search suggestion list: row anatomy, icons, distance placement, "Choose on map" (section 3.3). No screenshot found.
- The station sheet's departures list layout and grouping (section 7). Only Help text and teardown strings were found.
- Sheet motion: snap velocities, spring feel, scroll hand-off and whether back collapses one detent at a time. Detent positions are measured; the physics are Material defaults plus memory.
- Whether the map camera tracks the sheet during the drag or only on settle.
- The home sheet's middle and expanded detents.
- The blue dot's heading cone.
- The time picker's options (Arrive by, Last available).
- Whether transit walking legs now receive turn-by-turn banners after the Sept 2025 update.
- How Google chooses the coordinate of a large interchange.
- Font sizes: estimated from glyph heights in JPEGs, good to about ±2sp.
- Colour values: sampled from compressed screenshots, good to a few units per channel.
- The Play Store images are marketing renders. They show the current layout, but were not used for measurement.
- The Material Design website (m3.material.io) could not be read by a text fetch; Material numbers come from the Material Components for Android source and docs instead.
- Nothing here was checked on a device. Google ships layout changes server-side and per region, so a Swiss account may differ.
