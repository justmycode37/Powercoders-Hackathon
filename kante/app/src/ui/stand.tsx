import type { Quay } from "../api/types";
import { compass } from "../lib/geo";
import { cap, levelSpoken, levelText, quayNoun, sectors, sectorWord } from "../lib/lines";
import { Icon } from "./icons";

const ACCESS: Record<NonNullable<Quay["access"]>, { text: string; ok: boolean }> = {
  autonomous: { text: "Step-free boarding", ok: true },
  assisted: { text: "Boarding with staff assistance", ok: false },
  "assisted-on-notice": { text: "Boarding assistance must be booked ahead", ok: false },
  "not-accessible": { text: "Not wheelchair accessible", ok: false },
};

/** The plain sign of a boarding point: "Bay / C" on ink with the yellow edge. */
export function Sign({ quay, bearing, size }: { quay: Quay; bearing?: number; size?: "sm" }) {
  const noun = quayNoun(quay);
  return (
    <div class={"sign" + (quay.label ? "" : " unsigned") + (quay.label.length > 2 ? " long" : "") + (size ? " " + size : "")}>
      <span class="sign-noun">{noun}</span>
      {quay.label ? (
        <span class="sign-label">{quay.label}</span>
      ) : bearing !== undefined ? (
        <span class="sign-arrow" style={{ transform: `rotate(${bearing}deg)` }} role="img" aria-label={`Heading ${compass(bearing)}`}>
          <Icon name="arrow" size={size ? 20 : 30} />
        </span>
      ) : (
        <span class="sign-arrow" aria-hidden="true">
          <Icon name="dot" size={size ? 18 : 26} />
        </span>
      )}
    </div>
  );
}

/**
 * "Where to stand": the boarding point as a sign with everything known about
 * it in words — side of the street, sectors, level, which way the vehicle
 * leaves. It states only what the data knows: an unsigned stop gets no invented
 * label, an imprecise position gets a caveat.
 */
export function StandCard(props: { quay: Quay; towards?: string; bearing?: number; planned?: string; onShow?: () => void; kicker?: string; showStation?: boolean }) {
  const { quay: q, towards, bearing } = props;
  const changed = props.planned !== undefined && props.planned !== q.label;
  const level = levelText(q.level);
  const acc = q.access ? ACCESS[q.access] : null;
  const noun = quayNoun(q);
  const caveat =
    q.precision === "edge-at-station"
      ? `Exact ${q.noun === "edge" || q.noun === "stop" ? "waiting spot" : noun.toLowerCase() + " location"} unknown — map pin shows the stop`
      : q.precision === "station"
        ? "Exact platform or bay unknown — map pin shows the stop"
        : null;
  return (
    <div class="stand">
      <div class="stand-main">
        <Sign quay={q} bearing={bearing} />
        <div class="stand-info">
          <div class="stand-kicker">{props.kicker ?? "Where to stand"}</div>
          {q.side ? <div class="stand-side">{cap(q.side.text)}</div> : props.showStation && <div class="stand-side">{q.stationName}</div>}
          {(q.sectors || level) && (
            <div class="stand-tags">
              {q.sectors && (
                <span class="tag strong">
                  {sectorWord(q.sectors)} {sectors(q.sectors)}
                </span>
              )}
              {level && (
                <span class="tag" aria-label={cap(levelSpoken(q.level!))}>
                  {level}
                </span>
              )}
            </div>
          )}
          {towards && (
            <div class="stand-dir">
              {bearing !== undefined && q.label && (
                <span class="stand-compass" style={{ transform: `rotate(${bearing}deg)` }} role="img" aria-label={`Leaves heading ${compass(bearing)}`}>
                  <Icon name="arrow" size={14} />
                </span>
              )}
              <span>
                Next stop: <b>{towards}</b>
              </span>
            </div>
          )}
        </div>
      </div>
      {changed && (
        <div class="stand-note warn">
          <Icon name="alert" size={16} />
          {props.planned ? `Changed today (normally ${noun.toLowerCase()} ${props.planned})` : "Changed today"}
        </div>
      )}
      {caveat && (
        <div class="stand-note">
          <Icon name="info" size={16} />
          {caveat}
        </div>
      )}
      {(acc || props.onShow) && (
        <div class="stand-foot">
          {acc ? (
            <span class={"stand-acc" + (acc.ok ? " ok" : "")}>
              <Icon name="wheelchair" size={16} />
              {acc.text}
            </span>
          ) : (
            <span />
          )}
          {props.onShow && (
            <button class="link-btn" onClick={props.onShow}>
              Show on map <Icon name="right" size={14} />
            </button>
          )}
        </div>
      )}
    </div>
  );
}
