# Powercoders Hackathon

Team project for the Powercoders Hackathon.

## Getting started

```bash
git clone https://github.com/justmycode37/Powercoders-Hackathon.git
cd Powercoders-Hackathon
```

## Platforms and stop edges

The map shows the exact position of every train platform (Gleis) and bus/tram stop edge (Kante) in
Switzerland as small white dots once you zoom in close (zoom 17+). Tap one to see its next departures. Journeys start and end on the platform
the timetable gives, or, when it gives none, on the edge for the direction of travel.

The journey sheet has one card per step, swiped sideways. Ride cards show where to stand (sectors or
side of the road, floor level, next stop). Change cards show the time to spare, the walk and any change of
floor. The bar at the top shows the whole trip: each ride is a solid line with its name above it, and
walking, changing and waiting are rows of dots. The part already travelled fades.

On the map the journey is drawn the same way as in the Kante prototype on the `nikitas-implementation`
branch: each ride in its line colour, a circle at every stop, walks as a yellow band with arrows, a
"Platform 7" / "Bay C" sign where you board, and a marker where a walk changes floor. The base map and its
dark variant are the same as in that prototype, rebuilt to run in this page without a server.

The data comes from the official ATLAS master data on [opentransportdata.swiss](https://opentransportdata.swiss)
(service points + traffic points), with floor levels from OpenStreetMap, and is stored in `platforms.js`.
To refresh it:

```bash
python3 tools/build_platforms.py
```
