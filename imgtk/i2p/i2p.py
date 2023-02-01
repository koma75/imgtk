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
import glob
import re
from pprint import pformat
import click
from fpdf import FPDF
from PIL import Image

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
                "out: output.pdf\n",
                "toc: toc.yml\n",
                "dpi: 96\n",
                "ext:\n",
                "  - jpg\n",
                "  - jpeg\n",
                "  - png\n",
            ])
    except:
        pout("could not create {file}".format(file=conf), verbose, Level.ERROR)
    pass

def pixelmm(dpi):
    return float(1/dpi)*25.4

numbers = re.compile(r'(\d+)')
def numericalSort(value):
    parts = numbers.split(value)
    parts[1::2] = map(int, parts[1::2])
    return parts

def join(kwargs):
    """Convert set of images to PDF.
    Implementation.

    Args:
        kwargs (dict): command line arguments parsed by Click library
    """
    verbose = kwargs["verbose"]
    pout("Command line arguments:", verbose, Level.DEBUG)
    pout(pformat(kwargs,depth=3,indent=4), verbose, Level.DEBUG)


    # 0. Get information from config.yml
    # If file does not exist, create a default config file
    if not os.path.exists(kwargs['config']):
        createConf(kwargs['config'], verbose)
    try:
        with click.open_file(kwargs['config'], 'r') as cnf:
            conf = yaml.safe_load(cnf)
    except Exception as e:
        pout("could not open config file: {file}".format(file=kwargs['config']), verbose, Level.ERROR)
        pout("{error}".format(error=e), verbose, Level.DEBUG)
        return

    pout("Read config file:", verbose, Level.DEBUG)
    pout(pformat(conf,depth=3,indent=4), verbose, Level.DEBUG)
    # 1. Now parse kwargs
    conf['ext'].extend(kwargs['ext'])
    conf['ext'] = sorted(set(conf['ext']))
    conf['img'] = kwargs['img']
    
    # overwrite some parameters if given in command line
    if kwargs['toc']:
        conf['toc'] = kwargs['toc']
    if kwargs['out']:
        conf['out'] = kwargs['out']
    if kwargs['dpi']:
        conf['dpi'] = kwargs['dpi']
    pout("Operating parameter:")
    pout(pformat(conf,depth=3,indent=4), verbose, Level.INFO)

    # 2. Main application logic

    # Check if there are any files in img. if empty exit gracefully
    if len(conf['img']) == 0:
        pout("nothing to parse", verbose, Level.INFO)
        return

    # for each img merge into one list of image files
    #   for direcotry, parse for files with specified extensions
    #   for image, append to list
    #   files in directories should be sorted. but should not sort the final result.
    images = []
    for path in conf['img']:
        if os.path.isdir(path):
            # find all files in specified directory
            tmpImages = []
            for extension in conf['ext']:
                tmpImages.extend(
                    glob.glob(os.path.join(
                        path,
                        "*.{ext}".format(ext=extension))))
            images.extend(sorted(set(tmpImages), key=numericalSort))
        else:
            # is a file.
            images.append(path)
    pout(images, verbose, Level.DEBUG)

    # read in TOC data if available
    try:
        with open(conf['toc'], encoding='utf-8') as tocfile:
            toc = yaml.safe_load(tocfile)
    except Exception as e:
        # if toc cannot be read, just make empty TOC
        pout(e, verbose, Level.ERROR)
        pout('ToC Will not be populated due to toc file read error', verbose, Level.WARNING)
        toc = {} 

    # for each file in list, get width/height, calculate size in mm, 
    # use w/h to create new pdf page and add the image to the pdf
    # if toc file is available, parse and append to the outline of the PDF file.
    pdf = FPDF()
    pixelsize = pixelmm(conf['dpi'])
    pout("pixelsize: {size}".format(size=pixelsize), verbose, Level.DEBUG)
    pageNum = 0

    with click.progressbar(images) as imgs:
        for path in imgs:
            try:
                pout("process {path}".format(path=path), verbose, Level.DEBUG)
                imageFile = Image.open(path)
            except Exception as e:
                pout(e, verbose, Level.WARNING)
                continue
            iw, ih = imageFile.size
            # convert pixel in mm with 1px=0.264483 mm (assuming 96dpi)
            iw, ih = float(iw * pixelsize), float(ih * pixelsize)
            pout("width: {width}, height: {height}".format(width=iw, height=ih), verbose, Level.DEBUG)
            pageNum += 1

            pdf.add_page(orientation='P', format=(iw,ih))
            if pageNum in toc:
                # If there is an entry in the toc for the page, 
                for item in toc[pageNum]:
                    try:
                        pdf.start_section(item['title'], item['level'])
                    except Exception as e:
                        pout("toc parse error: {err}".format(err=e),verbose,Level.WARNING)
            try:
                pdf.image(path, 0, 0, iw, ih)
            except Exception as e:
                pout(e, verbose, Level.WARNING)

    # Write out result
    try:
        pdf.output(conf['out'], 'F')
    except Exception as e:
        pout(e,verbose, Level.ERROR)
    pass
