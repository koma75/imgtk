#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 koma <okunoya@path-works.net>
# SPDX-License-Identifier: BSD-2-Clause


"""
Console logging helpers shared by all imgtk subcommands.

.. currentmodule:: imgtk._logging
.. moduleauthor:: koma <okunoya@path-works.net>
"""

from enum import IntEnum

import click
import re


CONTROL_CHARACTERS = re.compile(r'[\x00-\x08\x0b-\x1f\x7f\x80-\x9f]')


def sanitize(msg):
    """Strip control characters from a message before it reaches the terminal.

    Configuration-derived strings (filenames, option values read from yaml) are
    echoed to the terminal, and unescaped control characters in them could
    otherwise write escape sequences to the console.

    Args:
        msg (string): message to clean up
    Returns:
        string -- message with newline and tab preserved, other control
              characters removed
    """
    return CONTROL_CHARACTERS.sub('', str(msg))


class Level(IntEnum):
    NOTSET = 0
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


def pout(msg=None, Verbose=0, level=Level.INFO, newline=True):
    """stdout support method
    All Error, Critical and Info are printed out.
    while Warning and Debug are printed only with verbosity setting.
    INFO -- Intended for standard output. output to STDOUT
    DEBUG -- Intended for debug output. Shown only in verbosity>=2 output to STDOUT
    WARNING -- Intended to show detailed warning. Shown only in verbosity>=1.  output to STDERR
    ERROR -- Intended to show error.  output to STDERR
    CRITICAL -- Intended to show critical error. output to STDERR

    Keyword Arguments:
        msg (string) -- message to print (default: {None})
        Verbose (Int) -- Set True to print DEBUG message (default: {0})
        level (Level) -- Set message level for coloring (default: {Level.INFO})
        newline (bool) -- set to False if trailing new line is not needed (default: {True})
    """
    error=False
    if level in {Level.NOTSET, Level.DEBUG}:
        # blah
        if Verbose < 2:
            return
        fg = 'magenta'
    elif level == Level.INFO:
        fg = 'green'
    elif level == Level.WARNING:
        if Verbose < 1:
            return
        fg = 'yellow'
        error=True
    elif level in {Level.ERROR, Level.CRITICAL}:
        fg = 'red'
        error=True
    else:
        fg = 'white'
    click.echo(click.style(sanitize(msg), fg=fg), nl=newline, err=error)
