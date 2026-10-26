# Changelog

Change-point identifiers: **[Added]** new feature/option · **[Changed]** behavior
changed · **[Breaking]** incompatible change · **[Minor]** cosmetic/clarification
· **[Performance]** performance improvement · **[Fixed]** bug fix.

## 1.3.0 (2026.10.20)

**Summary:** PDF document-catalog/viewer options for `join` (page layout, reading
direction, view mode, zoom); shared logging and unified exit codes across subcommands;
CLI test harness added.

**User-facing specification changes**

*join — new document-catalog options*

- **[Added]** **[Changed]** `-P, --page-layout <layout>` writes `/PageLayout` into the PDF catalog:
  `SinglePage`, `OneColumn`, `TwoColumnLeft`, `TwoColumnRight`, `TwoPageLeft`,
  `TwoPageRight`, `none`; default `TwoPageRight`. The `TwoPage*` values raise the
  generated file to PDF 1.5 as the PDF spec requires.
- **[Added]** **[Changed]** `-D, --direction <dir>` writes `/Direction` into `ViewerPreferences`:
  `L2R`, `R2L`, `none`; default `R2L` (right-to-left book).
- **[Added]** `-m, --page-mode <mode>` writes `/PageMode`: `UseOutlines`, `UseNone`,
  `UseOC`, `UseAttachments`, `FullScreen`, `none`; default `UseOutlines` when the run
  wrote a PDF outline, otherwise the entry is omitted.
- **[Added]** `-z, --zoom <zoom>` writes an `/OpenAction` Go To on the first page:
  `default`, `none`, `actual`, `NN%` (e.g. `150%`, `75%`), `fit_page` (`/Fit`),
  `fit_width` (`/FitH`), `fit_height` (`/FitV`), `fit_visible` (`/FitB`),
  `fit_visible_width` (`/FitBH`), `fit_visible_height` (`/FitBV`); default `default`
  (no `/OpenAction`).
- **[Added]** New configuration keys (`page_layout`, `direction`, `page_mode`, `zoom`)
  can be set in the `imgtk-join.yml` config file; command-line values win.
- **[Changed]** Each catalog key has three states: omitted → tool default written;
  set to a value → that value written; `none` → entry removed from the PDF (not the
  same as leaving it out).
- **[Added]** `join` now requires a new runtime dependency, `pikepdf`, to apply the
  catalog entries. The PDF is staged in a temp file next to the target and renamed
  into place, so a failed run leaves no partial PDF; the output is re-serialized by
  qpdf and is not byte-identical to the generator alone.
- **[Minor]** A bad configuration value is reported and makes `join` exit
  unsuccessfully; invalid command-line values are rejected by the parser first.

*exit codes (all subcommands)*

- **[Changed]** `join`, `sort` and `dedup` now return process exit codes; `imgtk`
  exits non-zero on failure.
- **[Minor]** `dedup --hash-size/-s` help corrected to "default: 8; accepted but
  not implemented"; the value is still only range-checked and is not forwarded to the
  hash functions.
- **[Minor]** `sort --fmt/-f` help notes it is ignored when `--hierarch` is given;
  `--hierarch` always nests the target as `%Y/%m/%d`.

**Bug fixes**

- **[Fixed]** `join` no longer writes the invalid `/Direction RTL` name that fpdf
  produced; catalog name values are emitted per the PDF spec via pikepdf.

**Other changes**

- Internal refactor: shared console-logging module (`imgtk/_logging.py`); command
  APIs converted from `**kwargs` dicts to typed keyword arguments.
- `imgtk/__init__.py` falls back to a dev version when the setuptools-scm generated
  `_version.py` is absent in a bare checkout.
- Runtime/dependency updates: `pikepdf` added; `pillow` 11.3 → 12.2; `PyYaml`
  renamed `PyYAML`; `requires-python` 3.9 → 3.11 (and classifier Python 3.9 → 3.11).
- Dependency bumps for security updates.
- Docs: README `--help`/usage text aligned with the implementation (config default
  `i2p.yml` → `imgtk-join.yml`, sort args `SOURCEDIR`/`TARGETDIR` →
  `SRCDIR`/`TGTDIR`, `--recursive` → `--recurse`, hash-size/hash-func help); a
  "Known Issues" section added.
