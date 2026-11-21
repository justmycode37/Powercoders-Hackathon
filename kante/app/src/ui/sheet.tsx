import { signal } from "@preact/signals";
import type { ComponentChildren } from "preact";
import { useEffect, useLayoutEffect, useRef } from "preact/hooks";
import { insets } from "../map/scene";
import { closeOverlay } from "../router";
import { Icon } from "./icons";

export type Detent = "low" | "mid" | "full";
/** Where the bottom sheet rests. */
export const detent = signal<Detent>("mid");
export function setDetent(d: Detent): void {
  if (!isWide.peek()) detent.value = d;
}

const wide = matchMedia("(min-width: 900px)");
export const isWide = signal(wide.matches);
wide.addEventListener("change", (e) => (isWide.value = e.matches));

/** The expanded sheet stops this far below the top, so a sliver of map stays visible. */
const TOP_GAP = 54;
/** Where the previous screen's sheet was, so the next one glides from there. */
let lastY: number | null = null;

// env(safe-area-inset-*) cannot be read from a custom property; measure a probe instead.
let probe: HTMLDivElement | null = null;
function safe(name: "top" | "bottom"): number {
  if (!probe) {
    probe = document.createElement("div");
    probe.style.cssText = "position:fixed;visibility:hidden;pointer-events:none;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)";
    document.body.appendChild(probe);
  }
  const cs = getComputedStyle(probe);
  return parseFloat(name === "top" ? cs.paddingTop : cs.paddingBottom) || 0;
}

export interface SheetProps {
  label: string;
  /** Stays in place while the body scrolls; the low detent is fitted to it. */
  header?: ComponentChildren;
  children: ComponentChildren;
  /** Pinned to the bottom of the screen at every detent. */
  footer?: ComponentChildren;
  initial?: Detent;
  /** Share of the viewport covered at the middle detent (default one half). */
  mid?: number;
  /** Pixels of the header that stick out above the sheet's top edge (the home search bar). */
  overhang?: number;
  /** Square top without a handle (home). */
  flat?: boolean;
  /** Called when the user has moved the sheet to another detent. */
  onDetent?: (d: Detent) => void;
  class?: string;
}

/**
 * Bottom sheet with three detents: low (fitted to the header), middle (half the
 * screen) and expanded (stopping short of the top). Dragging moves the element
 * with a transform only. The body scrolls only when expanded. On wide screens it
 * is a static side panel.
 */
