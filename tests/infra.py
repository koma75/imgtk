"""Shared test-harness scaffolding: paths, dependency guard, CLI runner, scenarios.

This is harness plumbing only -- no assertions about the tool's behaviour.
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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
            "run the harness through uv so the dev env is provisioned:\n"
            "    uv run runtests.py\n".format(", ".join(missing))
        )
        sys.exit(2)


require_deps()


def cli_prefix():
    # Always run through the interpreter that launched this harness. uv pins a
    # per-version interpreter when it invokes the child, so the tool under test
    # uses exactly the Python version being exercised (never a stale console
    # script that some other venv may have left on PATH).
    return [sys.executable, "-m", "imgtk.cli"]


def run_cli(args, cwd, expect_rc: int | None = 0):
    env = os.environ.copy()
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


def _clip(text, limit=320):
    text = (text or "").strip()
    if not text:
        return ""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    tail = lines[-1] if lines else text
    return tail if len(tail) <= limit else tail[:limit] + "..."


def _test_label(case):
    cls = type(case).__name__
    meth = getattr(case, "__testMethodName__", "")
    return (cls + "." + meth) if meth else cls
