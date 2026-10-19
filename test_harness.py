#!/usr/bin/env python3
"""Test harness for the imgtk command line tool.

Exercises every subcommand advertised in README.md (join, sort, dedup)
against generated fixture images, then asserts on observable results
(PDF structure/outline, directory placement, duplicate grouping).

Layout:
    testharness/fixtures/   generated input images (join/, sort/, dedup/)
    testharness/runs/       per-scenario working dirs and tool outputs

Run:
    source .venv/bin/activate
    python test_harness.py [--only join|sort|dedup|opts] [--keep]
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import time
import unittest
from datetime import date
from pathlib import Path

import imagehash
from functools import partial

from PIL import Image, ImageDraw
from PIL.ExifTags import IFD

ROOT = Path(__file__).resolve().parent
TESTDIR = ROOT / "testharness"
FIXTURES = TESTDIR / "fixtures"
RUNS = TESTDIR / "runs"

FINDINGS: list[str] = []


def finding(msg):
    FINDINGS.append(msg)
    return msg


def require_deps():
    missing = []
    for mod in ("click", "fpdf", "imagehash", "yaml", "tqdm", "PIL"):
        if importlib.util.find_spec(mod) is None:
            missing.append(mod)
    if missing:
        sys.stderr.write(
            "missing runtime dependencies: {0}\n"
            "activate the project venv first:\n"
            "    source .venv/bin/activate && pip install -e .\n".format(", ".join(missing))
        )
        sys.exit(2)


require_deps()


def cli_prefix():
    entry = shutil.which("imgtk")
    if entry:
        return [entry]
    return [sys.executable, "-m", "imgtk.cli"]


def run_cli(args, cwd, expect_rc: int | None = 0):
    env = os.environ.copy()
    if shutil.which("imgtk") is None:
        env["PYTHONPATH"] = str(ROOT)
    proc = subprocess.run(
        cli_prefix() + [str(a) for a in args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        env=env,
    )
    if expect_rc is not None and proc.returncode != expect_rc:
        raise AssertionError(
            "cli exited {0} (expected {1}): {2}\nstdout={3}\nstderr={4}".format(
                proc.returncode,
                expect_rc,
                " ".join(map(str, args)),
                proc.stdout[-900:],
                proc.stderr[-900:],
            )
        )
    return proc.returncode, proc.stdout, proc.stderr


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


def scenario(name, src=None):
    root = RUNS / name
    if root.exists():
        shutil.rmtree(str(root))
    root.mkdir(parents=True, exist_ok=True)
    if src is not None:
        shutil.copytree(str(src), str(root / Path(src).name), dirs_exist_ok=True)
    return root


def wipe(path):
    if path.exists():
        shutil.rmtree(str(path))


def pdf_objects(data):
    return {int(m.group(1)): m.group(2) for m in re.finditer(rb"(?m)^(\d+)\s+0\s+obj\b(.*?)endobj", data, re.S)}


def pdf_page_order(data):
    objs = pdf_objects(data)
    node = None
    for body in objs.values():
        if re.search(rb"/Type\s*/Pages\b", body):
            node = body
            break
    if node is None:
        raise AssertionError("PDF has no /Type /Pages node")
    kids = re.search(rb"/Kids\s*\[([^\]]*)\]", node)
    if kids is None:
        raise AssertionError("PDF /Pages node has no /Kids array")
    return objs, [int(n) for n in re.findall(rb"(\d+)\s+0\s+R", kids.group(1))]


def pdf_pages(data):
    objs, order = pdf_page_order(data)
    out = []
    for num in order:
        body = objs[num]
        box = re.search(rb"/MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", body)
        if box is None:
            raise AssertionError("page object {0} has no MediaBox".format(num))
        w, h = float(box.group(3)), float(box.group(4))
        sizes = []
        res = re.search(rb"/Resources\s*(\d+)\s+0\s+R", body)
        if res:
            xobj = re.search(rb"/XObject\s*<<([^>]*)>>", objs[int(res.group(1))], re.S)
            if xobj:
                for ref in re.findall(rb"(\d+)\s+0\s+R", xobj.group(1)):
                    img = objs[int(ref)]
                    mw = re.search(rb"/Width\s+(\d+)", img)
                    mh = re.search(rb"/Height\s+(\d+)", img)
                    if mw and mh:
                        sizes.append((int(mw.group(1)), int(mh.group(1))))
        out.append((w, h, sizes))
    return out


def pdf_outlines(data):
    objs, order = pdf_page_order(data)
    index = {num: i + 1 for i, num in enumerate(order)}
    out = {}
    for body in objs.values():
        title = re.search(rb"/Title\s*\(([^)]*)\)", body)
        dest = re.search(rb"/Dest\s*\[\s*(\d+)\s+0\s+R", body)
        if title and dest:
            out[title.group(1).decode()] = index.get(int(dest.group(1)), -1)
    return out


def pdf_catalog(data):
    objs = pdf_objects(data)
    for body in objs.values():
        if re.search(rb"/Type\s*/Catalog\b", body):
            return body
    raise AssertionError("PDF has no /Type /Catalog object")


def pdf_page_layout(data):
    """/PageLayout name in the document catalog (PDF32000 Table 3.2), or None."""
    m = re.search(rb"/PageLayout\s*/([A-Za-z]+)", pdf_catalog(data))
    return m.group(1).decode() if m else None


def pdf_direction(data):
    """/Direction name in the catalog ViewerPreferences (PDF32000 Table 3.22), or None."""
    prefs = re.search(rb"/ViewerPreferences\s*<<(.*?)>>", pdf_catalog(data), re.S)
    if prefs is None:
        return None
    direction = re.search(rb"/Direction\s*/([A-Za-z0-9]+)", prefs.group(1))
    return direction.group(1).decode() if direction else None


def pdf_check(data):
    if not data.startswith(b"%PDF-"):
        raise AssertionError("output is not a PDF (missing %PDF- header)")
    if b"%%EOF" not in data[-1024:]:
        raise AssertionError("PDF is truncated (missing %%EOF trailer)")
    return data


def expect_pdf(work, pdf_name, expected_names, dpi, label):
    data = pdf_check((work / pdf_name).read_bytes())
    pages = pdf_pages(data)
    if len(pages) != len(expected_names):
        raise AssertionError(
            "{0}: PDF has {1} pages, expected {2} ({3})".format(
                label, len(pages), len(expected_names), ", ".join(expected_names)
            )
        )
    for i, name in enumerate(expected_names, 1):
        got_w, got_h, sizes = pages[i - 1]
        want_w, want_h = JOIN_SIZES[name]
        for got, want_px, unit in ((got_w, want_w, "width"), (got_h, want_h, "height")):
            want_pt = want_px * 72.0 / dpi
            if abs(got - want_pt) > 0.05:
                raise AssertionError(
                    "{0}: page {1} {2} MediaBox is {3}pt, expected {4:.2f}pt ({5}px at {6}dpi)".format(
                        label, i, unit, got, want_pt, want_px, dpi
                    )
                )
        if len(sizes) != 1:
            raise AssertionError("{0}: page {1} embeds {2} images (expected 1)".format(label, i, len(sizes)))
        if sizes[0] != (want_w, want_h):
            raise AssertionError(
                "{0}: page {1} embeds a {2}x{3}px image, expected {4}x{5}px for {6}".format(
                    label, i, sizes[0][0], sizes[0][1], want_w, want_h, name
                )
            )
    return data


def expect_pdf_toc(data, toc_entries, label):
    outlines = pdf_outlines(data)
    for pagenum, level, title in toc_entries:
        if title not in outlines:
            raise AssertionError("{0}: PDF outline is missing entry {1!r}".format(label, title))
        if outlines[title] != pagenum:
            raise AssertionError(
                "{0}: outline entry {1!r} points at page {2} (expected {3})".format(label, title, outlines[title], pagenum)
            )
    return outlines




# ================================================================ join tests
JOIN_ORDER_DEFAULT = ["01_first.jpg", "02_mid.png", "10_last.jpg"]
JOIN_ORDER_GIF = ["01_first.jpg", "02_mid.png", "03_skip.gif", "10_last.jpg"]
JOIN_ORDER_CUSTOM = ["01_first.jpg", "03_skip.gif", "10_last.jpg"]


class JoinTests(unittest.TestCase):
    def test_join_generates_default_config(self):
        root = scenario("join_default", src=FIXTURES / "join")
        rc, out, err = run_cli(["join", "join/srcdir", "-o", "out.pdf"], cwd=root)
        cfg = root / "imgtk-join.yml"
        self.assertTrue(cfg.exists(), "join did not create ./imgtk-join.yml when no config existed")
        self.assertEqual(
            cfg.read_text(),
            "out: output.pdf\ntoc: toc.yml\ndpi: 96\next:\n  - jpg\n  - jpeg\n  - png\n"
            "page_layout: TwoPageLeft\ndirection: R2L\n",
            "generated default config does not match the defaults documented in README.md",
        )
        expect_pdf(root, "out.pdf", JOIN_ORDER_DEFAULT, 96, "default config")

    def test_join_filters_directory_by_extension(self):
        root = scenario("join_ext", src=FIXTURES / "join")
        rc, out, err = run_cli(["join", "join/srcdir", "-o", "filtered.pdf"], cwd=root)
        data = expect_pdf(root, "filtered.pdf", JOIN_ORDER_DEFAULT, 96, "config ext filter")
        pages = pdf_pages(data)
        self.assertEqual(len(pages), 3, "jpg/jpeg/png ext filter should pick 3 of the 5 directory entries")
        self.assertEqual(sorted(s for _w, _h, sizes in pages for s in sizes),
                         [(60, 100), (90, 130), (120, 180)],
                         "ext filter embedded the wrong images")

    def test_join_ext_option_adds_extension(self):
        root = scenario("join_extopt", src=FIXTURES / "join")
        rc, out, err = run_cli(["join", "join/srcdir", "-o", "withgif.pdf", "-e", "gif"], cwd=root)
        expect_pdf(root, "withgif.pdf", JOIN_ORDER_GIF, 96, "cli -e gif")

    def test_join_directory_entries_sort_numerically(self):
        root = scenario("join_order", src=FIXTURES / "join")
        rc, out, err = run_cli(["join", "join/srcdir", "-o", "ordered.pdf"], cwd=root)
        data = expect_pdf(root, "ordered.pdf", JOIN_ORDER_DEFAULT, 96, "numeric ordering")
        self.assertNotEqual(
            pdf_pages(data)[1][2], [JOIN_SIZES["10_last.jpg"]],
            "02_mid.png must sort before 10_last.jpg numerically",
        )

    def test_join_explicit_files_keep_given_order(self):
        root = scenario("join_explicit", src=FIXTURES / "join")
        rc, out, err = run_cli(
            ["join", "join/srcdir/10_last.jpg", "join/srcdir/01_first.jpg", "-o", "explicit.pdf"],
            cwd=root,
        )
        expect_pdf(root, "explicit.pdf", ["10_last.jpg", "01_first.jpg"], 96, "explicit file order")

    def test_join_pdf_outline_from_toc(self):
        root = scenario("join_toc", src=FIXTURES / "join")
        rc, out, err = run_cli(["join", "join/srcdir", "-o", "withtoc.pdf", "-t", "join/toc.yml"], cwd=root)
        data = expect_pdf(root, "withtoc.pdf", JOIN_ORDER_DEFAULT, 96, "toc outline")
        outlines = expect_pdf_toc(data, TOC_FIXTURE, "toc outline")
        self.assertEqual(len(outlines), len(TOC_FIXTURE),
                         "PDF outline has {0} entries, toc fixture declares {1}".format(len(outlines), len(TOC_FIXTURE)))

    def test_join_config_file_supplies_defaults(self):
        root = scenario("join_custom", src=FIXTURES / "join")
        rc, out, err = run_cli(["join", "join/srcdir", "-c", "join/custom.yml"], cwd=root)
        self.assertTrue((root / "custom-out.pdf").exists(), "config 'out:' key was not used as the PDF filename")
        self.assertFalse((root / "output.pdf").exists(), "tool ignored the config 'out:' key")
        expect_pdf(root, "custom-out.pdf", JOIN_ORDER_CUSTOM, 48, "custom config out/dpi/ext keys")

    def test_join_dpi_option_scales_pages(self):
        root = scenario("join_dpi", src=FIXTURES / "join")
        run_cli(["join", "join/srcdir", "-o", "dpi96.pdf"], cwd=root)
        run_cli(["join", "join/srcdir", "-o", "dpi48.pdf", "-d", "48"], cwd=root)
        base = pdf_pages(expect_pdf(root, "dpi96.pdf", JOIN_ORDER_DEFAULT, 96, "default dpi"))
        half = pdf_pages(expect_pdf(root, "dpi48.pdf", JOIN_ORDER_DEFAULT, 48, "-d 48"))
        self.assertEqual([p[2] for p in base], [p[2] for p in half], "-d 48 changed the embedded image sizes")
        for i in range(len(base)):
            self.assertAlmostEqual(half[i][0], base[i][0] * 2, delta=0.1,
                                   msg="page {0} width not doubled by -d 48: {1} vs {2}".format(i + 1, half[i][0], base[i][0]))
            self.assertAlmostEqual(half[i][1], base[i][1] * 2, delta=0.1,
                                   msg="page {0} height not doubled by -d 48: {1} vs {2}".format(i + 1, half[i][1], base[i][1]))

    def test_join_bad_extension_entry_does_not_crash(self):
        root = scenario("join_txt", src=FIXTURES / "join")
        rc, out, err = run_cli(["join", "join/srcdir", "-o", "txt.pdf", "-e", "txt"], cwd=root)
        self.assertEqual(rc, 0, "join should survive unreadable entries in the directory")
        data = expect_pdf(root, "txt.pdf", JOIN_ORDER_DEFAULT, 96, "txt entry skipped")
        self.assertEqual(len(pdf_pages(data)), 3, "notes.txt must never become a PDF page")

    def test_join_catalog_viewer_defaults_documented(self):
        root = scenario("join_catalog", src=FIXTURES / "join")
        rc, out, err = run_cli(["join", "join/srcdir", "-o", "spread.pdf"], cwd=root)
        data = expect_pdf(root, "spread.pdf", JOIN_ORDER_DEFAULT, 96, "catalog defaults")
        self.assertEqual(pdf_page_layout(data), "TwoPageLeft",
                         "default /PageLayout is {0}, README documents TwoPageLeft".format(pdf_page_layout(data)))
        self.assertEqual(pdf_direction(data), "R2L",
                         "default /Direction is {0}, README documents R2L".format(pdf_direction(data)))

    def test_join_page_layout_option(self):
        root = scenario("join_layout", src=FIXTURES / "join")
        rc, out, err = run_cli(["join", "join/srcdir", "-o", "single.pdf", "--page-layout", "SinglePage"], cwd=root)
        data = expect_pdf(root, "single.pdf", JOIN_ORDER_DEFAULT, 96, "--page-layout SinglePage")
        self.assertEqual(pdf_page_layout(data), "SinglePage",
                         "--page-layout SinglePage produced /PageLayout {0}".format(pdf_page_layout(data)))
        run_cli(["join", "join/srcdir", "-o", "twocol.pdf", "-P", "TwoColumnRight"], cwd=root)
        data = expect_pdf(root, "twocol.pdf", JOIN_ORDER_DEFAULT, 96, "-P TwoColumnRight")
        self.assertEqual(pdf_page_layout(data), "TwoColumnRight",
                         "-P TwoColumnRight produced /PageLayout {0}".format(pdf_page_layout(data)))
        run_cli(["join", "join/srcdir", "-o", "l2r.pdf", "-D", "L2R"], cwd=root)
        data = expect_pdf(root, "l2r.pdf", JOIN_ORDER_DEFAULT, 96, "-D L2R")
        self.assertEqual(pdf_direction(data), "L2R",
                         "-D L2R produced /Direction {0}".format(pdf_direction(data)))

    def test_join_catalog_keys_from_config(self):
        root = scenario("join_catalogcfg", src=FIXTURES / "join")
        (root / "catalog.yml").write_text(
            "out: cfgcatalog.pdf\npage_layout: twocolumnleft\ndirection: l2r\n"
            "ext:\n  - jpg\n  - png\n")
        rc, out, err = run_cli(["join", "join/srcdir", "-c", "catalog.yml"], cwd=root)
        data = expect_pdf(root, "cfgcatalog.pdf", JOIN_ORDER_DEFAULT, 96, "config page_layout/direction keys")
        self.assertEqual(pdf_page_layout(data), "TwoColumnLeft",
                         "config 'page_layout: twocolumnleft' produced /PageLayout {0}".format(pdf_page_layout(data)))
        self.assertEqual(pdf_direction(data), "L2R",
                         "config 'direction: l2r' produced /Direction {0}".format(pdf_direction(data)))
        # command line takes precedence over the configuration file
        rc, out, err = run_cli(["join", "join/srcdir", "-c", "catalog.yml", "-D", "R2L", "-o", "cfgcli.pdf"], cwd=root)
        data = expect_pdf(root, "cfgcli.pdf", JOIN_ORDER_DEFAULT, 96, "cli -D overrides config direction")
        self.assertEqual(pdf_direction(data), "R2L",
                         "cli --direction did not override the config value: {0}".format(pdf_direction(data)))
        self.assertEqual(pdf_page_layout(data), "TwoColumnLeft",
                         "config page_layout was dropped when only --direction was given")

    def test_join_catalog_entries_can_be_disabled(self):
        root = scenario("join_nocat", src=FIXTURES / "join")
        rc, out, err = run_cli(["join", "join/srcdir", "-o", "plain.pdf", "-P", "none", "-D", "none"], cwd=root)
        data = expect_pdf(root, "plain.pdf", JOIN_ORDER_DEFAULT, 96, "-P none -D none")
        self.assertIsNone(pdf_page_layout(data),
                          "--page-layout none must remove /PageLayout, found {0}".format(pdf_page_layout(data)))
        self.assertIsNone(pdf_direction(data),
                          "--direction none must remove /Direction, found {0}".format(pdf_direction(data)))

    def test_join_none_differs_from_omitted_config_key(self):
        root = scenario("join_nonecfg", src=FIXTURES / "join")
        (root / "nonecfg.yml").write_text("out: nonecfg.pdf\next:\n  - jpg\n  - png\npage_layout: none\n")
        rc, out, err = run_cli(["join", "join/srcdir", "-c", "nonecfg.yml"], cwd=root)
        data = expect_pdf(root, "nonecfg.pdf", JOIN_ORDER_DEFAULT, 96, "config page_layout: none")
        self.assertIsNone(pdf_page_layout(data),
                          "'page_layout: none' left /PageLayout {0} in the catalog".format(pdf_page_layout(data)))
        self.assertEqual(pdf_direction(data), "R2L",
                          "omitted direction key must fall back to the R2L default: {0}".format(pdf_direction(data)))

    def test_join_failed_write_leaves_no_partial_file(self):
        root = scenario("join_nowrite", src=FIXTURES / "join")
        rc, out, err = run_cli(["join", "join/srcdir", "-o", "nodir/out.pdf"], cwd=root, expect_rc=1)
        self.assertIn("could not write", out + err, "write failure not reported")
        self.assertFalse((root / "out.pdf").exists(), "a partial out.pdf was left behind")
        leftovers = [str(p.name) for p in root.iterdir() if p.name.endswith(".tmp")]
        self.assertEqual(leftovers, [], "temporary staging files left behind: {0}".format(leftovers))

    def test_join_rejects_invalid_catalog_setting(self):
        root = scenario("join_badcatalog", src=FIXTURES / "join")
        (root / "badcatalog.yml").write_text("page_layout: Booklet\n")
        rc, out, err = run_cli(["join", "join/srcdir", "-c", "badcatalog.yml"], cwd=root, expect_rc=1)
        self.assertIn("invalid page_layout", out + err, "invalid config page_layout value not reported")
        rc, out, err = run_cli(["join", "join/srcdir", "-D", "TTB"], cwd=root, expect_rc=None)
        self.assertNotEqual(rc, 0, "invalid --direction value was accepted")
        self.assertIn("not one of", out + err, "invalid --direction value not rejected by the cli")


# ================================================================ sort tests
SORT_NESTED = "sort-nested-mtime-2003-03-03.jpg"


class SortTests(unittest.TestCase):
    def test_sort_copy_is_default_and_keeps_source(self):
        root = scenario("sort_copy", src=FIXTURES / "sort" / "src")
        src, tgt = root / "src", root / "tgt"
        rc, out, err = run_cli(["sort", str(src), str(tgt)], cwd=root)
        sort_check(tgt, SORT_TOPLEVEL, label="copy default")
        for name in SORT_TOPLEVEL:
            self.assertTrue((src / name).exists(), "copy mode removed {0} from SRCDIR".format(name))

    def test_sort_copy_does_not_recurse_by_default(self):
        root = scenario("sort_copy", src=FIXTURES / "sort" / "src")
        src, tgt = root / "src", root / "tgt"
        rc, out, err = run_cli(["sort", str(src), str(tgt)], cwd=root)
        self.assertEqual(locate_under(tgt, SORT_NESTED), [],
                         "non-recursive run recursed into SRCDIR subdirectories")

    def test_sort_move_removes_source_files(self):
        root = scenario("sort_move", src=FIXTURES / "sort" / "src")
        src, tgt = root / "src", root / "tgt"
        rc, out, err = run_cli(["sort", "--move", str(src), str(tgt)], cwd=root)
        sort_check(tgt, SORT_TOPLEVEL, label="move")
        for name in SORT_TOPLEVEL:
            self.assertFalse((src / name).exists(), "--move left {0} behind in SRCDIR".format(name))
        self.assertEqual(locate_under(tgt, SORT_NESTED), [], "--move without -r must not touch nested files")

    def test_sort_prefers_exif_date_over_file_date(self):
        root = scenario("sort_exif", src=FIXTURES / "sort" / "src")
        src, tgt = root / "src", root / "tgt"
        rc, out, err = run_cli(["sort", str(src), str(tgt)], cwd=root)
        checked = 0
        for name, exif_when, mt_when, *_ in SORT_FIXTURES:
            if exif_when is None or "/" in name:
                continue
            base = Path(name).name
            self.assertTrue((tgt / exif_when.strftime("%Y-%m-%d") / base).exists(),
                            "{0} not filed under its exif date {1}".format(base, exif_when))
            self.assertFalse((tgt / mt_when.strftime("%Y-%m-%d") / base).exists(),
                            "{0} filed under file date {1} instead of exif date".format(base, mt_when))
            checked += 1
        self.assertEqual(checked, 2, "fixture set should contain two exif-dated top level images")

    def test_sort_falls_back_to_file_date_without_exif(self):
        root = scenario("sort_filedate", src=FIXTURES / "sort" / "src")
        src, tgt = root / "src", root / "tgt"
        rc, out, err = run_cli(["sort", str(src), str(tgt)], cwd=root)
        plain = [n for n in SORT_TOPLEVEL if "exif" not in n]
        self.assertEqual(len(plain), 2, "need two exif-free fixtures")
        sort_check(tgt, plain, label="file-date fallback")
        for name in plain:
            base = Path(name).name
            self.assertEqual(locate_under(tgt, base),
                             [str(target_dir_for(base) / base)],
                             "{0} misplaced".format(base))

    def test_sort_fmt_option_names_folder(self):
        root = scenario("sort_fmt", src=FIXTURES / "sort" / "src")
        src, tgt = root / "src", root / "tgt"
        rc, out, err = run_cli(["sort", "--fmt", "%Y_%m", str(src), str(tgt)], cwd=root)
        sort_check(tgt, SORT_TOPLEVEL, fmt="%Y_%m", label="--fmt folder naming")
        want = sorted({target_dir_for(n, "%Y_%m").name for n in SORT_TOPLEVEL})
        got = sorted(d.name for d in tgt.iterdir() if d.is_dir())
        self.assertEqual(got, want, "--fmt %Y_%m produced folders {0}".format(got))

    def test_sort_hierarch_option(self):
        root = scenario("sort_hier", src=FIXTURES / "sort" / "src")
        src, tgt = root / "src", root / "tgt"
        rc, out, err = run_cli(["sort", "--hierarch", str(src), str(tgt)], cwd=root)
        sort_check(tgt, SORT_TOPLEVEL, hierarch=True, label="--hierarch nesting")
        placements = locate_under(tgt, Path(SORT_TOPLEVEL[0]).name)
        self.assertEqual(len(placements), 1, "{0} landed more than once: {1}".format(SORT_TOPLEVEL[0], placements))
        self.assertEqual(len(placements[0].split(os.sep)), 4,
                         "--hierarch should nest year/month/day plus the file: {0}".format(placements))

    def test_sort_recursive_option(self):
        root = scenario("sort_rec", src=FIXTURES / "sort" / "src")
        src, tgt = root / "src", root / "tgt"
        rc, out, err = run_cli(["sort", "-r", "--move", str(src), str(tgt)], cwd=root)
        sort_check(tgt, [n for n, *_ in SORT_FIXTURES], label="-r recursion")
        nested = src / "nested"
        self.assertTrue(nested.is_dir(), "-r --move removed the now-empty nested source dir")
        self.assertEqual([f.name for f in nested.iterdir()], [],
                         "-r --move left files behind in the nested source directory")

    def test_sort_overwrite_option(self):
        root = scenario("sort_over")
        src_a, src_b, tgt = root / "srcA", root / "srcB", root / "tgt"
        wipe(tgt)
        name = "sort-conflict-mtime-1999-12-31.jpg"
        for d, seed in ((src_a, 31), (src_b, 32)):
            d.mkdir(parents=True, exist_ok=True)
            make_image(d / name, 60, 80, seed, "content-{0}".format(d.name))
            stamp_mtime(d / name, date(1999, 12, 31))
        expected = tgt / "1999-12-31" / name

        rc, out, err = run_cli(["sort", "--copy", str(src_a), str(tgt)], cwd=root)
        self.assertTrue(expected.exists(), "first copy pass did not place the file")
        self.assertEqual(expected.read_bytes(), (src_a / name).read_bytes(), "first pass content mismatch")

        rc, out, err = run_cli(["sort", "--copy", "-v", str(src_b), str(tgt)], cwd=root)
        self.assertEqual(expected.read_bytes(), (src_a / name).read_bytes(),
                         "conflicting file overwritten without --overwrite")
        self.assertIn("already exists", out + err,
                      "conflict not reported by the tool")

        rc, out, err = run_cli(["sort", "--copy", "--overwrite", str(src_b), str(tgt)], cwd=root)
        self.assertEqual(expected.read_bytes(), (src_b / name).read_bytes(),
                         "--overwrite did not replace the target file")

    def test_sort_hierarch_ignores_fmt(self):
        root = scenario("sort_hierfmt", src=FIXTURES / "sort" / "src")
        src, tgt = root / "src", root / "tgt"
        run_cli(["sort", "--hierarch", "--fmt", "%Y_%m", str(src), str(tgt)], cwd=root)
        sort_check(tgt, SORT_TOPLEVEL, hierarch=True, label="--hierarch overrides --fmt")
        self.assertEqual(sorted(d.name for d in tgt.iterdir() if d.is_dir()),
                         sorted({target_dir_for(n, hierarch=True).parts[0] for n in SORT_TOPLEVEL}),
                         "--fmt %Y_%m leaked into the top level folder names while --hierarch was given")

    def test_sort_dry_run_changes_nothing(self):
        root = scenario("sort_dry", src=FIXTURES / "sort" / "src")
        src, tgt = root / "src", root / "tgt"
        rc, out, err = run_cli(["sort", "--dry-run", str(src), str(tgt)], cwd=root)
        for name in SORT_TOPLEVEL:
            self.assertTrue((src / name).exists(), "dry run moved {0}".format(name))
        self.assertEqual(locate_under(tgt, Path(SORT_TOPLEVEL[0]).name), [], "dry run wrote files into TGTDIR")
        self.assertIn("DRY RUN", out + err, "dry run produced no confirmation message")


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


# ================================================================ dedup tests
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


class DedupTests(unittest.TestCase):
    def test_dedup_fixture_hashes_are_distinct(self):
        paths = [(n, FIXTURES / "dedup" / "images" / n) for n in DEDUP_NAMES]
        hashes = {n: image_hash(p, imagehash.dhash) for n, p in paths}
        self.assertEqual(len(set(hashes.values())), 5,
                         "fixture set should yield 5 distinct dhashes (3 unique + 2 groups), got {0}: {1}".format(
                             len(set(hashes.values())), hashes))
        for uniq in DEDUP_UNIQUE:
            shared = [n for n in DEDUP_NAMES if n != uniq and hashes[n] == hashes[uniq]]
            self.assertEqual(shared, [], "unique fixture {0} collides with {1}".format(uniq, shared))

    def test_dedup_groups_identical_images_by_hash(self):
        root = scenario("dedup_dhash", src=FIXTURES / "dedup" / "images")
        work = root / "images"
        want = expected_groups([(n, work / n) for n in DEDUP_NAMES], imagehash.dhash)
        rc, out, err = run_cli(["dedup", str(work)], cwd=root)
        loose, groups = dedup_state(work)
        self.assertEqual(len(groups), len(want),
                         "expected {0} hash folders, got {1}: {2}".format(len(want), len(groups), sorted(groups)))
        for h, names in want.items():
            self.assertIn(h, groups, "hash folder {0} was not created".format(h))
            self.assertEqual(groups[h], names, "hash folder {0} contains {1} (expected {2})".format(h, groups[h], names))
            self.assertRegex(h, r"^[0-9a-f]+$", "hash folder {0} is not a hash name".format(h))
            for name in names:
                self.assertNotIn(name, loose, "{0} should have been moved into {1}".format(name, h))
        return groups

    def test_dedup_leaves_unique_images_alone(self):
        root = RUNS / "dedup_dhash"
        work = root / "images"
        loose, groups = dedup_state(work)
        for uniq in DEDUP_UNIQUE:
            self.assertIn(uniq, loose, "unique image {0} was moved".format(uniq))
        moved = [n for names in groups.values() for n in names]
        self.assertEqual([n for n in moved if n in DEDUP_UNIQUE], [], "unique images got grouped as duplicates")
        self.assertTrue(any(len(names) > 2 for names in groups.values()),
                        "the triple fixture should end up as a 3-image folder")

    def test_dedup_default_hash_func_matches_dhash(self):
        root_a = scenario("dedup_default", src=FIXTURES / "dedup" / "images")
        root_b = scenario("dedup_dhash2", src=FIXTURES / "dedup" / "images")
        run_cli(["dedup", str(root_a / "images")], cwd=root_a)
        run_cli(["dedup", "-f", "dhash", str(root_b / "images")], cwd=root_b)
        _la, ga = dedup_state(root_a / "images")
        _lb, gb = dedup_state(root_b / "images")
        self.assertEqual(sorted(ga), sorted(gb), "default hash func is not dhash")
        self.assertEqual(ga, gb, "default and -f dhash grouped different images")

    def test_dedup_alternate_hash_function(self):
        root = scenario("dedup_ahash", src=FIXTURES / "dedup" / "images")
        work = root / "images"
        want = expected_groups([(n, work / n) for n in DEDUP_NAMES], imagehash.average_hash)
        rc, out, err = run_cli(["dedup", "-f", "ahash", str(work)], cwd=root)
        loose, groups = dedup_state(work)
        self.assertEqual(set(groups), set(want),
                         "ahash produced folders {0} instead of {1}".format(sorted(groups), sorted(want)))
        for h in want:
            self.assertEqual(groups[h], want[h], "ahash folder {0} misplaced images".format(h))

    def test_dedup_accepts_every_documented_hash_function(self):
        empty = []
        for func in ("ahash", "phash", "dhash", "haar", "db4", "color", "crop"):
            root = scenario("dedup_{0}".format(func), src=FIXTURES / "dedup" / "images")
            work = root / "images"
            want = expected_groups([(n, work / n) for n in DEDUP_NAMES], HASH_FUNCS[func])
            rc, out, err = run_cli(["dedup", "-f", func, str(work)], cwd=root)
            loose, groups = dedup_state(work)
            self.assertEqual(set(groups), set(want),
                             "{0}: folders {1} vs expected {2}".format(func, sorted(groups), sorted(want)))
            if not groups:
                empty.append(func)
        if empty:
            finding("dedup -f {0} found no duplicates in the fixture set (fixture images too dissimilar for that hash)".format(
                ", ".join(empty)))

    def test_dedup_hash_size_option_effect(self):
        root8 = scenario("dedup_size8", src=FIXTURES / "dedup" / "images")
        root4 = scenario("dedup_size4", src=FIXTURES / "dedup" / "images")
        run_cli(["dedup", str(root8 / "images")], cwd=root8)
        run_cli(["dedup", "-s", "4", str(root4 / "images")], cwd=root4)
        _l8, g8 = dedup_state(root8 / "images")
        _l4, g4 = dedup_state(root4 / "images")
        self.assertEqual(set(g4), set(g8),
                         "README documents --hash-size as not implemented, but -s 4 changed grouping: "
                         "{0} vs {1}".format(sorted(g4), sorted(g8)))
        self.assertEqual(g4, g8, "--hash-size is documented as inert; grouping must be identical")

    def test_dedup_rejects_nonpositive_hash_size(self):
        root = scenario("dedup_sizebad", src=FIXTURES / "dedup" / "images")
        rc, out, err = run_cli(["dedup", "-s", "0", str(root / "images")], cwd=root, expect_rc=1)
        self.assertIn("Hash size must be a positive integer", out + err,
                      "range check message missing")
        loose, groups = dedup_state(root / "images")
        self.assertEqual(groups, {}, "-s 0 should bail out before moving anything")

    def test_dedup_reports_when_no_duplicates(self):
        root = scenario("dedup_nodups")
        work = root / "images"
        work.mkdir(parents=True, exist_ok=True)
        for name, seed, w, h, label in DEDUP_FIXTURES[:3]:
            make_image(work / name, w, h, seed, label)
        rc, out, err = run_cli(["dedup", str(work)], cwd=root)
        loose, groups = dedup_state(work)
        self.assertEqual(groups, {}, "a directory of distinct images produced hash directories {0}".format(sorted(groups)))
        self.assertEqual(rc, 0, "the no-duplicate case should exit successfully")

    def test_dedup_ignores_non_image_entries(self):
        root = scenario("dedup_nonimg", src=FIXTURES / "dedup" / "images")
        work = root / "images"
        (work / "notes.txt").write_text("ignore me\n")
        (work / "clip.mov").write_bytes(b"not a jpg")
        rc, out, err = run_cli(["dedup", str(work)], cwd=root)
        loose, groups = dedup_state(work)
        self.assertNotIn("notes.txt", [n for names in groups.values() for n in names],
                         "dedup hashed a text file")
        self.assertNotIn("clip.mov", [n for names in groups.values() for n in names],
                         "dedup hashed a video file")
        self.assertEqual(rc, 0, "dedup failed on a directory containing non-image entries")


# ==================================================================== cli opts
OPTION_CLAIMS = {
    "join": {
        "usage": "imgtk join [OPTIONS] [IMG]...",
        "options": ["-c, --config <cfg>", "-o, --out <out>", "-t, --toc <toc>",
                    "-e, --ext <ext>", "-d, --dpi <dpi>",
                    "-P, --page-layout <layout>", "-D, --direction <dir>",
                    "-v, --verbose", "-h, --help"],
    },
    "sort": {
        "usage": "imgtk sort [OPTIONS] SRCDIR TGTDIR",
        "options": ["--copy", "--move", "-r, --recurse", "-o, --overwrite",
                    "-H, --hierarch", "-d, --dry-run", "-f, --fmt <fmt>",
                    "-v, --verbose", "-h, --help"],
    },
    "dedup": {
        "usage": "imgtk dedup [OPTIONS] PATH",
        "options": ["-s, --hash-size <size>", "-f, --hash-func <hashfunc>",
                    "-v, --verbose", "-h, --help"],
    },
}


class OptionTests(unittest.TestCase):
    def test_cli_options_match_readme_usage(self):
        for sub, claim in OPTION_CLAIMS.items():
            rc, out, err = run_cli([sub, "--help"], cwd=TESTDIR)
            help_text = out
            self.assertIn(claim["usage"].split("[OPTIONS]")[1].strip().split()[0], help_text,
                          "{0} is missing its positional arguments".format(sub))
            for opt in claim["options"]:
                self.assertIn(opt, help_text, "{0} usage is missing {1}".format(sub, opt))

    def test_cli_help_and_group_listing(self):
        rc, out, err = run_cli(["--help"], cwd=TESTDIR)
        for sub in ("join", "sort", "dedup"):
            self.assertIn(sub, out, "top level help does not list {0}".format(sub))
        rc, out, err = run_cli(["--version"], cwd=TESTDIR)
        self.assertRegex((out + err).strip(), r"[0-9]+\.[0-9]+\.[0-9]+")

    def test_documented_option_defaults(self):
        rc, out, err = run_cli(["join", "--help"], cwd=TESTDIR)
        self.assertIn("Configuration File (default: imgtk-join.yml)", out,
                      "join --config help does not state the README default")

        rc, out, err = run_cli(["sort", "--help"], cwd=TESTDIR)
        flat = " ".join(out.split())
        self.assertIn("%Y-%m-%d", flat, "sort --fmt default not documented in --help")
        self.assertIn("Ignored when --hierarch is specified", flat,
                      "sort --fmt help does not state that --hierarch overrides it")

        rc, out, err = run_cli(["dedup", "--help"], cwd=TESTDIR)
        flat = " ".join(out.split())
        self.assertIn("hash size to use for image hashing", flat, "dedup --hash-size help missing")
        self.assertIn("accepted but not implemented", flat,
                      "dedup --hash-size help does not admit the option is inert")

    def test_readme_documents_config_name_consistently(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        for stale in ("i2p.yml", "imgtk-join.yaml", "imgtk.yaml"):
            self.assertNotIn(stale, text,
                             "README still names the join config file as {0}".format(stale))
        self.assertIn("imgtk-join.yml", text, "README never names the config file the tool reads")

    def test_readme_usage_blocks_match_cli_help(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        blocks = {}
        for m in re.finditer(r"~~~console\n(.*?)\n~~~", text, re.S):
            body = m.group(1)
            first = body.strip().splitlines()[0]
            if first.startswith("Usage: imgtk "):
                blocks[first.split()[2]] = body
        self.assertEqual(sorted(blocks), ["dedup", "join", "sort"],
                         "README documents usage blocks for {0}".format(sorted(blocks)))
        for sub, claimed in blocks.items():
            rc, out, err = run_cli([sub, "--help"], cwd=TESTDIR)
            actual = "Usage: imgtk " + out[out.index(sub):]
            claimed = "Usage: imgtk " + claimed[claimed.index(sub):]
            squeeze = lambda s: re.sub(r"\s+", " ", s).strip()
            self.assertEqual(squeeze(actual), squeeze(claimed),
                             "{0}: README usage block differs from --help".format(sub))

# ====================================================================== main
TEST_GROUPS = {
    "join": [JoinTests],
    "opts": [OptionTests],
    "sort": [SortTests],
    "dedup": [DedupTests],
}


def report():
    lines = ["fixtures: {0}".format(FIXTURES), "scenario outputs: {0}".format(RUNS)]
    lines.append("join: {0} (page order: {1})".format(
        RUNS / "join_toc" / "withtoc.pdf", ", ".join(JOIN_ORDER_DEFAULT)))
    for i, name in enumerate(JOIN_ORDER_DEFAULT, 1):
        lines.append("  page {0}: {1} {2}px".format(i, name, JOIN_SIZES[name]))
    lines.append("  pdf outline: {0}".format([t for _p, _l, t in TOC_FIXTURE]))
    lines.append("sort: {0} (each folder name equals the date claimed in the file name)".format(RUNS / "sort_copy" / "tgt"))
    for name in SORT_TOPLEVEL:
        lines.append("  {0} -> {1}".format(name, target_dir_for(name)))
    lines.append("dedup: {0} (hash-named folders hold the duplicate sets)".format(RUNS / "dedup_dhash" / "images"))
    return lines


def main():
    ap = argparse.ArgumentParser(description="imgtk CLI test harness")
    ap.add_argument("--only", action="append", choices=sorted(TEST_GROUPS),
                    help="run only the named test group (repeatable)")
    ap.add_argument("--keep", action="store_true", help="keep existing fixtures instead of regenerating them")
    ap.add_argument("--verbose", action="store_true", help="per-test unittest output")
    args = ap.parse_args()

    if TESTDIR.exists() and not args.keep:
        shutil.rmtree(str(TESTDIR))
    TESTDIR.mkdir(parents=True, exist_ok=True)
    build_fixtures()

    chosen = args.only or sorted(TEST_GROUPS)
    loader = unittest.TestLoader()
    suites = []
    for group in chosen:
        for cls in TEST_GROUPS[group]:
            suites.append(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2 if args.verbose else 1)
    result = runner.run(unittest.TestSuite(suites))

    for line in report():
        print(line)
    if FINDINGS:
        print("\nREADME/spec discrepancies worth a docs or code fix:")
        for msg in FINDINGS:
            print("  - " + msg)
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