export function Sheet(props: SheetProps) {
  const root = useRef<HTMLDivElement>(null);
  const head = useRef<HTMLDivElement>(null);
  const body = useRef<HTMLDivElement>(null);
  const foot = useRef<HTMLDivElement>(null);
  const y = useRef(0);
  const p = useRef(props);
  p.current = props;

  const positions = () => {
    const h = window.innerHeight;
    // a floating card at the top (from/to card, minimised guidance) stays visible above the expanded sheet
    const card = document.querySelector<HTMLElement>(".topcard") ?? document.querySelector<HTMLElement>(".gstrip");
    const over = p.current.overhang ?? 0;
    const full = Math.round(card ? card.getBoundingClientRect().bottom + 8 : safe("top") + TOP_GAP) + over;
    const grip = p.current.flat ? 0 : 20;
    const footH = foot.current?.offsetHeight ?? 0;
    const headH = head.current?.offsetHeight ?? 60;
    const low = Math.max(full + 40, h - grip - headH - footH - (footH ? 0 : safe("bottom")));
    const mid = Math.min(low, Math.max(full, Math.round(h * (1 - (p.current.mid ?? 0.5)))));
    return { full, mid, low, h, cardBottom: card ? full - over - 8 : safe("top") };
  };
  const moveFabs = (top: number, animate: boolean) => {
    const rail = document.getElementById("fab-rail");
    if (!rail) return;
    const h = window.innerHeight;
    const over = p.current.overhang ?? 0;
    rail.style.transition = animate ? "" : "none";
    rail.style.transform = `translate3d(0,${Math.round(top - over - h)}px,0)`;
    rail.classList.toggle("covered", top - over < h * 0.3);
  };
  const place = (d: Detent, animate: boolean) => {
    const el = root.current;
    if (!el) return;
    if (isWide.value) {
      el.style.transform = "";
      el.style.height = "";
      el.dataset.detent = "full";
      lastY = null;
      insets.value = { top: 0, bottom: 0, left: 0 };
      const rail = document.getElementById("fab-rail");
      if (rail) rail.style.transform = "";
      return;
    }
    const pos = positions();
    y.current = pos[d];
    lastY = y.current;
    el.style.height = `${pos.h - pos.full}px`;
    el.style.transition = animate ? "" : "none";
    el.style.transform = `translate3d(0,${y.current}px,0)`;
    el.dataset.detent = d;
    moveFabs(y.current, animate);
    const over = p.current.overhang ?? 0;
    insets.value = { top: pos.cardBottom, bottom: pos.h - y.current + over, left: 0 };
  };

  useLayoutEffect(() => {
    const el = root.current!;
    const from = lastY;
    if (props.initial) detent.value = props.initial;
    place(detent.peek(), false);
    // glide from where the previous screen's sheet was
    if (from !== null && !isWide.value && Math.abs(from - y.current) > 4) {
      const target = y.current;
      el.style.transform = `translate3d(0,${from}px,0)`;
      moveFabs(from, false);
      void el.offsetHeight;
      el.style.transition = "";
      el.style.transform = `translate3d(0,${target}px,0)`;
      moveFabs(target, true);
    }
  }, []);
  useEffect(() => {
    const unsub = detent.subscribe((d) => place(d, true));
    const unsubWide = isWide.subscribe(() => place(detent.peek(), false));
    const onResize = () => place(detent.peek(), false);
    window.addEventListener("resize", onResize);
    const ro = new ResizeObserver(() => {
      if (detent.peek() === "low") place("low", false);
    });
    if (head.current) ro.observe(head.current);
    if (foot.current) ro.observe(foot.current);
    return () => {
      unsub();
      unsubWide();
      window.removeEventListener("resize", onResize);
      ro.disconnect();
    };
  }, []);

  // drag
  useEffect(() => {
    const el = root.current!;
    let startY = 0, startX = 0, base = 0, mode: "" | "drag" | "native" = "";
    let samples: { t: number; y: number }[] = [];
    const begin = (cx: number, cy: number) => {
      startX = cx;
      startY = cy;
      base = y.current;
      mode = "";
      samples = [{ t: performance.now(), y: cy }];
    };
    const move = (cx: number, cy: number, target: EventTarget | null, ev: Event) => {
      const dy = cy - startY;
      if (mode === "") {
        const dx = cx - startX;
        if (Math.abs(dy) < 6 && Math.abs(dx) < 6) return;
        if (Math.abs(dx) > Math.abs(dy)) mode = "native";
        else if (detent.peek() === "full" && body.current?.contains(target as Node)) mode = body.current.scrollTop > 0 || dy < 0 ? "native" : "drag";
        else mode = "drag";
        if (mode === "drag") {
          el.style.transition = "none";
          el.classList.add("dragging");
        }
      }
      if (mode !== "drag") return;
      if (ev.cancelable) ev.preventDefault();
      const pos = positions();
      let ny = base + dy;
      if (ny < pos.full) ny = pos.full - Math.sqrt(pos.full - ny) * 2; // rubber band above the top
      if (ny > pos.low) ny = pos.low + (ny - pos.low) * 0.35;
      y.current = ny;
      el.style.transform = `translate3d(0,${ny}px,0)`;
      moveFabs(ny, false);
      const now = performance.now();
      samples.push({ t: now, y: cy });
      while (samples.length > 2 && now - samples[0]!.t > 120) samples.shift();
    };
    const end = () => {
      if (mode !== "drag") return;
      mode = "";
      el.classList.remove("dragging");
      const a = samples[0]!, b = samples[samples.length - 1]!;
      const v = b.t > a.t ? (b.y - a.y) / (b.t - a.t) : 0; // px per ms
      const pos = positions();
      const order: Detent[] = ["full", "mid", "low"];
      let best: Detent = order[0]!;
      for (const d of order) if (Math.abs(pos[d] - y.current) < Math.abs(pos[best] - y.current)) best = d;
      // a fling over 500 px/s moves one detent in its direction
      const cur = detent.peek();
      if (Math.abs(v) > 0.5) {
        const i = order.indexOf(cur) + (v > 0 ? 1 : -1);
        if (order[i] && (best === cur || order.indexOf(best) === i)) best = order[i]!;
      }
      if (best === cur) place(cur, true);
      else {
        detent.value = best;
        p.current.onDetent?.(best);
      }
    };
    const ts = (e: TouchEvent) => {
      if (isWide.value || e.touches.length !== 1) return;
      begin(e.touches[0]!.clientX, e.touches[0]!.clientY);
    };
    const tm = (e: TouchEvent) => {
      if (isWide.value || e.touches.length !== 1) return;
      move(e.touches[0]!.clientX, e.touches[0]!.clientY, e.target, e);
    };
    el.addEventListener("touchstart", ts, { passive: true });
    el.addEventListener("touchmove", tm, { passive: false });
    el.addEventListener("touchend", end);
    el.addEventListener("touchcancel", end);
    // mouse: drag by the header only
    const grip = el.querySelector(".sheet-top") as HTMLElement;
    const md = (e: PointerEvent) => {
      if (isWide.value || e.pointerType !== "mouse" || (e.target as Element).closest("button, a, input, [role=tab]")) return;
      begin(e.clientX, e.clientY);
      const mm = (ev: PointerEvent) => move(ev.clientX, ev.clientY, null, ev);
      const mu = () => {
        window.removeEventListener("pointermove", mm);
        window.removeEventListener("pointerup", mu);
        end();
      };
      window.addEventListener("pointermove", mm);
      window.addEventListener("pointerup", mu);
    };
    grip.addEventListener("pointerdown", md);
    const wheel = (e: WheelEvent) => {
      if (isWide.value) return;
      const d = detent.peek();
      let next: Detent | null = null;
      if (d !== "full" && e.deltaY > 0) next = "full";
      else if (d === "full" && e.deltaY < -30 && (body.current?.scrollTop ?? 0) <= 0) next = "mid";
      if (next) {
        detent.value = next;
        p.current.onDetent?.(next);
      }
    };
    el.addEventListener("wheel", wheel, { passive: true });
    return () => {
      el.removeEventListener("touchstart", ts);
      el.removeEventListener("touchmove", tm);
      el.removeEventListener("touchend", end);
      el.removeEventListener("touchcancel", end);
      grip.removeEventListener("pointerdown", md);
      el.removeEventListener("wheel", wheel);
    };
  }, []);

  const cycle = () => {
    const d = detent.peek();
    const next: Detent = d === "full" ? "mid" : "full";
    detent.value = next;
    props.onDetent?.(next);
  };
  return (
    <>
      <section class={"sheet" + (props.flat ? " flat" : "") + (props.footer ? " has-foot" : "") + (props.class ? " " + props.class : "")} ref={root} aria-label={props.label}>
        <div class="sheet-top">
          {!props.flat && (
            <button class="sheet-handle" onClick={cycle} aria-label={detent.value === "full" ? "Show more of the map" : "Expand panel"}>
              <span />
            </button>
          )}
          <div class="sheet-head" ref={head}>{props.header}</div>
        </div>
        <div class="sheet-body" ref={body}>
          {props.children}
          <div class="sheet-end" />
        </div>
        {props.footer && isWide.value && <div class="sheet-foot">{props.footer}</div>}
      </section>
      {props.footer && !isWide.value && (
        <div class="sheet-foot fixed" ref={foot}>
          {props.footer}
        </div>
      )}
    </>
  );
}

