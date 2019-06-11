import logging
from .shells import *  # noqa: F401, F403


__copyright__ = 'Copyright (C) 2019, Nokia'


logging.getLogger('crl.interactivesessions').addHandler(
    logging.NullHandler())
