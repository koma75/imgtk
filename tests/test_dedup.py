"""dedup subcommand: perceptual-hash duplicate grouping, hash-function selection,
hash-size inertness, non-image skipping, and the no-duplicate case.
"""
from __future__ import annotations

import unittest

import imagehash

from .infra import run_cli, scenario, finding, FIXTURES
from .fixtures import make_image, DEDUP_FIXTURES
from .deduputil import (
    DEDUP_NAMES,
    DEDUP_UNIQUE,
    HASH_FUNCS,
    image_hash,
    expected_groups,
    dedup_state,
)


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

    def test_dedup_leaves_unique_images_alone(self):
        root = scenario("dedup_uniquecheck", src=FIXTURES / "dedup" / "images")
        work = root / "images"
        run_cli(["dedup", str(work)], cwd=root)
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
