#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 koma <okunoya@path-works.net>
# SPDX-License-Identifier: BSD-2-Clause

from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import partial
from tqdm import tqdm


import os
import shutil
from pprint import pformat
from PIL import Image
import imagehash

from .._logging import Level, pout


# Single source of truth mapping a short CLI hash name to the imagehash
# callable used to hash an image.  Both the CLI option parser and find_dup
# derive their behaviour from this table.
HASH_FUNCS = {
    'ahash': imagehash.average_hash,
    'phash': imagehash.phash,
    'dhash': imagehash.dhash,
    'haar': imagehash.whash,
    'db4': partial(imagehash.whash, mode='db4'),
    'color': imagehash.colorhash,
    'crop': imagehash.crop_resistant_hash,
}


def compute_hash(path, hashfunc, verbose):
    # TODO: --hash-size is accepted on the command line but is not implemented:
    # hash_size is never forwarded here, so every hash function runs at its own
    # built-in default size (8).  Thread a hash_size argument through this
    # helper and bind it per function before wiring it up (colorhash() takes no
    # hash_size, and crop_resistant_hash() needs hash_func=partial(dhash,
    # hash_size=<size>)).
    try:
        return f"{hashfunc(Image.open(path))}", path
    except Exception as e:
        pout(f"\nProblem: {e} with {path}", verbose, Level.ERROR)
        return None


def is_image(filename):
    f = filename.lower()
    return f.endswith('.png') or f.endswith('.jpg') or \
        f.endswith('.jpeg') or f.endswith('.bmp') or \
        f.endswith('.jfif') or f.endswith('.gif') or '.jpg' in f or f.endswith('.svg')


def find_dup(path, *, hashfunc=imagehash.dhash, hash_size=8, verbose=0):
    """Image Duplicate finder using Image Hash.
    Implementation.

    Args:
        path (string): directory with images to check for duplicates
    Keyword Arguments:
        hashfunc (callable): imagehash callable to hash images with
        hash_size (int): hash size used for image hashing
        verbose (int): verbosity level
    Returns:
        int -- process exit code (0 on success, non-zero on hard failure)
    """
    verbose = int(verbose)
    pout("Command line arguments:", verbose, Level.DEBUG)
    pout(pformat({'path': path, 'hash_size': hash_size, 'verbose': verbose}, depth=3, indent=4), verbose, Level.DEBUG)

    # 1. Now parse arguments

    # TODO: hash_size is only range-checked and then dropped; it is not applied
    # to the hashing (see compute_hash).  README documents --hash-size as
    # "not implemented" and lists it under Known Issues.
    if hash_size < 1:
        pout(f"Hash size must be a positive integer [{hash_size}]", verbose, Level.ERROR)
        return 1

    dir_path = path
    if not os.path.isdir(dir_path):
        pout(f"Path {dir_path} does not exist.  Specify directory with images.", verbose, Level.ERROR)
        return 1

    # 2. and do it's bidding
    # Initialize image sort dictionary (key=hash, value=array of image paths with that hash value)
    himages = {}

    # Find image files and put them in an array
    image_paths = []
    image_paths += [os.path.join(dir_path, p) for p in os.listdir(dir_path) if is_image(p)]
    pout(image_paths, verbose, Level.DEBUG)

    if len(image_paths) == 0:
        pout(f"No images found inside {dir_path}", verbose, Level.INFO)
        return 0

    with ProcessPoolExecutor() as executor:
        futures = [executor.submit(compute_hash, img, hashfunc, verbose) for img in image_paths]
        for future in tqdm(as_completed(futures), total=len(image_paths), desc="Processing images"):
            result = future.result()
            if result is not None:
                hash_val, img = result
                if hash_val not in himages:
                    himages[hash_val] = [img]
                else:
                    himages[hash_val].append(img)

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

    return 0
