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

from enum import IntEnum


import yaml
import os
import re
from pprint import pformat
import click

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
        pass
    click.echo(click.style(str(msg), fg=fg), nl=newline, err=error)


def createConf(conf, verbose):
    """Generate default configuratino at path specified in conf

    Args:
        conf (string): Path to generate default configuration file to.
        verbose (int): Verbosity level
    """
    try:
        with click.open_file(conf, 'w', 'utf-8') as fd:
            fd.writelines([
                "option1: option1param\n",
                "option2: option2param\n",
                "optionArray:\n",
                "  - item1\n",
                "  - item2\n",
                "optionDict:\n",
                "  key1: item1\n",
                "  key2: item2\n",
                "  key3: item3\n",
            ])
    except:
        pout("could not create {file}".format(file=conf), verbose, Level.ERROR)
    pass

def cmd(kwargs):
    """Image file manipulation toolkit
    Implementation.

    Args:
        kwargs (dict): command line arguments parsed by Click library
    """
    verbose = kwargs["verbose"]
    pout("Command line arguments:", verbose, Level.INFO)
    pout(pformat(kwargs,depth=3,indent=4), verbose, Level.INFO)


    # 0. Get information from config.yml
    # If file does not exist, create a default config file
    if not os.path.exists(kwargs['config']):
        createConf(kwargs['config'], verbose)
    try:
        with click.open_file(kwargs['config'], 'r') as cnf:
            conf = yaml.safe_load(cnf)
    except:
        pout("could not open config file: {file}".format(file=kwargs['config']), verbose, Level.ERROR)

    pout("Read config file:", verbose, Level.INFO)
    pout(pformat(conf,depth=3,indent=4), verbose, Level.INFO)
    # 1. Now parse kwargs
    # TODO: it may be a good time to merge the options specified in kwargs into conf to put all
    #       execution parameters in one place.

    # 2. and do it's bidding

    pass
