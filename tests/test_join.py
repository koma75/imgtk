"""join subcommand: PDF assembly from a directory/explicit files, config, ext filter,
ordering, dpi scaling, catalog viewer keys, /PageMode, and /OpenAction zoom.
"""
from __future__ import annotations

import unittest

from .infra import run_cli, scenario, FIXTURES
from .fixtures import JOIN_SIZES, TOC_FIXTURE
from .pdfinspect import (
    expect_pdf,
    expect_pdf_toc,
    pdf_pages,
    pdf_page_layout,
    pdf_direction,
    pdf_page_mode,
    pdf_open_action,
)

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
            "page_layout: TwoPageRight\ndirection: R2L\n",
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
        self.assertEqual(pdf_page_layout(data), "TwoPageRight",
                         "default /PageLayout is {0}, README documents TwoPageRight".format(pdf_page_layout(data)))
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
        rc, out, err = run_cli(["join", "join/srcdir", "-z", "banana"], cwd=root, expect_rc=1)
        self.assertIn("invalid zoom", out + err, "invalid --zoom value not reported by the resolver")

    # ---------------- /PageMode and /OpenAction ----------------
    def test_join_page_mode_option(self):
        root = scenario("join_page_mode", src=FIXTURES / "join")
        rc, out, err = run_cli(["join", "join/srcdir", "-o", "pm_out.pdf", "-m", "UseOutlines"], cwd=root)
        data = expect_pdf(root, "pm_out.pdf", JOIN_ORDER_DEFAULT, 96, "-m UseOutlines")
        self.assertEqual(pdf_page_mode(data), "UseOutlines",
                         "-m UseOutlines produced /PageMode {0}".format(pdf_page_mode(data)))
        run_cli(["join", "join/srcdir", "-o", "pm_none.pdf", "-m", "none"], cwd=root)
        data = expect_pdf(root, "pm_none.pdf", JOIN_ORDER_DEFAULT, 96, "-m none")
        self.assertIsNone(pdf_page_mode(data),
                          "-m none must remove /PageMode, found {0}".format(pdf_page_mode(data)))

    def test_join_page_mode_auto_default_from_toc(self):
        # an outline written from toc.yml selects /PageMode UseOutlines when
        # the option is omitted; with no outline the entry is omitted too
        root = scenario("join_pmauto", src=FIXTURES / "join")
        rc, out, err = run_cli(["join", "join/srcdir", "-o", "tocauto.pdf",
                                "-t", "join/toc.yml"], cwd=root)
        data = expect_pdf(root, "tocauto.pdf", JOIN_ORDER_DEFAULT, 96, "outline auto default")
        outlines = expect_pdf_toc(data, TOC_FIXTURE, "outline auto default")
        self.assertEqual(pdf_page_mode(data), "UseOutlines",
                         "when the run wrote an outline, page_mode auto default must produce /PageMode UseOutlines, found {0}".format(pdf_page_mode(data)))
        run_cli(["join", "join/srcdir", "-o", "noauto.pdf"], cwd=root)
        data = expect_pdf(root, "noauto.pdf", JOIN_ORDER_DEFAULT, 96, "no outline")
        self.assertIsNone(pdf_page_mode(data),
                          "no outline written must leave /PageMode absent, found {0}".format(pdf_page_mode(data)))

    def test_join_zoom_option(self):
        root = scenario("join_zoom", src=FIXTURES / "join")
        run_cli(["join", "join/srcdir", "-o", "z150.pdf", "-z", "150%"], cwd=root)
        data = expect_pdf(root, "z150.pdf", JOIN_ORDER_DEFAULT, 96, "-z 150%")
        self.assertEqual(pdf_open_action(data), "page=1,xyz,zoom=1.5",
                         "-z 150% wrote an /OpenAction {0}".format(pdf_open_action(data)))
        run_cli(["join", "join/srcdir", "-o", "zfit.pdf", "-z", "fit_page"], cwd=root)
        data = expect_pdf(root, "zfit.pdf", JOIN_ORDER_DEFAULT, 96, "-z fit_page")
        self.assertEqual(pdf_open_action(data), "page=1,fit=Fit",
                         "-z fit_page wrote /OpenAction {0}".format(pdf_open_action(data)))
        run_cli(["join", "join/srcdir", "-o", "zact.pdf", "-z", "actual"], cwd=root)
        data = expect_pdf(root, "zact.pdf", JOIN_ORDER_DEFAULT, 96, "-z actual")
        self.assertEqual(pdf_open_action(data), "page=1,xyz,zoom=1",
                         "-z actual wrote /OpenAction {0}".format(pdf_open_action(data)))

    def test_join_default_omits_open_action(self):
        # fpdf writes a /FitH /OpenAction by default; the tool's default must
        # remove that entry so the viewer's own preference wins.
        root = scenario("join_noaction", src=FIXTURES / "join")
        run_cli(["join", "join/srcdir", "-o", "noaction.pdf"], cwd=root)
        data = expect_pdf(root, "noaction.pdf", JOIN_ORDER_DEFAULT, 96, "no /OpenAction")
        self.assertEqual(pdf_open_action(data), "none",
                         "default must not keep the generator's /OpenAction, found {0}".format(pdf_open_action(data)))
        run_cli(["join", "join/srcdir", "-o", "znone.pdf", "-z", "none"], cwd=root)
        data = expect_pdf(root, "znone.pdf", JOIN_ORDER_DEFAULT, 96, "-z none")
        self.assertEqual(pdf_open_action(data), "none",
                         "-z none must remove /OpenAction, found {0}".format(pdf_open_action(data)))

    def test_join_zoom_and_page_mode_from_config(self):
        root = scenario("join_zoomcfg", src=FIXTURES / "join")
        (root / "zm.yml").write_text(
            "out: zmcfg.pdf\npage_mode: fullscreen\nzoom: fit_width\n"
            "ext:\n  - jpg\n  - png\n"
        )
        rc, out, err = run_cli(["join", "join/srcdir", "-c", "zm.yml"], cwd=root)
        data = expect_pdf(root, "zmcfg.pdf", JOIN_ORDER_DEFAULT, 96, "config page_mode/zoom")
        self.assertEqual(pdf_page_mode(data), "FullScreen",
                         "config 'page_mode: fullscreen' produced /PageMode {0}".format(pdf_page_mode(data)))
        self.assertEqual(pdf_open_action(data), "page=1,fit=FitH",
                         "config 'zoom: fit_width' produced /OpenAction {0}".format(pdf_open_action(data)))
        # command line takes precedence over the configuration file
        rc, out, err = run_cli(["join", "join/srcdir", "-c", "zm.yml",
                                "-m", "UseNone", "-z", "fit_height", "-o", "zmcli.pdf"], cwd=root)
        data = expect_pdf(root, "zmcli.pdf", JOIN_ORDER_DEFAULT, 96, "cli overrides config zoom/page_mode")
        self.assertEqual(pdf_page_mode(data), "UseNone",
                         "cli --page-mode did not override the config value: {0}".format(pdf_page_mode(data)))
        self.assertEqual(pdf_open_action(data), "page=1,fit=FitV",
                         "cli --zoom did not override the config value: {0}".format(pdf_open_action(data)))
