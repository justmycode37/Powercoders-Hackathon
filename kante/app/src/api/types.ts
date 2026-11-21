// HTTP API contract between the Kante engine (Rust) and the web app.
// The server implements exactly these shapes; keep both sides in sync.
//
// Conventions
// - All timestamps are unix seconds (UTC). Display them in Europe/Zurich.
// - Coordinates are WGS84. Points are `lat`/`lon` fields; polylines are
//   `[lon, lat][]` (GeoJSON order) so they can be handed to MapLibre directly.
// - Durations are seconds, distances metres.
// - Fields marked optional are omitted when unknown or not applicable.

export type Mode =
  | "rail" | "tram" | "bus" | "metro" | "boat" | "funicular"
  | "cableway" | "rack" | "lift" | "ondemand" | "other";

/** How to draw a line badge. */
export interface LineBadge {
  /** Public line name: "IC 1", "S3", "10", "N17". May be empty for cableways. */
  name: string;
  /** Swiss product category: IC, IR, RE, S, T (tram), B (bus), BAT (boat), FUN, PB, GB, SL … */
  category: string;
  mode: Mode;
  operator: string;
}

// ---------------------------------------------------------------- places

export type PlaceKind = "station" | "address" | "poi" | "coord";

export interface Place {
  /** Stable id: "st:<id>" for stations, "addr:<…>", "poi:<…>", or "coord:<lat>,<lon>". */
  id: string;
  kind: PlaceKind;
  name: string;
  /** Second line: locality for addresses and POIs, e.g. "3011 Bern"; category for POIs. */
  detail?: string;
  lat: number;
  lon: number;
  /** Stations only: modes that call there, most important first. */
  modes?: Mode[];
  /** Present when the request carried a position: straight-line metres. */
  distM?: number;
}

/** GET /api/search?q=&lat=&lon=&limit=  (lat/lon optional: bias and distM) */
export interface SearchResponse {
  results: Place[];
}

/** GET /api/nearby?lat=&lon=&radius=&limit=&time=  → stations around a point with what leaves next (`time`: unix s, default now). */
export interface NearbyResponse {
  stations: NearbyStation[];
}
export interface NearbyStation {
  place: Place;
  distM: number;
  /** Next departures grouped by line + direction, soonest first (max ~6 groups). */
  lines: NearbyLine[];
}
export interface NearbyLine {
  line: LineBadge;
  headsign: string;
  /** Boarding point of the next departure. */
  quay: Quay;
  /** Next departure times (unix s), up to 3, live where available. */
  next: number[];
  live: boolean;
  /** Delay of the first departure in seconds, when live. */
  delayS?: number;
  tripId: string;
  serviceDate: string;
  /** Position of this stop in the trip's stop sequence. */
  seq: number;
}

/** GET /api/reverse?lat=&lon= → a Place (kind "coord") named after the nearest address or street. */
export type ReverseResponse = Place;

// ---------------------------------------------------------------- boarding points

/** How precisely the boarding position is known. */
export type QuayPrecision =
  /** Individual boarding point with its own surveyed coordinate. */
  | "edge"
  /** Boarding point is identified but only the stop's coordinate is known. */
  | "edge-at-station"
  /** Only the stop is known. */
  | "station";

/** A boarding point: bus bay, tram edge, rail track, pier. */
export interface Quay {
  /** Stable id (GTFS stop id). */
  id: string;
  /** National registry id (SLOID) of the boarding point or stop. */
  sloid: string;
  stationId: string;
  stationName: string;
  /** Sign text without sectors: "K1", "7". Empty when the edge is unsigned. */
  label: string;
  /** Rail sectors, e.g. "A-C". */
  sectors?: string;
  /** What to call it: "Gleis"/track for rail, bay for bus stations, edge for street stops, pier for boats. */
  noun: "track" | "bay" | "edge" | "pier" | "stop";
  lat: number;
  lon: number;
  precision: QuayPrecision;
  /** OSM level (0 = ground, -1 = one below …) when the point is linked to the walking network. */
  level?: number;
  /** Which side of the street / tracks the boarding point is on. */
  side?: QuaySide;
  /** Getting into the vehicle from this platform. */
  access?: "autonomous" | "assisted" | "assisted-on-notice" | "not-accessible";
  /** Modes that call at this boarding point. */
  modes: Mode[];
}

