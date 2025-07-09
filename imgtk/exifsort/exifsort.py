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

import os
import platform
import re
import shutil
import time
from datetime import date
from enum import IntEnum

from PIL import ExifTags
import click
from PIL import Image
from PIL.ExifTags import TAGS

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


def copyImage(src, dst, dryrun=False, overwrite=False, verbose=False):
    """Copy image from src to dst

    Arguments:
        src {string} -- path to image to copy
        dst {string} -- path to copy src to

    Keyword Arguments:
        dryrun {bool} -- Set to True to dry-run command (default: {False})
        overwrite {bool} -- Set to True to overwrite any files in dst (default: {False})
        verbose {bool} -- Set to True for verbose messages (default: {False})
    """
    pout("{img} => {toDir}".format(img=os.path.abspath(src), toDir=os.path.abspath(dst)), verbose, Level.INFO)
    if not dryrun:
        if os.path.exists(dst):
            if overwrite:
                # delete file and copy
                try:
                    os.remove(dst)
                except:
                    pout("could not overwrite {file}".format(file=dst))
                    return
            else:
                pout("{file} already exists.".format(file=dst), verbose, Level.WARNING)
                return
        try:
            os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
            shutil.copy2(os.path.abspath(src), os.path.abspath(dst))
        except:
            pout("could not copy to {file}".format(file=os.path.abspath(dst)), verbose, Level.WARNING)
    else:
        pout("DRY RUN... nothing is copied", verbose, Level.INFO)

def moveImage(src, dst, dryrun=False, overwrite=False, verbose=False):
    """Move image from src to dst

    Arguments:
        src {string} -- path to image to move
        dst {string} -- path to move src to

    Keyword Arguments:
        dryrun {bool} -- Set to True to dry-run command (default: {False})
        overwrite {bool} -- Set to True to overwrite any files in dst (default: {False})
        verbose {bool} -- Set to True for verbose messages (default: {False})
    """
    pout("{img} => {toDir}".format(img=os.path.abspath(src), toDir=os.path.abspath(dst)), verbose, Level.INFO)
    if not dryrun:
        if os.path.exists(dst):
            if overwrite:
                # delete file and copy
                try:
                    os.remove(dst)
                except:
                    pout("could not overwrite {file}".format(file=dst))
                    return
            else:
                pout("{file} already exists.".format(file=dst), verbose, Level.WARNING)
                return
        try:
            os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
            shutil.move(os.path.abspath(src), os.path.abspath(dst))
        except:
            pout("could not move to {dst}".format(dst=os.path.abspath(dst)), verbose, Level.WARNING)
    else:
        pout("DRY RUN... nothing is moved", verbose, Level.INFO)

def creation_date(path_to_file):
    """Try to get the date that a file was created, falling back to when it was
    last modified if that isn't possible.
    See http://stackoverflow.com/a/39501288/1709587 for explanation.

    Arguments:
        path_to_file {string} -- Path to the file

    Returns:
        datetime.date -- returns date object with the creation date of file.
    """
    if platform.system() == 'Windows':
        return date(*time.localtime(os.path.getctime(path_to_file))[:3])
    else:
        stat = os.stat(path_to_file)
        try:
            return date(*time.localtime(stat.st_birthtime)[:3])
        except AttributeError:
            # We're probably on Linux. No easy way to get creation dates here,
            # so we'll settle for when its content was last modified.
            return date(*time.localtime(stat.st_mtime)[:3])

def getDateOfImage(fpath, verbose=False):
    """Get the date of image from exif, or file creation time

    Arguments:
        fpath {string} -- path to image file

    Keyword Arguments:
        verbose {bool} -- Set True to output verbose messages. (default: {False})

    Returns:
        datetime.date -- date of image taken, or file created.
    """
    rt = None
    # First try to get date from exif
    try:
        img = Image.open(fpath)
        exif = img.getexif()
        exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)
        if exif:
            exif_dict = {TAGS.get(k,k): v for k, v in exif.items()}
            exif_ifd_dict = {TAGS.get(k,k): v for k, v in exif_ifd.items()}
            pout(f"exif_dict: {exif_dict}", verbose, Level.DEBUG)
            pout(f"exif_ifd_dict: {exif_dict}", verbose, Level.DEBUG)
            dtArr = None
            if "DateTimeOriginal" in exif_ifd_dict:
                dtArr = re.split('[ :]', exif_ifd_dict['DateTimeOriginal'])
            elif "DateTimeDigitized" in exif_ifd_dict:
                dtArr = re.split('[ :]', exif_ifd_dict['DateTimeDigitized'])
            elif "DateTime" in exif_ifd_dict:
                dtArr = re.split('[ :]', exif_ifd_dict['DateTime'])
            elif "DateTime" in exif_dict:
                dtArr = re.split('[ :]', exif_dict['DateTime'])
            if dtArr is not None:
                rt = date(int(dtArr[0]), int(dtArr[1]), int(dtArr[2]))
        img.close()
    except Exception as e:
        pout(f"{fpath} not a supported image format: {e}",
            verbose,
            Level.DEBUG)
    if rt is None:
        rt = creation_date(fpath) # still needed to support .mov and other files
    return rt

