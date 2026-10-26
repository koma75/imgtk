"""sort subcommand: date-based file placement (exif vs file date), copy/move,
recursion, --fmt/--hierarch naming, overwrite, and dry-run.
"""
from __future__ import annotations

import unittest
import os
from datetime import date
from pathlib import Path

from .infra import run_cli, scenario, wipe, FIXTURES
from .fixtures import make_image, stamp_mtime, SORT_FIXTURES, SORT_TOPLEVEL
from .dates import target_dir_for
from .sortutil import locate_under, sort_check

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
