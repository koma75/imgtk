"""Dedup support: hash functions, expected-group computation, and directory-state probes."""
from __future__ import annotations

from functools import partial
from pathlib import Path

import imagehash
from PIL import Image

from .fixtures import DEDUP_FIXTURES

DEDUP_NAMES = [n for n, *_ in DEDUP_FIXTURES]
DEDUP_UNIQUE = [n for n, *_ in DEDUP_FIXTURES if n.startswith("dd-unique")]
HASH_FUNCS = {
    "ahash": imagehash.average_hash,
    "phash": imagehash.phash,
    "dhash": imagehash.dhash,
    "haar": imagehash.whash,
    "db4": partial(imagehash.whash, mode="db4"),
    "color": imagehash.colorhash,
    "crop": imagehash.crop_resistant_hash,
}


def image_hash(path, hashfunc, hash_size=None):
    im = Image.open(str(path))
    if hash_size is None:
        return str(hashfunc(im))
    return str(hashfunc(im, hash_size=hash_size))


def expected_groups(pairs, hashfunc, hash_size=None):
    groups = {}
    for name, path in pairs:
        groups.setdefault(image_hash(path, hashfunc, hash_size), set()).add(name)
    return {h: sorted(names) for h, names in groups.items() if len(names) > 1}


def dedup_state(root):
    loose, groups = set(), {}
    for entry in sorted(Path(root).iterdir()):
        if entry.is_dir():
            groups[entry.name] = sorted(f.name for f in entry.iterdir() if f.is_file())
        elif entry.is_file():
            loose.add(entry.name)
    return loose, groups