def getImages(flist=[], verbose=False):
    """Get images information from list of paths to images

    Keyword Arguments:
        flist {list} -- list of paths to image files (default: {[]})
        verbose {bool} -- set Verbose mode to print extra messages (default: {False})
    """
    for fpath in flist:
        dateinfo = getDateOfImage(fpath, verbose)
        # if datetimeinfor is "NON", get the date from os
        yield ({"path": fpath, "date" : dateinfo})

def getTgtDir(basePath, fmt, filedate, filename, hierarch=False, verbose=False, makedir=False):
    """Generate the path to move file to, based on base path and format.
    If the path does not exist, directories may be generated with makedir flag.

    Arguments:
        basePath {string} -- path where directories are made
        fmt {string} -- format string to use to create subdirectories
        filedate {datetime.date} -- date the image was taken or created
        filename {string} -- filename of the image

    Keyword Arguments:
        hierarch {bool} -- Set to true to create a new hierarchical path %Y/%m/%d (default: {False})
        verbose {bool} -- Set Verbose mode to output extra messages (default: {False})
        makedir {bool} -- Set true to create directories if it does not exist (default: {False})

    Returns:
        string -- path to move files to
    """
    rt = None
    if not hierarch:
        rt = os.path.join(basePath, filedate.strftime(fmt))
    else:
        rt = os.path.join(basePath, filedate.strftime(r"%Y"), filedate.strftime(r"%m"), filedate.strftime(r"%d"))
    if makedir:
        os.makedirs(rt, exist_ok=True)
    return os.path.join(rt, filename)

def sort(kwargs, func):
    """Sort images to sorted directories using func

    Arguments:
        kwargs {dict} -- command line argument parsed by click library
        func {function} -- function to use to process images
    """
    # 'srcdir': source directory to search (string)
    sSrc = kwargs['srcdir']
    # 'tgtdir': target directory to move/copy to (string)
    sTgt = kwargs['tgtdir']
    # 'recurse': recursively search inside srcdir (bool)
    bRec = kwargs['recurse']
    # 'overwrite': overwrite target (bool)
    bOverwrite = kwargs['overwrite']
    # 'hierarch': create hierarchical subdirectory structure in tgtdir (bool)
    bHier = kwargs['hierarch']
    # 'fmt': date format to use as subdirectory name in tgtdir (string)
    sFmt = kwargs['fmt']
    # 'verbose': verbose mode flag (bool)
    bVerb = kwargs['verbose']
    # 'dry-run':
    bDry = kwargs['dry_run']
    # Step 1:
    # search for images in kwargs["srcdir"]
    # TODO: prune file list of non-image files based on file extensions
    # jpg, jpeg, png, gif, tiff, tif, bmp, webp, img
    flist = []
    if bRec:
        for subdir, _, files in os.walk(sSrc):
            for fpath in files:
                flist.append(subdir + os.sep + fpath)
    else:
        for fpath in os.listdir(sSrc):
            flist.append(sSrc + os.sep + fpath)
    pout(flist, bVerb, Level.DEBUG)
    extensions = ( '.jpg', '.jpeg', '.png', '.gif', '.tif', '.tiff', '.bmp', '.webp', '.img', '.mov', '.mp4', '.3gp', '.avi', 'heic')
    flist = [ file for file in flist if file.lower().endswith(extensions) ]
    # Step 2:
    # Move/Copy files to kwargs["dstdir"]/<formatted date dir>
    i = 0
    num = len(flist)
    for image in getImages(flist, bVerb):
        pout(image, bVerb, Level.DEBUG)
        i += 1
        pout("{current}/{total} : ".format(
            current=i,
            total=num),
            bVerb, Level.INFO, newline=False)
        func(image["path"],
            getTgtDir(
                sTgt,
                sFmt,
                image["date"],
                os.path.basename(image["path"]),
                bHier,
                bVerb),
            bDry,
            bOverwrite,
            bVerb)
        # use func(src, dst, verbose) to move/copy image to appropriate path
    return

def cp(kwargs):
    """Copy images to sorted directories

    Arguments:
        kwargs {dict} -- command line arguments parsed by click library
    """
    # Copy images to sorted directories.
    pout(kwargs, kwargs["verbose"], Level.DEBUG)
    sort(kwargs, copyImage)
    pass

def mv(kwargs):
    """Move images to sorted directories

    Arguments:
        kwargs {dict} -- command line arguments parsed by click library
    """
    pout(kwargs, kwargs["verbose"], Level.DEBUG)
    sort(kwargs, moveImage)
    pass
