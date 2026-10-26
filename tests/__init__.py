"""imgtk CLI test suite.

Each subcommand has its own ``test_<sub>.py`` module; shared scaffolding lives
in the sibling support modules (infra, fixtures, dates, pdfinspect, sortutil,
deduputil).  The multi-version driver that runs this suite lives in
``harness.driver``.
"""
