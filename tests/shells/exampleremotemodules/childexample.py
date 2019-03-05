"""Example module child
"""
if 'grandchildexample' not in globals():
    from . import grandchildexample


__copyright__ = 'Copyright (C) 2019, Nokia'

CHILD_MODULES = [grandchildexample]


def child_func():
    return grandchildexample.grandchild_func()
