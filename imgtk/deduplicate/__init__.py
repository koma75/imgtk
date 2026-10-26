#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 koma <okunoya@path-works.net>
# SPDX-License-Identifier: BSD-2-Clause


"""
Image Duplicate finder using Image Hash.

.. currentmodule:: imgtk.deduplicate
.. moduleauthor:: koma <okunoya@path-works.net>
"""

from .deduplicate import find_dup, HASH_FUNCS

__all__ = ['find_dup', 'HASH_FUNCS']
