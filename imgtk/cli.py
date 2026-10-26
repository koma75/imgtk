#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 koma <okunoya@path-works.net>
# SPDX-License-Identifier: BSD-2-Clause

"""Main CLI Setup and Entrypoint."""

import sys

# Import the main click library
import click
# Import the sub-command implementations
from imgtk.exifsort import cp as exifsort_cp, mv as exifsort_mv, defaultFmt
from imgtk.i2p import join as i2p_join
from imgtk.deduplicate import find_dup, HASH_FUNCS
# Import the version information
from imgtk import __version__

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(version=__version__)
def cli():
    """Image File Manipulation Toolkit"""
    pass

@cli.command()
@click.argument('img', nargs=-1, type=click.Path(exists=True))
@click.option(
    '--config', '-c', default="./imgtk-join.yml",
    type=click.Path(exists=False, dir_okay=False, writable=True, resolve_path=True),
    metavar='<cfg>',
    help='Configuration File (default: imgtk-join.yml)'
    )
@click.option(
    '--out', '-o', type=str,
    metavar='<out>',
    help='output filename for the generated PDF'
    )
@click.option(
    '--toc', '-t', type=str,
    metavar='<toc>',
    help='toc file to populate PDF outline'
    )
@click.option(
    '--ext', '-e', type=str,
    multiple=True,
    metavar='<ext>',
    help='file extensions to pick up when parsing directories'
    )
@click.option(
    '--dpi', '-d', type=int,
    metavar='<dpi>',
    help='pixel density of input image in dpi'
    )
@click.option(
    '--page-layout', '-P', default=None,
    metavar='<layout>',
    type=click.Choice(['SinglePage', 'OneColumn', 'TwoColumnLeft',
                       'TwoColumnRight', 'TwoPageLeft', 'TwoPageRight', 'none'],
                      case_sensitive=False),
    help='page layout (/PageLayout) in the PDF document catalog: SinglePage, OneColumn, TwoColumnLeft, TwoColumnRight, TwoPageLeft, TwoPageRight, none (default: TwoPageRight)'
    )
@click.option(
    '--direction', '-D', default=None,
    metavar='<dir>',
    type=click.Choice(['L2R', 'R2L', 'none'], case_sensitive=False),
    help='reading order (/Direction) in the PDF viewer preferences: L2R, R2L, none (default: R2L)'
    )
@click.option(
    '--page-mode', '-m', default=None,
    metavar='<mode>',
    type=click.Choice(['UseOutlines', 'UseNone', 'UseOC',
                       'UseAttachments', 'FullScreen', 'none'],
                      case_sensitive=False),
    help='initial view mode (/PageMode) in the PDF document catalog: UseOutlines, UseNone, UseOC, UseAttachments, FullScreen, none (default: UseOutlines when a TOC outline was written, otherwise no entry)'
    )
@click.option(
    '--zoom', '-z', default=None,
    metavar='<zoom>',
    help='initial magnification (/OpenAction Go To on the first page): default, none, actual, NN% such as 150%, fit_page, fit_width, fit_height, fit_visible, fit_visible_width, fit_visible_height (default: default, i.e. do not write an /OpenAction)'
    )
@click.option(
    '--verbose', '-v', count=True,
    help='output in verbose mode'
    )
def join(img, config, out, toc, ext, dpi, page_layout, direction, page_mode, zoom, verbose):
    """Join images into one PDF file"""
    rc = i2p_join(img, config=config, out=out, toc=toc, ext=ext, dpi=dpi,
                  page_layout=page_layout, direction=direction,
                  page_mode=page_mode, zoom=zoom, verbose=verbose)
    if rc:
        raise SystemExit(rc, "Failed to join images into PDF")

@cli.command()
@click.argument('PATH', type=click.Path(exists=True))
@click.option(
    '--hash-size', '-s', default=8, type=int,
    metavar='<size>',
    help='hash size to use for image hashing (default: 8; accepted but not implemented)'
    )
@click.option(
    '--hash-func', '-f',
    metavar='<hashfunc>',
    type=click.Choice(sorted(HASH_FUNCS), case_sensitive=False),
    default='dhash',
    help='hash function to use for comparing images'
    )
@click.option(
    '--verbose', '-v', count=True,
    help='output in verbose mode'
    )
def dedup(path, hash_size, hash_func, verbose):
    """Find duplicates in PATH using <hashfunc>

    <hashfunc> can be any of the following:

\b
        ahash	: Average hash
        phash	: Perceptual hash
        dhash	: Difference hash (default)
        haar	: Haar wavelet hash
        db4	: Daubechies wavelet hash 
        color	: HSV color hash
        crop	: crop-resistant hash
    """
    rc = find_dup(path, hashfunc=HASH_FUNCS[hash_func], hash_size=hash_size, verbose=verbose)
    if rc:
        raise SystemExit(rc, "Failed to search for duplicate images")

# EXIF Sort
@cli.command()
@click.argument('SRCDIR')
@click.argument('TGTDIR')
@click.option(
    '--copy', 'sortfn', flag_value='copy', default=True,
    help='Copy files from SRCDIR to TGTDIR (Default)'
    )
@click.option(
    '--move', 'sortfn', flag_value='move',
    help='Move files from SRCDIR to TGTDIR'
    )
@click.option(
    '--recurse', '-r', is_flag=True,
    help='Search for images in SRCDIR recursively'
    )
@click.option(
    '--overwrite', '-o', is_flag=True,
    help='Overwrite files in TGTDIR'
    )
@click.option(
    '--hierarch', '-H', is_flag=True,
    help='Create a hierarchical directory for Year, Month and Date in TGTDIR'
    )
@click.option(
    '--dry-run', '-d', is_flag=True,
    help='Dry run the command without moving'
    )
@click.option(
    '--fmt', '-f', default=defaultFmt, type=str,
    metavar='<fmt>',
    help="Format target directory name using date format strftime string give in <fmt> (default: %Y-%m-%d).  Ignored when --hierarch is specified."
    )
@click.option(
    '--verbose', '-v', count=True,
    help='output in verbose mode'
    )
def sort(srcdir, tgtdir, sortfn, recurse, overwrite, hierarch, dry_run, fmt, verbose):
    """Sort and Move/Copy images from SRCDIR to TGTDIR."""
    opts = dict(
        recurse=recurse, overwrite=overwrite, hierarch=hierarch,
        fmt=fmt, dry_run=dry_run, verbose=verbose,
    )
    if sortfn == 'move':
        rc = exifsort_mv(srcdir, tgtdir, **opts)
    else:
        rc = exifsort_cp(srcdir, tgtdir, **opts)
    if rc:
        raise SystemExit(rc, "Failed to sort images")

# Entry point
def main():
    """Main script."""
    try:
        cli()
    except SystemExit as exc:
        args = exc.args
        rc = args[0] if args else 0
        if len(args) > 1:
            click.echo(str(args[1]), err=True)
        sys.exit(rc)

if __name__ == '__main__':
    main()
