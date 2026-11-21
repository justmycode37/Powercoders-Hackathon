import { effect, signal, type Signal } from "@preact/signals";

/** A signal mirrored to localStorage. Storage can be missing or full; the app works without it. */
export function persisted<T>(key: string, initial: T): Signal<T> {
  let value = initial;
  try {
    const raw = localStorage.getItem(key);
    if (raw !== null) value = JSON.parse(raw) as T;
  } catch {
    /* unreadable: start fresh */
  }
  const s = signal<T>(value);
  let first = true;
  effect(() => {
    const v = s.value;
    if (first) {
      first = false;
      return;
    }
    try {
      if (v === null || v === undefined) localStorage.removeItem(key);
      else localStorage.setItem(key, JSON.stringify(v));
    } catch {
      /* quota or private mode */
    }
  });
  return s;
}

export function readJSON<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(key);
    return raw === null ? null : (JSON.parse(raw) as T);
  } catch {
    return null;
  }
}
export function writeJSON(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* ignore */
  }
}
