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

import yaml
import os
import glob
import re
import tempfile
from pprint import pformat
import click
from fpdf import FPDF
from PIL import Image
# Document catalog settings (PageLayout / ViewerPreferences) are written with
# pikepdf, which emits the name values required by the PDF specification.
from pikepdf import Pdf, Dictionary, Name, ObjectStreamMode

from .._logging import Level, pout


DEFAULT_CONFIG = "./imgtk-join.yml"
DEFAULT_DPI = 96
DEFAULT_OUT = "output.pdf"
DEFAULT_TOC = "toc.yml"
DEFAULT_PAGE_LAYOUT = "TwoPageLeft"
DEFAULT_DIRECTION = "R2L"

# PDF 32000-2008 Table 3.2 (Document Catalog) -- /PageLayout
PAGE_LAYOUT_NAMES = {
    'singlepage': 'SinglePage',
    'onecolumn': 'OneColumn',
    'twocolumnleft': 'TwoColumnLeft',
    'twocolumnright': 'TwoColumnRight',
    'twopageleft': 'TwoPageLeft',
    'twopageright': 'TwoPageRight',
    'none': None,
}
# PDF 32000-2008 Table 3.22 (Viewer Preferences) -- /Direction
DIRECTION_NAMES = {
    'l2r': 'L2R',
    'r2l': 'R2L',
    'none': None,
}


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
                "page_layout: TwoPageLeft\n",
                "direction: R2L\n",
            ])
    except Exception as e:
        pout("could not create {file}: {err}".format(file=conf, err=e), verbose, Level.ERROR)
    pass


def pixelmm(dpi):
    return float(1/dpi)*25.4


numbers = re.compile(r'(\d+)')
def numericalSort(value):
    parts = numbers.split(value)
    parts[1::2] = map(int, parts[1::2])
    return parts


def pdfName(value, names, key):
    """Resolve a document catalog setting to its PDF name.

    The lookup is case insensitive and ignores '-', '_' and spaces so the
    values in the yaml configuration file need not be typed exactly as the
    PDF specification spells them.

    Args:
        value (string): value read from the configuration or command line
        names (dict): mapping of normalized value to PDF name
        key (string): configuration key name used for the error message
    Returns:
        tuple (string|None, string|None): resolved PDF name and error message
              name is None when the setting is turned off ('none')
    """
    if value is None:
        return None, None
    token = re.sub(r'[-_ ]', '', str(value)).lower()
    if token not in names:
        return None, "invalid {key}: {value} (expected one of {allowed})".format(
            key=key, value=value, allowed=", ".join(sorted(names)))
    return names[token], None


def temp_out(out, workdir):
    """Create a temporary file in the same directory as out.

    Keeping the temporary files next to the target means they are on the same
    filesystem, so the final os.replace() is atomic, and it means the target
    is never seen half written.

    Args:
        out (string): target PDF filename
        workdir (string): directory the temporary file should live in
    Returns:
        string -- path of the created (and closed) temporary file
    """
    fd, staged = tempfile.mkstemp(
        dir=workdir,
        prefix="{0}.".format(os.path.basename(out)),
        suffix=".tmp")
    os.close(fd)
    return staged


def remove_tmp(paths, verbose=0):
    """Remove temporary files, reporting but ignoring failures.

    Args:
        paths (sequence): temporary file paths to remove (None entries skipped)
        verbose (int): verbosity level
    """
    for path in paths:
        if not path:
            continue
        try:
            os.remove(path)
        except OSError as e:
            pout("could not remove temporary file {file}: {error}".format(file=path, error=e),
                 verbose, Level.DEBUG)


