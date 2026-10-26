"""Options/README consistency: per-subcommand --help usage text, version banner,
documented defaults, and cross-references between README.md and the CLI.
"""
from __future__ import annotations

import re
import unittest

from .infra import run_cli, TESTDIR, ROOT

OPTION_CLAIMS = {
    "join": {
        "usage": "imgtk join [OPTIONS] [IMG]...",
        "options": ["-c, --config <cfg>", "-o, --out <out>", "-t, --toc <toc>",
                    "-e, --ext <ext>", "-d, --dpi <dpi>",
                    "-P, --page-layout <layout>", "-D, --direction <dir>",
                    "-m, --page-mode <mode>", "-z, --zoom <zoom>",
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
