#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""Test suite for prepare_metadata

(Because it's trickier to get right, so a test suite is prioritized)
"""

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "MIT"

from nose.tools import assert_raises, eq_
import prepare_metadata

test_data = [
    {
        'id': 1,
        'parent_id': None,
        'title': 'Test title 1',
        'author': 'author 1',
        'author_email': None,
        'tags': [],
        'thread': None
    },
    {
        'id': 2,
        'parent_id': 1,
        'title': 'Test title 2',
        'author': 'author 2',
        'author_email': "foo@example.com",
        'tags': ['dark'],
        'thread': 'Well, that got dark quickly'
    },
    {
        'id': 3,
        'parent_id': 1,
        'title': 'Test title 3',
        'author': 'author 1',
        'author_email': None,
        'tags': ['waff', 'lime'],
        'thread': None
    },
]


def test_records_as_ids():
    """records_as_ids: basic function"""
    eq_(list(sorted(prepare_metadata.records_as_ids(test_data, 'id'))),
        [1,2,3])

    eq_(list(sorted(prepare_metadata.records_as_ids(test_data, 'title'))),
        ['Test title 1', 'Test title 2', 'Test title 3'])

def test_render_inner_single():
    """render_inner_single: basic function"""
    eq_(prepare_metadata.render_inner_single([test_data[0]]), test_data[0])

    assert_raises(prepare_metadata.BadInputError,
                  prepare_metadata.render_inner_single, test_data)

# vim: set sw=4 sts=4 expandtab :
