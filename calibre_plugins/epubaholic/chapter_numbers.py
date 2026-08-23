#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Shared helpers for finding chapter files in a folder and deriving chapter
numbers from their filenames.

Used by the "Import chapters" option (which stores the result in #lastimport),
"Import chapters from folder\u2026" and "Create epub(s) from folder(s) of HTML
files\u2026" (which stores it in #contents), so they all agree on which files
count as chapters, what order they are in, and how they are numbered.
"""

import os
import re

HTML_EXTENSIONS = ('.html', '.htm', '.xhtml')


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


def html_chapter_files(folder):
    """
    Return the names of the HTML files in 'folder', ordered by
    chapter_sort_key. Returns an empty list when the folder is missing or
    holds no HTML files.
    """
    try:
        names = os.listdir(folder)
    except EnvironmentError:
        return []
    names = [n for n in names if n.lower().endswith(HTML_EXTENSIONS)]
    return sorted(names, key=chapter_sort_key)
