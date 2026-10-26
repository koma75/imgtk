"""Session-scoped fixture build shared by every test module.

The generated images/EXIF/side-files are rebuilt once per pytest session into
``testharness/fixtures`` (kept in place with ``--keep``); each test then derives
its own scenario working dir under ``testharness/runs``.
"""
from __future__ import annotations

import shutil

import pytest

from .infra import TESTDIR
from .fixtures import build_fixtures


def pytest_addoption(parser):
    parser.addoption("--keep", action="store_true",
                     help="keep existing fixtures instead of regenerating them")


@pytest.fixture(scope="session", autouse=True)
def _session_fixtures(request):
    keep = request.config.getoption("--keep")
    if TESTDIR.exists() and not keep:
        shutil.rmtree(str(TESTDIR))
    TESTDIR.mkdir(parents=True, exist_ok=True)
    build_fixtures()
