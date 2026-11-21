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

The journey sheet shows the whole trip top to bottom. Each boarding point gets a "Where to stand" card
(platform or bay, sectors, side of the road, floor level, next stop). Each walk and change has written
directions, the change time to spare and any change of floor. These ideas come from the Kante prototype
on the `nikitas-implementation` branch, rebuilt to run in this page without a server.

The data comes from the official ATLAS master data on [opentransportdata.swiss](https://opentransportdata.swiss)
(service points + traffic points), with floor levels from OpenStreetMap, and is stored in `platforms.js`.
To refresh it:

```bash
python3 tools/build_platforms.py
```
