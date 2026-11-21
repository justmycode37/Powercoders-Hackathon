#!/usr/bin/env python3
"""Download the official source datasets into .cache/ and record provenance.

Usage:  python scripts/fetch_sources.py [--only NAME ...] [--skip-existing] [--resolve-only]

Each source lands in its own folder .cache/<name>/ next to a source.json holding the
resolved file name, HTTP Last-Modified/ETag, size, sha256 and fetch time. Nothing is
unpacked: later steps stream straight out of the GTFS zips.

The atlas files are republished every night under a new resource id, so their download
links are not stable. The link is therefore looked up on the dataset page by file name
at fetch time; the link stored in common.py is only the one that was valid on 2026-11-21.
--resolve-only prints the links that would be used and downloads nothing.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import urllib.request

from common import CACHE, OTD, SOURCES, USER_AGENT


def resolve_url(src: dict) -> str:
    """Current download link of an opentransportdata.swiss resource, found by file name on its dataset page."""
    url = src["url"]
    if not url.startswith(OTD) or url.endswith("/permalink"):
        return url                                  # permalinks and non-OTD sources are stable
    wanted = url.rsplit("/", 1)[-1]
    req = urllib.request.Request(src["landing"], headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        html = resp.read().decode("utf-8", "replace")
    links = re.findall(re.escape(OTD) + r"/dataset/[0-9a-f-]+/resource/[0-9a-f-]+/download/[^\"'<> ]+", html)
    for link in links:
        if link.rsplit("/", 1)[-1].lower() == wanted.lower():
            return link
    raise RuntimeError(f"no download link for {wanted} on {src['landing']} (found: {[l.rsplit('/', 1)[-1] for l in links]})")


def fetch(name: str, skip_existing: bool, resolve_only: bool = False) -> dict | None:
    src = SOURCES[name]
    folder = CACHE / name
    target = folder / src["file"]
    meta_path = folder / "source.json"
    if skip_existing and target.exists() and meta_path.exists():
        print(f"[skip] {name}")
        return json.loads(meta_path.read_text(encoding="utf-8"))

    url = resolve_url(src)
    if resolve_only:
        print(f"[link] {name}: {url}" + ("" if url == src["url"] else "   (changed since 2026-11-21)"))
        return None
    folder.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    sha = hashlib.sha256()
    size = 0
    tmp = target.with_suffix(target.suffix + ".part")
    with urllib.request.urlopen(req, timeout=120) as resp, open(tmp, "wb") as out:
        headers = resp.headers
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
            sha.update(chunk)
            size += len(chunk)
    tmp.replace(target)

    # Downloads redirect to a signed object URL; only the stable request URL is recorded.
    cd = headers.get("Content-Disposition") or ""
    m = re.search(r'filename="?([^";]+)', cd)
    meta = {
        "name": name,
        "title": src["title"],
        "publisher": src["publisher"],
        "licence": src["licence"],
        "used_for": src["used_for"],
        "landing_page": src["landing"],
        "request_url": url,
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
    ap.add_argument("--resolve-only", action="store_true", help="print the download links, download nothing")
    args = ap.parse_args()
    for name in args.only or SOURCES:
        fetch(name, args.skip_existing, args.resolve_only)
    return 0


if __name__ == "__main__":
    sys.exit(main())