/** Circular close button for the top-right of a sheet header. */
export function SheetClose({ onClick, label = "Close" }: { onClick: () => void; label?: string }) {
  return (
    <button class="round-btn" onClick={onClick} aria-label={label}>
      <Icon name="close" size={18} />
    </button>
  );
}

/** Modal sheet with a scrim: traps focus, closes on Escape, scrim tap or Back. `full` covers the screen (option editing). */
export function Modal(props: { title: string; children: ComponentChildren; onClose?: () => void; full?: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  const close = props.onClose ?? closeOverlay;
  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null;
    const el = ref.current!;
    const focusables = () => [...el.querySelectorAll<HTMLElement>('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')].filter((x) => !x.hasAttribute("disabled"));
    (el.querySelector<HTMLElement>("[data-autofocus]") ?? el).focus({ preventScroll: true });
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        close();
      } else if (e.key === "Tab") {
        const f = focusables();
        if (!f.length) return;
        const first = f[0]!, last = f[f.length - 1]!;
        if (e.shiftKey && (document.activeElement === first || document.activeElement === el)) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("keydown", key);
      prev?.focus?.({ preventScroll: true });
    };
  }, []);
  return (
    <div class={"modal-layer" + (props.full ? " full" : "")}>
      <div class="modal-scrim" onClick={close} />
      <div class="modal" role="dialog" aria-modal="true" aria-label={props.title} ref={ref} tabIndex={-1}>
        {!props.full && <span class="modal-handle" aria-hidden="true" />}
        <div class="modal-head">
          <h2>{props.title}</h2>
          <button class="round-btn" onClick={close} aria-label="Close">
            <Icon name="close" size={18} />
          </button>
        </div>
        <div class="modal-body">{props.children}</div>
      </div>
    </div>
  );
}
