"""Example module main
"""
if 'childexample' not in globals():
    from . import (
        childexample,
        grandchildexample)


__copyright__ = 'Copyright (C) 2019, Nokia'

CHILD_MODULES = [childexample, grandchildexample]


def call_descendants():
    return 'child: {child}, grandchild: {grandchild}'.format(
        child=childexample.child_func(),
        grandchild=grandchildexample.grandchild_func())
