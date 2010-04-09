#! /usr/bin/env python
# -*- coding: utf-8 -*-

try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

import os

setup(
    name='Weboob',
    version='0.1',
    description='Weboob, web out of the browser',
    author='Romain Bignon',
    author_email='',
    license='GPLv3',
    url='',
    packages=find_packages(exclude=['ez_setup']),
    scripts=[os.path.join('scripts', script) for script in os.listdir('scripts')],
)
