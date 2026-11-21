// Navigation helpers shared by the screens.
import type { Place } from "./api/types";
import { HERE, queryParams, type PlanQuery } from "./plan";
import { go } from "./router";
import { onboard, remember, type ActiveOnboard } from "./state";
import { nowS } from "./lib/time";

export function planTo(to: Place): void {
  remember(to);
  const ob = onboard.peek();
  const active = ob && ob.until > nowS() ? ob : null;
  const q: PlanQuery = {
    from: active ? null : HERE,
    to,
    time: null,
    arriveBy: false,
    onboard: active ? { tripId: active.tripId, serviceDate: active.serviceDate, ...(active.nextSeq !== undefined ? { nextSeq: active.nextSeq } : {}) } : null,
  };
  go("plan", queryParams(q));
}
export function openStation(id: string, quay?: string, opts?: { replace?: boolean }): void {
  go("station", { id, quay }, opts);
}
export function openTrip(id: string, date: string, seq?: number): void {
  go("trip", { id, date, seq });
}
/** Remember the vehicle the user sits in and ask where they are going. */
export function boardTrip(o: ActiveOnboard): void {
  onboard.value = o;
  go("search", { f: "to", ob: [o.tripId, o.serviceDate, o.nextSeq ?? ""].join("|").replace(/\|$/, "") });
}
