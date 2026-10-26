"""Generated input fixtures (images, EXIF stamps, side files) and the data tables
that both build them and drive the assertions.
"""
from __future__ import annotations

import os
import time
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw
from PIL.ExifTags import IFD

from .infra import FIXTURES


def make_image(path, w, h, seed, label=""):
    im = Image.new("RGB", (w, h), ((seed * 37) % 256, (seed * 71) % 256, (seed * 131) % 256))
    d = ImageDraw.Draw(im)
    for i in range(0, max(w, h), 7):
        col = ((seed * 13 + i * 3) % 256, (i * 17 + seed * 5) % 256, (seed * 29 + i * 11) % 256)
        d.line(((i * 3 + seed) % w, (i * 11) % h, (i * 7 + 4) % w, (i * 5 + seed * 3) % h), fill=col, width=3)
    d.rectangle((4, 4, w - 5, h - 5), outline=(0, 0, 0), width=4)
    if label:
        d.rectangle((8, 8, 8 + 9 * len(label), 26), fill=(255, 255, 255))
        d.text((10, 10), label, fill=(0, 0, 0))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    im.save(path)


def stamp_mtime(path, when):
    ts = time.mktime((when.year, when.month, when.day, 12, 0, 0, 0, 0, -1))
    os.utime(str(path), (ts, ts))


def save_with_exif(path, taken, mtime, seed, w, h, label=""):
    im = Image.new("RGB", (w, h), ((seed * 37) % 256, (seed * 71) % 256, (seed * 131) % 256))
    d = ImageDraw.Draw(im)
    for i in range(0, max(w, h), 7):
        col = ((seed * 13 + i * 3) % 256, (i * 17 + seed * 5) % 256, (seed * 29 + i * 11) % 256)
        d.line(((i * 3 + seed) % w, (i * 11) % h, (i * 7 + 4) % w, (i * 5 + seed * 3) % h), fill=col, width=3)
    d.rectangle((4, 4, w - 5, h - 5), outline=(0, 0, 0), width=4)
    if label:
        d.rectangle((8, 8, 8 + 9 * len(label), 26), fill=(255, 255, 255))
        d.text((10, 10), label, fill=(0, 0, 0))
    exif = Image.Exif()
    stamp = taken.strftime("%Y:%m:%d %H:%M:%S")
    exif[IFD.Exif] = {36867: stamp, 36868: stamp}
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    im.save(path, exif=exif.tobytes())
    if mtime is not None:
        stamp_mtime(path, mtime)


JOIN_IMAGES = [
    ("01_first.jpg", 60, 100, 7, "P1 jpg 60x100"),
    ("02_mid.png", 120, 180, 3, "P2 png 120x180"),
    ("03_skip.gif", 40, 50, 9, "P3 gif 40x50"),
    ("10_last.jpg", 90, 130, 5, "P10 jpg 90x130"),
]
JOIN_SIZES = {name: (w, h) for name, w, h, _s, _l in JOIN_IMAGES}

TOC_FIXTURE = [
    (1, 0, "Getting Started"),
    (1, 1, "Installation"),
    (2, 1, "Hello, World"),
    (3, 0, "Programming a Guessing Game"),
]

SORT_FIXTURES = [
    ("sort-exif-2013-04-19-mtime-2001-01-01.jpg", date(2013, 4, 19), date(2001, 1, 1), 11, 64, 96),
    ("sort-exif-2020-12-25-mtime-2002-02-02.png", date(2020, 12, 25), date(2002, 2, 2), 13, 72, 88),
    ("sort-mtime-2002-07-01.jpg", None, date(2002, 7, 1), 17, 56, 80),
    ("sort-mtime-1999-12-31.png", None, date(1999, 12, 31), 19, 48, 64),
    ("nested/sort-nested-mtime-2003-03-03.jpg", None, date(2003, 3, 3), 23, 52, 76),
]
SORT_TOPLEVEL = [n for n, _e, _m, _s, _w, _h in SORT_FIXTURES if "/" not in n]

DEDUP_FIXTURES = [
    ("dd-unique-diag.jpg", 1, 90, 70, "uniq-diag"),
    ("dd-unique-checker.png", 2, 80, 110, "uniq-checker"),
    ("dd-unique-noise.jpg", 3, 100, 60, "uniq-noise"),
    ("dd-pair-a.jpg", 11, 64, 64, "dup-pair"),
    ("dd-pair-b.jpg", 11, 64, 64, "dup-pair"),
    ("dd-trip-a.jpg", 12, 70, 66, "dup-triple"),
    ("dd-trip-b.jpg", 12, 70, 66, "dup-triple"),
    ("dd-trip-c.jpg", 12, 70, 66, "dup-triple"),
]


def build_fixtures():
    for name, w, h, seed, label in JOIN_IMAGES:
        make_image(FIXTURES / "join" / "srcdir" / name, w, h, seed, label)
    (FIXTURES / "join" / "srcdir" / "notes.txt").write_text("not an image\n")

    toc = FIXTURES / "join" / "toc.yml"
    toc.parent.mkdir(parents=True, exist_ok=True)
    toc.write_text(
        "1:\n"
        "    - level: 0\n"
        "      title: 'Getting Started'\n"
        "    - level: 1\n"
        "      title: 'Installation'\n"
        "2:\n"
        "    - level: 1\n"
        "      title: 'Hello, World'\n"
        "3:\n"
        "    - level: 0\n"
        "      title: 'Programming a Guessing Game'\n"
    )

    conf = FIXTURES / "join" / "custom.yml"
    conf.parent.mkdir(parents=True, exist_ok=True)
    conf.write_text("out: custom-out.pdf\ndpi: 48\next:\n  - gif\n  - jpg\n")

    for name, exif_when, mt_when, seed, w, h in SORT_FIXTURES:
        path = FIXTURES / "sort" / "src" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if exif_when is None:
            make_image(path, w, h, seed, name)
        else:
            save_with_exif(path, exif_when, mt_when, seed, w, h, name)
        stamp_mtime(path, mt_when)

    for name, seed, w, h, label in DEDUP_FIXTURES:
        make_image(FIXTURES / "dedup" / "images" / name, w, h, seed, label)

    (FIXTURES / "dedup" / "README.txt").write_text("dedup ignores non-image entries\n")
