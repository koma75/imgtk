#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BSD 2-Clause License
# 
# Copyright (c) 2023 koma <okunoya@path-works.net>
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Main CLI Setup and Entrypoint."""

from __future__ import absolute_import, division, print_function

# Import the main click library
import click
# Import the sub-command implementations
from imgtk.exifsort import exifsort
from imgtk.i2p import i2p
from imgtk.deduplicate import deduplicate
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
    '--verbose', '-v', count=True,
    help='output in verbose mode'
    )
def join(**kwargs):
    """Join images into one PDF file"""
    i2p.join(kwargs)
    pass

@cli.command()
@click.argument('PATH', type=click.Path(exists=True))
@click.option(
    '--hash-size', '-s', default=8, type=int,
    metavar='<size>',
    help='hash size to use for image hashing (default: dhash)'
    )
@click.option(
    '--hash-func', '-f', 
    metavar='<hashfunc>',
    type=click.Choice(
        [
            'ahash',
            'phash',
            'dhash',
            'haar',
            'db4',
            'color',
            'crop'
        ], 
        case_sensitive=False
    ),
    default='dhash',
    help='hash function to use for comparing images'
    )
@click.option(
    '--verbose', '-v', count=True,
    help='output in verbose mode'
    )
def dedup(**kwargs):
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
    # convert cli option to find_dup method
    func_switch = {
        'ahash':'ahash',
        'phash':'phash',
        'dhash':'dhash',
        'haar':'whash-haar',
        'db4':'whash-db4',
        'color':'colorhash',
        'crop':'crop-resistant'
    }
    if kwargs['hash_func'] in func_switch:
        hfunc=func_switch[kwargs['hash_func']]
    else:
        hfunc='dhash'

    deduplicate.find_dup(kwargs, hashmethod=hfunc)
    pass

# EXIF Sort
defaultFmt = r'%Y-%m-%d'

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
    help="Format target directory name using date format strftime string give in <fmt> (default: %Y-%m-%d)."
    )
@click.option(
    '--verbose', '-v', count=True,
    help='output in verbose mode'
    )
def sort(**kwargs):
    """Sort and Move/Copy images from SRCDIR to TGTDIR."""
    if kwargs['sortfn'] == 'move':
        exifsort.mv(kwargs)
    else:
        exifsort.cp(kwargs)

# Entry point
def main():
    """Main script."""
    cli()

if __name__ == '__main__':
    main()
