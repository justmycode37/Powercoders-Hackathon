"""Shared helpers: polite rate-limited HTTP with on-disk cache (cache is git-ignored)."""
import hashlib, json, os, time, urllib.error, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".cache")
DATA = os.path.join(ROOT, "data")
UA = "BernTransitRefBot/0.3 (hackathon station-reference research; low request rate)"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
_last = {}


def http(url, binary=False, data=None, minint=1.0, cache=True, timeout=120):
    key = hashlib.sha1((url + (data.decode() if data else "")).encode()).hexdigest()
    path = os.path.join(CACHE, "http", key[:2], key)
    if cache and os.path.exists(path):
        b = open(path, "rb").read()
        return b if binary else json.loads(b)
    host = urllib.parse.urlparse(url).netloc
    err = None
    for i in range(7):
        w = _last.get(host, 0) + minint - time.time()
        if w > 0:
            time.sleep(w)
        _last[host] = time.time()
        req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                b = r.read()
            break
        except urllib.error.HTTPError as e:
            err = e
            if e.code in (429, 502, 503, 504):
                ra = e.headers.get("Retry-After")
                s = int(ra) if ra and ra.isdigit() else 15 * (i + 1)
                print(f"  [{e.code}] {host} sleep {s}s", flush=True)
                time.sleep(min(s, 120))
                continue
            raise
        except Exception as e:  # network hiccup
            err = e
            print("  [err]", e, flush=True)
            time.sleep(5 * (i + 1))
    else:
        raise RuntimeError(f"failed {url}: {err}")
    if cache:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "wb").write(b)
    return b if binary else json.loads(b)


def commons(**p):
    p.update(format="json", formatversion="2", maxlag="5")
    return http(COMMONS_API + "?" + urllib.parse.urlencode(p), minint=3.0)


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def save(name, obj):
    os.makedirs(DATA, exist_ok=True)
    p = os.path.join(DATA, name)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    return p


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