def writePdf(pdf, out, page_layout: str | None = DEFAULT_PAGE_LAYOUT,
             direction: str | None = DEFAULT_DIRECTION, verbose=0):
    """Write out the generated PDF, setting document catalog viewer defaults.

    The document is composed by fpdf into a temporary file, reopened with
    pikepdf, and the catalog entries are then set or deleted with the name
    values required by PDF 32000-2008 (Table 3.2 for /PageLayout, Table 3.22
    for ViewerPreferences /Direction): fpdf alone would write the invalid
    "/Direction RTL" name.  The result is staged in a second temporary file and
    renamed into place, so a failed run never leaves a partial PDF behind.

    Args:
        pdf (FPDF): the composed document
        out (string): output PDF filename
        page_layout (string|None): PDF /PageLayout name, None removes the entry
        direction (string|None): ViewerPreferences /Direction name, None removes it
        verbose (int): verbosity level
    Returns:
        int -- process exit code (0 on success, non-zero on hard failure)
    """
    if page_layout is None:
        pout('PageLayout is removed from the document catalog', verbose, Level.WARNING)
    if direction is None:
        pout('ViewerPreferences Direction is removed from the document catalog', verbose, Level.WARNING)
    pout("document catalog: PageLayout={page_layout}, Direction={direction}".format(
        page_layout=page_layout, direction=direction), verbose, Level.DEBUG)

    staged = None
    result = None
    try:
        workdir = os.path.dirname(out) or '.'
        staged = temp_out(out, workdir)
        result = temp_out(out, workdir)

        pdf.output(staged)
        with Pdf.open(staged) as composed:
            warnings = composed.get_warnings()
            if warnings:
                pout("pikepdf warnings while reading the composed PDF: {warn}".format(
                    warn="; ".join(str(w) for w in warnings)), verbose, Level.WARNING)

            catalog = composed.Root
            if page_layout:
                catalog.PageLayout = Name("/{0}".format(page_layout))
            elif '/PageLayout' in catalog:
                del catalog['/PageLayout']

            if direction:
                if '/ViewerPreferences' in catalog and catalog.ViewerPreferences.is_dictionary:
                    catalog.ViewerPreferences.Direction = Name("/{0}".format(direction))
                else:
                    catalog.ViewerPreferences = Dictionary(Direction=Name("/{0}".format(direction)))
            elif '/ViewerPreferences' in catalog and catalog.ViewerPreferences.is_dictionary:
                viewer_prefs = catalog.ViewerPreferences
                if '/Direction' in viewer_prefs:
                    del viewer_prefs['/Direction']
                if len(viewer_prefs) == 0:
                    del catalog['/ViewerPreferences']

            # /TwoPageLeft and /TwoPageRight are only defined for PDF 1.5 and later
            composed.save(
                result,
                min_version='1.5' if page_layout in ('TwoPageLeft', 'TwoPageRight') else '',
                object_stream_mode=ObjectStreamMode.preserve,
                compress_streams=False)

        # same directory as out, so this rename is atomic
        os.replace(result, out)
        result = None
        return 0
    except Exception as e:
        pout("could not write {file}: {error}".format(file=out, error=e), verbose, Level.ERROR)
        pout("{error}".format(error=e), verbose, Level.DEBUG)
        return 1
    finally:
        remove_tmp((staged, result), verbose)


def join(img, *, config=DEFAULT_CONFIG, out=None, toc=None, ext=(), dpi=None,
         page_layout=None, direction=None, verbose=0):
    """Convert set of images to PDF.
    Implementation.

    Args:
        img (tuple): image files/directories to merge, in order
    Keyword Arguments:
        config (string) -- yaml config file path
        out (string) -- output PDF filename
        toc (string) -- TOC file used to populate the PDF outline
        ext (sequence) -- file extensions to pick up inside directories
        dpi (int) -- pixel density of the input images
        page_layout (string) -- /PageLayout name for the document catalog, 'none' removes the entry
        direction (string) -- ViewerPreferences /Direction name 'L2R' or 'R2L', 'none' removes the entry
        verbose (int) -- verbosity level
    Returns:
        int -- process exit code (0 on success, non-zero on hard failure)
    """
    verbose = int(verbose)
    params = {
        'img': list(img),
        'config': config,
        'out': out,
        'toc': toc,
        'ext': list(ext),
        'dpi': dpi,
        'page_layout': page_layout,
        'direction': direction,
        'verbose': verbose,
    }
    pout("Command line arguments:", verbose, Level.DEBUG)
    pout(pformat(params,depth=3,indent=4), verbose, Level.DEBUG)

    # 0. Get information from config.yml
    # If file does not exist, create a default config file
    if not os.path.exists(config):
        createConf(config, verbose)
    try:
        with click.open_file(config, 'r') as cnf:
            conf = yaml.safe_load(cnf) or {}
    except Exception as e:
        pout("could not open config file: {file}".format(file=config), verbose, Level.ERROR)
        pout("{error}".format(error=e), verbose, Level.DEBUG)
        return 1

    pout("Read config file:", verbose, Level.DEBUG)
    pout(pformat(conf,depth=3,indent=4), verbose, Level.DEBUG)
    # 1. Now parse kwargs
    conf['ext'] = sorted(set(list(conf.get('ext') or []) + list(ext)))
    conf['img'] = list(img)

    # overwrite some parameters if given in command line
    if toc:
        conf['toc'] = toc
    if out:
        conf['out'] = out
    if dpi:
        conf['dpi'] = dpi
    if page_layout:
        conf['page_layout'] = page_layout
    if direction:
        conf['direction'] = direction

    # provide safe defaults for anything the config file omitted
    conf.setdefault('toc', None)
    conf.setdefault('out', DEFAULT_OUT)
    conf.setdefault('dpi', DEFAULT_DPI)
    conf.setdefault('page_layout', DEFAULT_PAGE_LAYOUT)
    conf.setdefault('direction', DEFAULT_DIRECTION)
    pout("Operating parameter:")
    pout(pformat(conf,depth=3,indent=4), verbose, Level.INFO)

    # resolve the document catalog viewer defaults, 'none' turns the entry off
    page_layout, error = pdfName(conf['page_layout'], PAGE_LAYOUT_NAMES, 'page_layout')
    if error:
        pout(error, verbose, Level.ERROR)
        return 1
    direction, error = pdfName(conf['direction'], DIRECTION_NAMES, 'direction')
    if error:
        pout(error, verbose, Level.ERROR)
        return 1

    # 2. Main application logic

    # Check if there are any files in img. if empty exit gracefully
    if len(conf['img']) == 0:
        pout("nothing to parse", verbose, Level.INFO)
        return 0

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
    return writePdf(pdf, conf['out'], page_layout=page_layout, direction=direction, verbose=verbose)
