#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright(C) 2013-2019      Laurent Bachelier, Sébastien Jean
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function

import argparse
import inspect
import subprocess
import os
import sys


from importlib import import_module

BOILERPLATE_PATH = os.getenv(
    'BOILERPLATE_PATH',
    os.path.realpath(os.path.join(os.path.dirname(__file__), 'boilerplate_data')))

sys.path.append(os.path.dirname(__file__))
sys.path.append(BOILERPLATE_PATH)


def u8(s):
    if isinstance(s, bytes):
        return s.decode('utf-8')
    return s


def gitconfig(entry):
    return u8(subprocess.check_output('git config -z --get %s' % entry, shell=True)[:-1])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-a', '--author',
        default=gitconfig('user.name'), type=u8)
    parser.add_argument(
        '-e', '--email',
        default=gitconfig('user.email'), type=u8)
    subparsers = parser.add_subparsers()

    recipes_module = import_module('recipes', package='boilerplate_data')

    for k, v in recipes_module.__dict__.items():
        if inspect.isclass(v) and not k.startswith('_'):
            v.configure_subparser(subparsers)

    args = parser.parse_args()

    recipe = args.recipe(args)
    recipe.generate()


if __name__ == '__main__':
    main()