export interface QuaySide {
  /** Street or square the boarding point is on or beside; "" when unnamed. */
  street: string;
  /** Compass side of the roadway/track the boarding point is on. */
  side: "N" | "NE" | "E" | "SE" | "S" | "SW" | "W" | "NW";
  /** What the side refers to. */
  of: "road" | "tram-track" | "rail-track";
  /** Ready-made English sentence fragment: "north side of Bubenbergplatz", or "on Bubenbergplatz, south side of the road" for a stop on an island in a square. */
  text: string;
}

/** GET /api/quays?bbox=west,south,east,north → boarding points for the map (use at zoom ≥ 15). */
export interface QuaysResponse {
  quays: Quay[];
}

// ---------------------------------------------------------------- journey planning

export interface WalkOptions {
  /** Walking speed in m/s on level ground. Typical: 0.8 slow … 1.3 normal … 1.8 fast. */
  walkSpeed: number;
  /** "ok": stairs are fine; "avoid": fewer stairs when the detour is moderate; "never": step-free. */
  stairs: "ok" | "avoid" | "never";
  /** Allow escalators (false for wheelchairs, pushchairs, some luggage). */
  escalators: boolean;
  /** Wheelchair rules: also avoid ways tagged unsuitable and impassable barriers. */
  wheelchair: boolean;
}

export interface PlanOptions extends WalkOptions {
  /** Extra seconds added to every change on top of the walking time (default 120). */
  transferMarginS: number;
  /** Longest single walk to/from/between stops, minutes (default 20). */
  maxWalkMin: number;
  /** Modes to use; omit for all. */
  modes?: Mode[];
  /** Maximum number of changes (default 6). */
  maxTransfers?: number;
}

/** Either a place id from search, or a raw coordinate. */
export interface PlaceRef {
  id?: string;
  lat?: number;
  lon?: number;
  name?: string;
}

/** POST /api/plan */
export interface PlanRequest {
  /** Ignored when `onboard` is set. */
  from?: PlaceRef;
  to: PlaceRef;
  /** Unix seconds; omit for "now". */
  time?: number;
  /** `time` is the latest arrival instead of the earliest departure. */
  arriveBy?: boolean;
  /** "I'm already on this vehicle": plan from inside a running trip. */
  onboard?: OnboardRef;
  options: PlanOptions;
  /** Opaque cursor from a previous response (`earlier` / `later`). */
  page?: string;
}

export interface OnboardRef {
  tripId: string;
  /** Service date of the trip, YYYY-MM-DD. */
  serviceDate: string;
  /** Sequence index of the next stop the vehicle will reach (from /api/onboard); omit to derive from the clock. */
  nextSeq?: number;
}

export interface PlanResponse {
  from: Place;
  to: Place;
  journeys: Journey[];
  /** Walking the whole way, when that is a sensible option (under ~45 min). */
  walkOnly?: Journey;
  earlier?: string;
  later?: string;
  /** Server-side time spent, milliseconds. */
  tookMs: number;
  /** Live data was applied to this answer. */
  realtime: boolean;
}

export interface Journey {
  /** Stable for the same trips and stops across re-plans. */
  id: string;
  /** Leave the origin / arrive at the destination (unix s), including walking. */
  dep: number;
  arr: number;
  durationS: number;
  transfers: number;
  /** Total walking seconds and metres. */
  walkS: number;
  walkM: number;
  legs: Leg[];
  /** Something to warn about: cancelled leg, missed connection after delays, tight change. */
  alerts?: JourneyAlert[];
}

export interface JourneyAlert {
  severity: "info" | "warning" | "severe";
  kind: "delay" | "cancelled" | "platform-change" | "tight-change" | "missed-connection" | "other";
  /** Index into `legs` this alert refers to. */
  leg?: number;
  text: string;
}

export type Leg = RideLeg | WalkLeg;

