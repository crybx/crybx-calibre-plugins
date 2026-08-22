#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Shared helpers for deriving chapter numbers from filenames.

Used by both the "Import chapters" option (which stores the result in
#lastimport) and "Create epub(s) from folder(s) of HTML files" (which stores
it in #contents), so the two columns stay consistent.
"""

import re


def chapter_sort_key(filename):
    """
    Sort key that orders chapter filenames numerically rather than
    lexically, so 'auto_2' comes before 'auto_10'. All digits in the
    filename are concatenated; filenames without digits sort first.
    """
    digits = ''.join(c for c in filename if c in '0123456789')
    return int(digits) if digits else 0


def chapter_number_from_filename(filename, default=None):
    """
    Build a dot separated chapter number from each group of digits in the
    filename, e.g. 'v1c14.html' -> '1.14'. Leading zeros are stripped, so
    'chapter_007.html' -> '7'. Returns 'default' when there are no digits.
    """
    digit_groups = re.findall(r'\d+', filename)
    if not digit_groups:
        return default
    return '.'.join(str(int(g)) for g in digit_groups)
