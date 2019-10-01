# pylint: disable=no-member,import-outside-toplevel
import os
import sys
from setuptools import setup, find_packages


__copyright__ = 'Copyright (C) 2019, Nokia'

VERSIONFILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'src', 'crl', 'interactivesessions', '_version.py')


def import_module(name, path):
    if sys.version_info.major == 2:
        import imp
        return imp.load_source(name, path)

    import importlib
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def get_version():
    return import_module('_version', VERSIONFILE).get_version()


def read(fname):
    with open(os.path.join(os.path.dirname(__file__), fname)) as f:
        return f.read()


setup(
    name='crl.interactivesessions',
    version=get_version(),
    author='Petri Huovinen',
    author_email='petri.huovinen@nokia.com',
    description='Robot Framework test library collection on top of pexpect',
    install_requires=['pexpect>=4.0',
                      'six',
                      'paramiko',
                      'ipaddress',
                      'monotonic'],
    long_description=read('README.rst'),
    license='BSD-3-Clause',
    classifiers=['Intended Audience :: Developers',
                 'License :: OSI Approved :: BSD License',
                 'Programming Language :: Python :: 2',
                 'Programming Language :: Python :: 2.7',
                 'Programming Language :: Python :: 3',
                 'Programming Language :: Python :: 3.6',
                 'Programming Language :: Python :: 3.7',
                 'Topic :: Software Development'],
    keywords='robotframework',
    url='https://github.com/nokia/crl-interactivesessions',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    namespace_packages=['crl'],
    entry_points={'robotdocsconf': [
        'robotdocsconf = crl.interactivesessions.robotdocsconf:robotdocs']}
)