export interface RideLeg {
  type: "ride";
  line: LineBadge;
  headsign: string;
  /** Train / course number when there is one. */
  number?: string;
  tripId: string;
  serviceDate: string;
  from: StopCall;
  to: StopCall;
  /** Calls strictly between `from` and `to`. */
  intermediate: StopCall[];
  /** Stop-to-stop polyline of the ridden part, `[lon, lat][]`. */
  geometry: [number, number][];
  /** The vehicle continues from the previous ride leg: stay seated, no change. */
  stayOnBoard?: boolean;
  /** The traveller is already on this vehicle (first leg of an on-board plan). `from` is then the next stop the vehicle reaches (its `arr` is when), not a boarding. */
  onboard?: boolean;
  /** Headway service (cableways …): runs about every `headwayS` seconds; times are indicative. */
  headwayS?: number;
  cancelled?: boolean;
  /** Real-time state of this ride. */
  live: "observed" | "predicted" | "timetable";
  /** Name of the next stop after boarding, and bearing of travel when leaving `from` (degrees, 0 = north). */
  towards?: string;
  bearing?: number;
}

export interface StopCall {
  /** Position in the trip's stop sequence. */
  seq: number;
  quay: Quay;
  /** Scheduled times (unix s). First call has no `arr`, last no `dep`. */
  arr?: number;
  dep?: number;
  /** Live deviation in seconds (positive = late); absent without live data. */
  arrDelayS?: number;
  depDelayS?: number;
  /** Set when live data moved the boarding point: the planned label. `quay` is then the new one. */
  plannedLabel?: string;
  /** Not served today. */
  skipped?: boolean;
  onRequest?: boolean;
}

/** A change at the same boarding point is a WalkLeg with durationS 0, distanceM 0 and no steps. */
export interface WalkLeg {
  type: "walk";
  /** access: origin → first stop; transfer: between vehicles; egress: last stop → destination; direct: whole trip on foot. */
  kind: "access" | "transfer" | "egress" | "direct";
  from: WalkPoint;
  to: WalkPoint;
  dep: number;
  arr: number;
  /** Walking time at the requested speed, including lifts/escalators/crossing waits; excludes the transfer margin. */
  durationS: number;
  distanceM: number;
  stairsUp: number;
  stairsDown: number;
  lifts: number;
  escalators: number;
  stepFree: boolean;
  /** Level changes on this walk that the map does not explain (no stairs, ramp or lift mapped): expect stairs. Omitted when 0. */
  unmappedLevelChanges?: number;
  /** Slack before the next departure after walking and margin (transfers and access), seconds. */
  slackS?: number;
  /** Official minimum transfer time for this change, when the timetable defines one. */
  officialMinS?: number;
  /** No routable path was found; time is estimated from the straight-line distance. */
  approximate?: boolean;
  /** `[lon, lat][]` */
  geometry: [number, number][];
  /** OSM level per vertex of `geometry` (0 ground, -1 below …); null where unknown (outdoors). */
  levels: (number | null)[];
  steps: WalkStep[];
}

export interface WalkPoint {
  name: string;
  lat: number;
  lon: number;
  /** Set when the point is a boarding point. */
  quay?: Quay;
}

export type WalkStepKind =
  | "depart" | "walk" | "cross" | "stairs-up" | "stairs-down"
  | "escalator-up" | "escalator-down" | "lift" | "ramp-up" | "ramp-down"
  | "enter" | "exit" | "platform" | "arrive";

export interface WalkStep {
  kind: WalkStepKind;
  /** English instruction: "Take the stairs down to level −1". */
  text: string;
  distM: number;
  durS: number;
  /** Street / passage name when there is one. */
  name?: string;
  /** Level at the start and end of the step (only where known). */
  level?: number;
  toLevel?: number;
  /** Slice of the leg's `geometry` this step covers (vertex indices, inclusive). */
  from: number;
  to: number;
}

/** POST /api/walk  { from: PlaceRef, to: PlaceRef, options: WalkOptions } → a "direct" WalkLeg */
export interface WalkRequest {
  from: PlaceRef;
  to: PlaceRef;
  options: WalkOptions;
}

