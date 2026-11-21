#!/usr/bin/env python3
"""Rebuild every output of bern-research/transit from the official downloads.

Usage:  python scripts/run_all.py [--skip-fetch] [--offline]

  --skip-fetch  reuse the files already in .cache/ (otherwise all sources are downloaded again,
                about 560 MB, and the outputs then reflect the newest published versions)
  --offline     do not call transport.opendata.ch during validation

Python 3.11+, standard library only. `node` is used for one optional check when it is on PATH.
Takes about two and a half minutes after the downloads.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(*args: str) -> None:
    t0 = time.time()
    print(f"\n=== {' '.join(args)}", flush=True)
    res = subprocess.run([sys.executable, "-X", "utf8", str(HERE / args[0]), *args[1:]])
    if res.returncode != 0:
        sys.exit(f"{args[0]} failed with exit code {res.returncode}")
    print(f"=== done in {time.time() - t0:.0f} s", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-fetch", action="store_true")
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()

    run("fetch_sources.py", *(["--skip-existing"] if args.skip_fetch else []))
    for feed in ("fp2026", "fp2027"):
        run("extract_gtfs.py", "--feed", feed)
    run("build_stops.py")
    run("build_accessibility.py")
    for feed in ("fp2026", "fp2027"):
        run("build_timetable.py", "--feed", feed)
    run("slice_timetable.py", "--feed", "fp2026")      # the days left in the 2026 timetable year, a much smaller file
    run("write_manifest.py")
    flags = [] if args.offline else ["--online"]
    if shutil.which("node"):
        flags.append("--node")
    run("validate.py", *flags)
    return 0


if __name__ == "__main__":
    sys.exit(main())
