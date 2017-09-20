#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright(C) 2013      Laurent Bachelier
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function

import argparse
import subprocess
import datetime
import importlib
import os
import sys
import codecs
from mako.lookup import TemplateLookup

MODULE_PATH = os.getenv(
    'MODULE_PATH',
    os.path.realpath(os.path.join(os.path.dirname(__file__), '../modules')))
TEMPLATE_PATH = os.getenv(
    'TEMPLATE_PATH',
    os.path.realpath(os.path.join(os.path.dirname(__file__), 'boilerplate_data')))
VERSION = '1.4'

TEMPLATES = TemplateLookup(directories=[TEMPLATE_PATH])


def u8(s):
    if isinstance(s, bytes):
        return s.decode('utf-8')
    return s


def gitconfig(entry):
    return u8(subprocess.check_output('git config -z --get %s' % entry, shell=True)[:-1])


def write(target, contents):
    if not os.path.isdir(os.path.dirname(target)):
        os.makedirs(os.path.dirname(target))
    if os.path.exists(target):
        print("%s already exists." % target, file=sys.stderr)
        sys.exit(4)
    with codecs.open(target, mode='w', encoding='utf-8') as f:
        f.write(contents)
    print('Created %s' % target)


class Recipe(object):
    @classmethod
    def configure_subparser(cls, subparsers):
        subparser = subparsers.add_parser(cls.NAME)
        subparser.add_argument('name', help='Module name')
        subparser.set_defaults(recipe=cls)
        return subparser

    def __init__(self, args):
        self.name = args.name.lower().replace(' ', '')
        self.classname = args.name.title().replace(' ', '')
        self.year = datetime.date.today().year
        self.author = args.author
        self.email = args.email
        self.version = VERSION

    def write(self, filename, contents):
        return write(os.path.join(MODULE_PATH, self.name, filename), contents)

    def template(self, name, **kwargs):
        if '.' not in name:
            name += '.py'
        return TEMPLATES.get_template(name) \
            .render(r=self,
                    # workaround, as it's also a mako directive
                    coding='# -*- coding: utf-8 -*-',
                    **kwargs)

    def generate(self):
        raise NotImplementedError()


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

    LINES = {'def'    :  '    def %s%s:',
             'docbound': '        """',
             'docline':  '        %s',
             'body'   :  '        raise NotImplementedError()'
             }

    def __init__(self, args):
        super(CapRecipe, self).__init__(args)
        self.capname = args.capname

    @classmethod
    def configure_subparser(cls, subparsers):
        subparser = super(CapRecipe, cls).configure_subparser(subparsers)
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
        import re

        codes = []

        for name, member in inspect.getmembers(klass):
            if inspect.ismethod(member):
                argspec = inspect.getargspec(member)
                args = inspect.formatargspec(*argspec)

                code = []
                code.append(self.LINES['def'] % (name, args))
                doc = inspect.getdoc(member)
                if doc:
                    code.append(self.LINES['docbound'])
                    for line in doc.split('\n'):
                        if line:
                            line = re.sub('"""', '\\"\\"\\"', line)
                            code.append(self.LINES['docline'] % line)
                        else:
                            code.append('')
                    code.append(self.LINES['docbound'])
                code.append(self.LINES['body'])
                codes.append('\n'.join(code))

        return '\n\n'.join(codes)

    def generate(self):
        cap = self.find_module_cap()

        self.methods_code = self.methods_code(cap)

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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-a', '--author',
        default=gitconfig('user.name'), type=u8)
    parser.add_argument(
        '-e', '--email',
        default=gitconfig('user.email'), type=u8)
    subparsers = parser.add_subparsers()

    recipes = [BaseRecipe, ComicRecipe, ComicTestRecipe, CapRecipe]
    for recipe in recipes:
        recipe.configure_subparser(subparsers)

    args = parser.parse_args()

    recipe = args.recipe(args)
    recipe.generate()

if __name__ == '__main__':
    main()
