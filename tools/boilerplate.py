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

import argparse
import subprocess
import datetime
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
VERSION = '0.i'

TEMPLATES = TemplateLookup(directories=[TEMPLATE_PATH])


def u8(s):
    return s.decode('utf-8')


def gitconfig(entry):
    return u8(subprocess.check_output('git config -z --get %s' % entry, shell=True)[:-1])


def write(target, contents):
    if not os.path.isdir(os.path.dirname(target)):
        os.makedirs(os.path.dirname(target))
    if os.path.exists(target):
        print >>sys.stderr, "%s already exists." % target
        sys.exit(4)
    with codecs.open(target, mode='w', encoding='utf-8') as f:
        f.write(contents)
    print 'Created %s' % target


class Recipe(object):
    @classmethod
    def configure_subparser(cls, subparsers):
        subparser = subparsers.add_parser(cls.NAME)
        subparser.add_argument('name', help='Backend name')
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
        self.write('backend.py', self.template('base_backend'))
        self.write('browser.py', self.template('base_browser'))
        self.write('pages.py', self.template('base_pages'))
        self.write('test.py', self.template('base_test'))


class ComicRecipe(Recipe):
    NAME = 'comic'

    def generate(self):
        self.write('__init__.py', self.template('init'))
        self.write('backend.py', self.template('comic_backend'))


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

    recipes = [BaseRecipe, ComicRecipe, ComicTestRecipe]
    for recipe in recipes:
        recipe.configure_subparser(subparsers)

    args = parser.parse_args()

    recipe = args.recipe(args)
    recipe.generate()

if __name__ == '__main__':
    main()
