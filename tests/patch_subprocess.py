import subprocess
import os
import logging

from crl.interactivesessions.pexpectplatform import is_windows


__copyright__ = 'Copyright (C) 2019, Nokia'

logger = logging.getLogger(__name__)


if is_windows():
    origpopen = subprocess.Popen

    def windowspopen(*args, **kwargs):
        kwargsmod = kwargs.copy()
        if 'preexec_fn' in kwargs:
            del kwargsmod['preexec_fn']
        if 'executable' in kwargsmod:
            del kwargsmod['executable']
        logger.debug('origpopen(args=%s, kwargs=%s)', args, kwargsmod)

        return origpopen(*args, **kwargsmod)

    os.setsid = lambda *args, **kwargs: None
    subprocess.Popen = windowspopen
