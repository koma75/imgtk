"""Date spec parsing and target-directory naming shared by the join/sort fixtures."""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

DATE_SPEC = re.compile(r"(exif|mtime)[-_](\d{4}-\d{2}-\d{2})")


def spec_date(name):
    hits = DATE_SPEC.findall(name)
    for kind, iso in hits:
        if kind == "exif":
            return kind, date(*map(int, iso.split("-")))
    kind, iso = hits[0]
    return kind, date(*map(int, iso.split("-")))


def target_dir_for(name, fmt=None, hierarch=False):
    _, when = spec_date(name)
    if hierarch:
        return Path(when.strftime("%Y")) / when.strftime("%m") / when.strftime("%d")
    return Path(when.strftime(fmt or "%Y-%m-%d"))
