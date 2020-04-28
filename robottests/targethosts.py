"""Robot Framework variable file for robottests.

This is variable file for docker-robottests cluster"""

import os
import sys

__copyright__ = 'Copyright (C) 2019-2020, Nokia'


PYTHON_MAJOR = sys.version_info.major


def get_port(target):
    envpy = 'PY{}'.format(PYTHON_MAJOR)
    return os.environ['PORT_{envpy}_{target}'.format(envpy=envpy,
                                                     target=target)]


def update_sshshell_dicts(*shelldicts):
    for s in shelldicts:
        s['host'] = s.get('host', 'localhost')
        s.update({'user': 'root',
                  'password': 'targetpassword'})


DICT__HOST1 = {'port': get_port('PY2')}
DICT__HOST2 = {'port': get_port('PY3')}
DICT__GW = {'port': get_port('GW')}
DICT__HOST1_VIA_GW = {'host': 'py{}-py2'.format(PYTHON_MAJOR)}
DICT__HOST2_VIA_GW = {'host': 'py{}-py3'.format(PYTHON_MAJOR)}
DICT__HOST3_VIA_GW = {'host': 'py{}-py3-no-symlink'.format(PYTHON_MAJOR),
                      'python_command': 'python3'}
DICT__HOST4_VIA_GW = {'host': 'py{}-py3-no-symlink'.format(PYTHON_MAJOR),
                      'init_env': 'content: alias python=python3'}

SUDOSHELL = {'shellname': 'BashShell', 'cmd': 'sudo /bin/bash'}
KEYAUTHENTICATEDSHELL = {'host': 'localhost',
                         'initial_prompt': '# ',
                         'shellname': 'KeyAuthenticatedSshShell'}


update_sshshell_dicts(DICT__HOST1,
                      DICT__HOST2,
                      DICT__GW,
                      DICT__HOST1_VIA_GW,
                      DICT__HOST2_VIA_GW,
                      DICT__HOST3_VIA_GW,
                      DICT__HOST4_VIA_GW
                      )
