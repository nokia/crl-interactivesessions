import logging
from .shells import *


__copyright__ = 'Copyright (C) 2019, Nokia'


logging.getLogger('crl.interactivesessions').addHandler(
    logging.NullHandler())