// ---------------------------------------------------------------- departures and trips

/** GET /api/departures?station=<id>&time=&limit=  (or quay=<id>) */
export interface DeparturesResponse {
  station: Place;
  /** Every boarding point of the station, for the map. */
  quays: Quay[];
  departures: Departure[];
  realtime: boolean;
}

export interface Departure {
  line: LineBadge;
  headsign: string;
  number?: string;
  tripId: string;
  serviceDate: string;
  seq: number;
  /** Scheduled departure (unix s). */
  dep: number;
  /** Live data exists for this trip. */
  live: boolean;
  delayS?: number;
  cancelled?: boolean;
  /** Id of an entry in `quays`. */
  quayId: string;
  plannedLabel?: string;
  /** Next stop name: tells the direction on the street. */
  towards?: string;
  /** Bearing of travel when leaving the stop (degrees, 0 = north). */
  bearing?: number;
  headwayS?: number;
}

/** GET /api/trip?id=&date=YYYY-MM-DD */
export interface TripResponse {
  tripId: string;
  serviceDate: string;
  line: LineBadge;
  headsign: string;
  number?: string;
  calls: StopCall[];
  geometry: [number, number][];
  live: "observed" | "predicted" | "timetable";
  cancelled?: boolean;
  headwayS?: number;
}

// ---------------------------------------------------------------- vehicles and "I'm on board"

/**
 * GET /api/vehicles?bbox=west,south,east,north&t=
 * Vehicle positions are *estimates* interpolated from (live) stop times, not GPS.
 * Each vehicle comes as a short trajectory the client animates locally.
 */
export interface VehiclesResponse {
  t: number;
  vehicles: Vehicle[];
}
export interface Vehicle {
  tripId: string;
  serviceDate: string;
  line: LineBadge;
  headsign: string;
  /** Segment currently being travelled (or dwelt at): from → to between `dep` and `arr` (unix s). */
  from: [number, number];
  to: [number, number];
  dep: number;
  arr: number;
  nextStop: string;
  /** Sequence index of `nextStop` in the trip. */
  nextSeq: number;
  live: "observed" | "predicted" | "timetable";
}

/** GET /api/onboard?lat=&lon=&t=&q=  → vehicles the traveller is probably sitting in. `q` filters by line name. */
export interface OnboardResponse {
  candidates: OnboardCandidate[];
}
export interface OnboardCandidate {
  tripId: string;
  serviceDate: string;
  line: LineBadge;
  headsign: string;
  number?: string;
  /** Estimated distance between the traveller and the vehicle. */
  distM: number;
  /** Next stop the vehicle reaches and when. */
  nextSeq: number;
  nextStop: string;
  nextArr: number;
  /** Previous stop, for "between X and Y". */
  prevStop?: string;
  delayS?: number;
}

// ---------------------------------------------------------------- map overlays

/**
 * GET /api/indoor?bbox=west,south,east,north
 * Walkable network around a point for the station close-up (use at zoom ≥ 16):
 * a GeoJSON FeatureCollection of LineStrings with these properties.
 */
export interface IndoorFeatureProps {
  kind: "footway" | "sidewalk" | "crossing" | "path" | "pedestrian" | "steps"
    | "escalator" | "lift" | "corridor" | "platform" | "road";
  /** OSM level (may be fractional); null when untagged (ordinary outdoor way). */
  level: number | null;
  /** Second level for stairs/ramps/lifts that connect two levels. */
  toLevel?: number | null;
  indoor: boolean;
  name?: string;
}

/** GET /api/meta */
export interface MetaResponse {
  feedVersion: string;
  validFrom: string;
  validTo: string;
  /** Area with detailed walking data, `[west, south, east, north]`. */
  walkBbox: [number, number, number, number];
  realtime: { enabled: boolean; source?: string; updatedAt?: number; trips?: number; /** Last polling error, if the latest poll failed. */ error?: string };
  counts: { stations: number; quays: number; trips: number; walkEdges: number };
  attribution: string[];
}
