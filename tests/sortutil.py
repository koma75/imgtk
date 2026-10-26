"""File-placement probes used by the sort suite (search + expected layout check)."""
from __future__ import annotations

import os
from pathlib import Path

from .dates import target_dir_for


def locate_under(root, basename):
    hits = []
    for dirpath, _dirs, files in os.walk(str(root)):
        for f in files:
            if f == basename:
                hits.append(os.path.relpath(os.path.join(dirpath, f), str(root)))
    return sorted(hits)


def sort_check(tgt, names, fmt=None, hierarch=False, label="sort"):
    for name in names:
        base = Path(name).name
        want = target_dir_for(base, fmt, hierarch) / base
        if not (tgt / want).exists():
            where = locate_under(tgt, base)
            raise AssertionError(
                "{0}: {1} expected at {2}, found at {3}".format(label, base, want, where or "nowhere")
            )