- Tooling: `test_harness.py` added with a `test` Makefile target; `testharness/`
  scratch outputs git-ignored; `tasks.py` modernized to `python -m build`/`twine`
  and its task ordering/dependency references fixed.

## 1.2.1 (2026.01.13)

**Summary:** Quick-fix release: join no longer fails at PDF write-out.

**User-facing specification changes**

- (No specification changes.)

**Bug fixes**

- **[Fixed]** `join` no longer fails when writing the PDF: the fpdf2 output call
  `pdf.output(out, 'F')` was corrected to `pdf.output(out)`.
- **[Fixed]** Error reporting now includes the underlying exception text (e.g.
  config-create and image-read failures) instead of silently swallowing it.

**Other changes**

- Type-annotation/pyright issues cleaned up across `i2p`, `exifsort`, `deduplicate`.
- Tooling: `from distutils import cmd` removed from `tasks.py`; a VS Code
  `launch.json` (debug-python) added.

## 1.2.0 (2025.09.12)

**Summary:** `dedup` image hashing parallelized (multi-core), roughly 6× faster on
8 cores (~12 min → 2 min on 6,580 4K images).

**User-facing specification changes**

*dedup*

- **[Performance]** Image hashing now runs across multiple processes
  (`ProcessPoolExecutor`); duplicate grouping is unchanged.
- **[Changed]** The progress indicator switched to a labeled "Processing images"
  bar.

**Bug fixes**

- (No bug fixes.)

**Other changes**

- Runtime dependency `tqdm` added; `concurrent.futures` used for hashing.

## 1.1.1 (2025.07.10)

**Summary:** Documentation fix to the version-history table.

**User-facing specification changes**

- (No specification changes.)

**Bug fixes**

- (No bug fixes.)

**Other changes**

- Docs: the README version-history table was corrected (a mislabeled `1.0.2` entry
  fixed to `1.1.0`/`1.1.1`).

## 1.1.0 (2025.07.10)

**Summary:** Proper EXIF IFD tag support for date extraction in `sort`; Pillow
bumped to 11.x.

**User-facing specification changes**

*sort*

- **[Changed]** Date extraction now uses `getexif()` and the IFD (Exif) sub-IFD, with
  precedence `DateTimeOriginal` → `DateTimeDigitized` → `DateTime` (IFD) → `DateTime`
  (top-level), falling back to the file creation date. This changes which date is used
  to sort images that carry IFD timestamps.

**Bug fixes**

- **[Fixed]** The deprecated `_getexif()` call was replaced with `getexif()` (with IFD
  traversal); bare `except` clauses and `rt == None` comparisons replaced.

**Other changes**

- Runtime dependency `pillow` 10.1 → 11.3 (enables the IFD API).
- Packaging metadata: Development Status `Alpha` → `Production/Stable`.
- Docs: README "next changelog" formatting fixed.

## 1.0.0 (2023.11.12)

**Summary:** First stable (1.0.0) release.

**User-facing specification changes**

- (No specification changes; subcommand/option set unchanged from 0.1.0.)

**Bug fixes**

- (No bug fixes.)

**Other changes**

- Runtime dependency `pillow` 9.4 → 10.1.
- Added `[project.urls]` (homepage/documentation/repository).

## 0.1.0 (2023.02.08)

**Summary:** First release.

**User-facing specification changes**

- **[Added]** `join` — merge images/directories into one PDF: `-c/--config`
  (default `imgtk-join.yml`, auto-created when missing), `-o/--out`, `-t/--toc`,
  `-e/--ext`, `-d/--dpi`.
- **[Added]** `sort` — move/copy images into date-named folders: `--copy`/`--move`
  (default copy), `-r/--recurse`, `-o/--overwrite`, `-H/--hierarch`,
  `-d/--dry-run`, `-f/--fmt` (default `%Y-%m-%d`).
- **[Added]** `dedup` — group duplicate images by perceptual hash: `-s/--hash-size`
  (default 8), `-f/--hash-func` (default `dhash`): `ahash`, `phash`, `dhash`, `haar`,
  `db4`, `color`, `crop`.

**Bug fixes**

- (No bug fixes — initial implementation.)

**Other changes**

- Package skeleton, dependencies (`click`, `PyYAML`, `pillow`, `imagehash`,
  `fpdf2`); setuptools-scm versioning; BSD-2-Clause license added to `__init__.py`.
