#!/usr/bin/env python3
"""Download the official source datasets into .cache/ and record provenance.

Usage:  python scripts/fetch_sources.py [--only NAME ...] [--skip-existing]

Each source lands in its own folder .cache/<name>/ next to a source.json holding the
resolved file name, HTTP Last-Modified/ETag, size, sha256 and fetch time. Nothing is
unpacked: later steps stream straight out of the GTFS zips.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import urllib.parse
import urllib.request

from common import CACHE, SOURCES, USER_AGENT


def fetch(name: str, skip_existing: bool) -> dict:
    src = SOURCES[name]
    folder = CACHE / name
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / src["file"]
    meta_path = folder / "source.json"
    if skip_existing and target.exists() and meta_path.exists():
        print(f"[skip] {name}")
        return json.loads(meta_path.read_text(encoding="utf-8"))

    req = urllib.request.Request(src["url"], headers={"User-Agent": USER_AGENT})
    sha = hashlib.sha256()
    size = 0
    tmp = target.with_suffix(target.suffix + ".part")
    with urllib.request.urlopen(req, timeout=120) as resp, open(tmp, "wb") as out:
        final_url = resp.geturl()
        headers = resp.headers
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
            sha.update(chunk)
            size += len(chunk)
    tmp.replace(target)

    # Permalinks redirect to a signed object URL; keep only the stable part (no signature query).
    resolved = urllib.parse.urlsplit(final_url)
    cd = headers.get("Content-Disposition") or ""
    m = re.search(r'filename="?([^";]+)', cd)
    meta = {
        "name": name,
        "title": src["title"],
        "publisher": src["publisher"],
        "licence": src["licence"],
        "used_for": src["used_for"],
        "landing_page": src["landing"],
        "request_url": src["url"],
        "resolved_file": m.group(1) if m else src["file"],
        "http_last_modified": headers.get("Last-Modified"),
        "http_etag": (headers.get("ETag") or "").strip('"') or None,
        "bytes": size,
        "sha256": sha.hexdigest(),
        "fetched_at_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "local_file": f".cache/{name}/{src['file']}",
    }
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[ok]   {name}: {meta['resolved_file']}  {size:,} bytes  last-modified={meta['http_last_modified']}")
    return meta


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="*", choices=sorted(SOURCES), help="fetch only these sources")
    ap.add_argument("--skip-existing", action="store_true", help="keep files already in .cache/")
    args = ap.parse_args()
    for name in args.only or SOURCES:
        fetch(name, args.skip_existing)
    return 0


if __name__ == "__main__":
    sys.exit(main())
