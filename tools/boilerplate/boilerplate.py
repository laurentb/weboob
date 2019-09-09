#! /usr/bin/env python3
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
import os
import subprocess
import sys
from importlib import import_module

BOILERPLATE_PATH = os.getenv(
    'BOILERPLATE_PATH',
    os.path.realpath(os.path.join(os.path.dirname(__file__), 'boilerplate_data')))

sys.path.append(os.path.dirname(__file__))
sys.path.append(BOILERPLATE_PATH)

from recipe import Recipe  # NOQA


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
    subparsers = parser.add_subparsers(dest='recipe')
    subparsers.required = True

    recipes_module = import_module('recipes', package='boilerplate_data')

    if hasattr(recipes_module, '__all__'):
        for k in recipes_module.__all__:
            getattr(recipes_module, k).configure_subparser(subparsers)
    else:
        for k in dir(recipes_module):
            print(k)
            if issubclass(getattr(recipes_module, k), Recipe) and not k.startswith('_'):
                getattr(recipes_module, k).configure_subparser(subparsers)

    args = parser.parse_args()

    recipe = args.recipe_class(args)
    recipe.generate()


if __name__ == '__main__':
    main()
