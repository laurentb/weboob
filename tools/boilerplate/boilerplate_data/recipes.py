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

import importlib
import sys

from recipe import Recipe


__all__ = ['BaseRecipe', 'CapRecipe', 'ComicRecipe', 'ComicTestRecipe']


class BaseRecipe(Recipe):
    NAME = 'base'

    def generate(self):
        self.write('__init__.py', self.template('init'))
        self.write('module.py', self.template('base_module'))
        self.write('browser.py', self.template('base_browser'))
        self.write('pages.py', self.template('base_pages'))
        self.write('test.py', self.template('base_test'))


class CapRecipe(Recipe):
    NAME = 'cap'

    def __init__(self, args):
        super(CapRecipe, self).__init__(args)
        self.capname = args.capname
        self.login = args.login

    @classmethod
    def configure_subparser(cls, subparsers):
        subparser = super(CapRecipe, cls).configure_subparser(subparsers)
        subparser.add_argument('--login', action='store_true', help='The site requires login')
        subparser.add_argument('capname', help='Capability name')
        return subparser

    def find_module_cap(self):
        if '.' not in self.capname:
            return self.search_cap()

        PREFIX = 'weboob.capabilities.'
        if not self.capname.startswith(PREFIX):
            self.capname = PREFIX + self.capname

        try:
            self.capmodulename, self.capname = self.capname.rsplit('.', 1)
        except ValueError:
            self.error('Cap name must be in format module.CapSomething or CapSomething')

        try:
            module = importlib.import_module(self.capmodulename)
        except ImportError:
            self.error('Module %r not found' % self.capmodulename)
        try:
            cap = getattr(module, self.capname)
        except AttributeError:
            self.error('Module %r has no such capability %r' % (self.capmodulename, self.capname))
        return cap

    def search_cap(self):
        import pkgutil
        import weboob.capabilities

        modules = pkgutil.walk_packages(weboob.capabilities.__path__, prefix='weboob.capabilities.')
        for _, capmodulename, __ in modules:
            module = importlib.import_module(capmodulename)
            if hasattr(module, self.capname):
                self.capmodulename = capmodulename
                return getattr(module, self.capname)

        self.error('Capability %r not found' % self.capname)

    def error(self, message):
        print(message, file=sys.stderr)
        sys.exit(1)

    def methods_code(self, klass):
        import inspect

        methods = []

        for name, member in inspect.getmembers(klass):
            if inspect.ismethod(member) and name in klass.__dict__:
                lines, _ = inspect.getsourcelines(member)
                methods.append(lines)

        return methods

    def generate(self):
        cap = self.find_module_cap()

        self.methods = self.methods_code(cap)

        self.write('__init__.py', self.template('init'))
        self.write('module.py', self.template('cap_module'))
        self.write('browser.py', self.template('base_browser'))
        self.write('pages.py', self.template('base_pages'))
        self.write('test.py', self.template('base_test'))


class ComicRecipe(Recipe):
    NAME = 'comic'

    def generate(self):
        self.write('__init__.py', self.template('init'))
        self.write('module.py', self.template('comic_module'))


class ComicTestRecipe(Recipe):
    NAME = 'comic.test'

    @classmethod
    def configure_subparser(cls, subparsers):
        subparser = super(ComicTestRecipe, cls).configure_subparser(subparsers)
        subparser.add_argument('download_id', help='Download ID')
        return subparser

    def __init__(self, args):
        super(ComicTestRecipe, self).__init__(args)
        self.download_id = args.download_id

    def generate(self):
        self.write('test.py', self.template('comic_test'))
