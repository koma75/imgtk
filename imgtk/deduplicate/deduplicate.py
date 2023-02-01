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


import os
import shutil
import re
from pprint import pformat
import click
from PIL import Image
import imagehash

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

#	if hashmethod == 'ahash':
#		hashfunc = imagehash.average_hash
#	elif hashmethod == 'phash':
#		hashfunc = imagehash.phash
#	elif hashmethod == 'dhash':
#		hashfunc = imagehash.dhash
#	elif hashmethod == 'whash-haar':
#		hashfunc = imagehash.whash
#	elif hashmethod == 'whash-db4':
#		def hashfunc(img):
#			return imagehash.whash(img, mode='db4')
#	elif hashmethod == 'colorhash':
#		hashfunc = imagehash.colorhash
#	elif hashmethod == 'crop-resistant':
#		hashfunc = imagehash.crop_resistant_hash
#	else:
#		usage()


def find_dup(kwargs, hashmethod='ahash'):
    """Image Duplicate finder using Image Hash.
    Implementation.

    Args:
        kwargs (dict): command line arguments parsed by Click library
    """
    verbose = kwargs["verbose"]
    pout("Command line arguments:", verbose, Level.DEBUG)
    pout(pformat(kwargs,depth=3,indent=4), verbose, Level.DEBUG)

    # 1. Now parse arguments
    
    hashsize = kwargs["hash_size"]
    if hashsize < 1:
        pout(f"Hash size must be a positive integer [{hashsize}]", verbose, Level.ERROR)
        exit(1)
        
    dir_path = kwargs["path"]
    if not os.path.isdir(dir_path):
        pout(f"Path {dir_path} does not exist.  Specify directory with images.", verbose, Level.ERROR)
        exit(1)

    # Set the hash method based on input
    if hashmethod == 'ahash':
        hashfunc = imagehash.average_hash
    elif hashmethod == 'phash':
        hashfunc = imagehash.phash
    elif hashmethod == 'dhash':
        hashfunc = imagehash.dhash
    elif hashmethod == 'whash-haar':
        hashfunc = imagehash.whash
    elif hashmethod == 'whash-db4':
        def hashfunc(img):
            return imagehash.whash(img, mode='db4')
    elif hashmethod == 'colorhash':
        hashfunc = imagehash.colorhash
    elif hashmethod == 'crop-resistant':
        hashfunc = imagehash.crop_resistant_hash
    else:
        pout("no hash method set, falling back to difference hash", verbose, Level.WARNING)
        hashfunc = imagehash.dhash

    # 2. and do it's bidding
    # Initialize image sort dictionary (key=hash, value=array of image paths with that hash value)
    himages = {}

    # Find image files and put them in an array
    def is_image(filename):
        f = filename.lower()
        return f.endswith('.png') or f.endswith('.jpg') or \
            f.endswith('.jpeg') or f.endswith('.bmp') or \
            f.endswith('.jfif') or f.endswith('.gif') or '.jpg' in f or f.endswith('.svg')

    image_paths = []
    image_paths += [os.path.join(dir_path, path) for path in os.listdir(dir_path) if is_image(path)]
    pout(image_paths, verbose, Level.DEBUG)
    
    if len(image_paths) == 0:
        pout(f"No images found inside {dir_path}", verbose, Level.INFO)
        exit(0)

    # Check the hash value for each file and insert into the himages dictionary
    with click.progressbar(image_paths) as imgpaths:
        for img in imgpaths:
            try:
                hash = f"{hashfunc(Image.open(img))}"
            except Exception as e:
                pout(f"\nProblem: {e} with {img}", verbose, Level.ERROR)
                continue
            if hash not in himages:
                himages[hash] = [img]
            else:
                himages[hash] += [img]

    # for each hash value, check if there are more than one image for a hash.
    # create a subdirectory for the hash value and move all images with the hash into the directory
    for himage in himages:
        numImg = len(himages[himage])
        if numImg > 1:
            # Similar image found
            # make a directory for that hash and move the images inside
            hashdir = os.path.join(dir_path, himage)
            if os.path.exists(hashdir):
                pout(f"{hashdir} already exists")
            else:
                try:
                    os.mkdir(hashdir)
                except Exception as e:
                    pout(f"Could not create directory {hashdir}: {e}", verbose, Level.ERROR)
                    continue
            for img in himages[himage]:
                pout(f"{img} to {os.path.join(hashdir,os.path.basename(img))}", verbose, Level.DEBUG)
                shutil.move(img, os.path.join(hashdir,os.path.basename(img)))

    pass
