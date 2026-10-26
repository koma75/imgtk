#!/usr/bin/env python3
"""Test harness entry point for the imgtk command line tool.

Exercises every subcommand advertised in README.md (join, sort, dedup) against
generated fixture images, then asserts on observable results (PDF structure/outline,
directory placement, duplicate grouping).

Layout:
    tests/            per-subcommand test modules + shared support scaffolding
    harness/          multi-version driver (runs the suite per pyproject version)
    testharness/fixtures/   generated input images (join/, sort/, dedup/)
    testharness/runs/       per-scenario working dirs and tool outputs

Run:
    uv run runtests.py [--only join|sort|dedup|opts] [--keep] [--verbose]

The harness reads every 'Programming Language :: Python :: 3.NN' classifier from
pyproject.toml and re-runs the full suite under each of those Python versions
through a dedicated uv venv (.venv-3NN), reporting pass/fail per version. The
--self flag runs a single version in-process and is used internally by the
multi-version driver; it is not meant to be typed by hand.
"""
from harness.driver import main

if __name__ == "__main__":
    main()
