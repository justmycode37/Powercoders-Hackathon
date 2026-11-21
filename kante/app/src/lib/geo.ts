const R = 6371000;
const rad = Math.PI / 180;

export interface LatLon { lat: number; lon: number }
export type LngLat = [number, number];
/** [west, south, east, north] */
export type BBox = [number, number, number, number];

export function dist(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const x = (lon2 - lon1) * rad * Math.cos(((lat1 + lat2) / 2) * rad);
  const y = (lat2 - lat1) * rad;
  return Math.sqrt(x * x + y * y) * R;
}
export function bearing(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const x = (lon2 - lon1) * Math.cos(((lat1 + lat2) / 2) * rad);
  return (Math.atan2(x, lat2 - lat1) / rad + 360) % 360;
}
const COMPASS = ["north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west"];
/** "north", "south-west" … for a bearing in degrees. */
export const compass = (deg: number): string => COMPASS[Math.round((((deg % 360) + 360) % 360) / 45) % 8]!;

export function bboxOf(coords: Iterable<LngLat>): BBox | null {
  let w = Infinity, s = Infinity, e = -Infinity, n = -Infinity;
  for (const [x, y] of coords) {
    if (x < w) w = x;
    if (x > e) e = x;
    if (y < s) s = y;
    if (y > n) n = y;
  }
  return w === Infinity ? null : [w, s, e, n];
}
/** Distance in metres from a point to a polyline, and how far along it (0..1) the nearest point is. */
export function alongLine(p: LatLon, line: LngLat[]): { distM: number; frac: number } {
  let best = Infinity;
  let bestAt = 0;
  let total = 0;
  const lens: number[] = [];
  for (let i = 1; i < line.length; i++) {
    const l = dist(line[i - 1]![1], line[i - 1]![0], line[i]![1], line[i]![0]);
    lens.push(l);
    total += l;
  }
  let acc = 0;
  const k = Math.cos(p.lat * rad);
  for (let i = 1; i < line.length; i++) {
    const ax = (line[i - 1]![0] - p.lon) * k, ay = line[i - 1]![1] - p.lat;
    const bx = (line[i]![0] - p.lon) * k, by = line[i]![1] - p.lat;
    const dx = bx - ax, dy = by - ay;
    const len2 = dx * dx + dy * dy;
    const t = len2 ? Math.min(1, Math.max(0, -(ax * dx + ay * dy) / len2)) : 0;
    const cx = ax + dx * t, cy = ay + dy * t;
    const d = Math.sqrt(cx * cx + cy * cy) * rad * R;
    if (d < best) {
      best = d;
      bestAt = acc + lens[i - 1]! * t;
    }
    acc += lens[i - 1]!;
  }
  return { distM: best, frac: total ? bestAt / total : 0 };
}
/** "14 m", "65 m", "240 m", "1.4 km", "12 km" */
export function metres(m: number): string {
  if (m < 20) return `${Math.round(m)} m`;
  if (m < 100) return `${Math.round(m / 5) * 5} m`;
  if (m < 950) return `${Math.round(m / 10) * 10} m`;
  return `${(m / 1000).toFixed(m < 9950 ? 1 : 0)} km`;
}
