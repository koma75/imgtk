"""Multi-version test driver: provisions a uv venv per ``pyproject`` Python
classifier, runs the suite in a child interpreter, and reports per-version verdicts.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

from tests.infra import ROOT, TESTDIR, FIXTURES, RUNS, FINDINGS, _clip, _test_label
from tests.fixtures import build_fixtures, JOIN_SIZES, TOC_FIXTURE, SORT_TOPLEVEL
from tests.dates import target_dir_for
from tests.test_join import JoinTests, JOIN_ORDER_DEFAULT
from tests.test_sort import SortTests
from tests.test_dedup import DedupTests
from tests.test_opts import OptionTests


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


def _fixture_setup(keep):
    if TESTDIR.exists() and not keep:
        shutil.rmtree(str(TESTDIR))
    TESTDIR.mkdir(parents=True, exist_ok=True)
    build_fixtures()


def _build_suites(only):
    loader = unittest.TestLoader()
    suites = []
    for group in (only or sorted(TEST_GROUPS)):
        for cls in TEST_GROUPS[group]:
            suites.append(loader.loadTestsFromTestCase(cls))
    return suites


def run_suite_local(args):
    """Single-version in-process run. The interpreter uv selected for this
    child IS the Python under test, so the CLI subprocesses (sys.executable)
    and the assertions all execute against that minor version. Emits one
    RESULT_JSON line so the multi-version driver can reason about the outcome."""
    _fixture_setup(args.keep)
    quiet = io.StringIO()
    result = unittest.TextTestRunner(stream=quiet, verbosity=0).run(
        unittest.TestSuite(_build_suites(args.only))
    )
    bad = []
    for case, tb in result.failures + result.errors:
        bad.append({"test": _test_label(case), "reason": _clip(tb, 320)})

    payload = {
        "python": "{0}.{1}".format(*sys.version_info[:2]),
        "requested": args.self,
        "ran": result.testsRun,
        "ok": result.wasSuccessful(),
        "problems": bad,
        "findings": FINDINGS,
    }
    if args.verbose:
        sys.stderr.write(quiet.getvalue() + "\n")
    for line in report():
        print(line)
    if FINDINGS:
        print("\nREADME/spec discrepancies worth a docs or code fix:")
        for msg in FINDINGS:
            print("  - " + msg)
    print("RESULT_JSON " + json.dumps(payload, sort_keys=True))
    return 0 if result.wasSuccessful() else 1


TEST_GROUPS = {
    "join": [JoinTests],
    "opts": [OptionTests],
    "sort": [SortTests],
    "dedup": [DedupTests],
}


# --------------------------------------------------------------------- child mode
def discover_versions():
    """Python minor versions from pyproject classifiers of the form 3.NN."""
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    found = re.findall(r"Programming Language :: Python :: (3\.\d+)", text)
    seen = []
    for v in found:
        if v not in seen:
            seen.append(v)
    return seen


def uv(cmd, virtual_env=None):
    env = os.environ.copy()
    if virtual_env:
        env["VIRTUAL_ENV"] = str(virtual_env)
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, env=env)
    return proc.returncode, proc.stdout, proc.stderr


def parse_result_json(out):
    for line in reversed((out or "").splitlines()):
        if line.startswith("RESULT_JSON "):
            try:
                return json.loads(line[len("RESULT_JSON "):])
            except ValueError:
                return None
    return None


def drive_versions(args):
    """Parent mode: provision a dedicated uv venv (.venv-3NN) per classifier
    version, run the suite in a uv-spawned child, and print one verdict per
    version. A version's failure is reported with its reason and never stops
    the remaining versions from being tested."""
    versions = discover_versions()
    if not versions:
        sys.stderr.write("no 'Programming Language :: Python :: 3.NN' classifiers in pyproject.toml\n")
        return 2

    child_extra = []
    if args.only:
        for g in args.only:
            child_extra += ["--only", g]

    rows = []
    for ver in versions:
        venv = ROOT / (".venv-" + ver.replace(".", ""))
        rc, out, err = uv(["uv", "venv", str(venv), "--python", ver, "--clear", "--force"])
        if rc != 0:
            rows.append((ver, "SETUP-FAIL", "interpreter unavailable: " + _clip(err)))
            continue
        rc, out, err = uv(
            ["uv", "run", "--active", "--python", ver, "runtests.py",
             "--self", ver] + child_extra,
            virtual_env=venv,
        )
        payload = parse_result_json(out)
        if payload is None:
            rows.append((ver, "SETUP-FAIL",
                         _clip(err) or "env could not be provisioned for " + ver))
            continue
        if payload["ok"]:
            rows.append((ver, "PASS", "{0} tests".format(payload["ran"])))
        else:
            detail = "; ".join(
                "{0} -> {1}".format(p["test"], p["reason"]) for p in payload["problems"]
            )
            rows.append((ver, "TEST-FAIL", detail or _clip(err)))

    print("\nper-version results (pyproject Python classifiers: {0})".format(", ".join(versions)))
    fails = 0
    for ver, verdict, detail in rows:
        if verdict != "PASS":
            fails += 1
        print("  {0}  {1:11s}  {2}".format(ver, verdict, detail))
    print("\n{0} of {1} Python versions failed".format(fails, len(rows)))
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description="imgtk CLI test harness")
    ap.add_argument("--only", action="append", choices=sorted(TEST_GROUPS),
                    help="run only the named test group (repeatable)")
    ap.add_argument("--keep", action="store_true", help="keep existing fixtures instead of regenerating them")
    ap.add_argument("--verbose", action="store_true", help="per-test unittest output (child mode)")
    ap.add_argument("--self", metavar="PYVER",
                    help="internal: run one version in-process and emit RESULT_JSON")
    args = ap.parse_args()

    if args.self:
        sys.exit(run_suite_local(args))
    sys.exit(drive_versions(args))
