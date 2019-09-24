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

import codecs
import datetime
import os
import sys

from mako.lookup import TemplateLookup

from weboob import __version__

WEBOOB_MODULES = os.getenv(
    'WEBOOB_MODULES',
    os.path.realpath(os.path.join(os.path.dirname(__file__), '../../modules')))
BOILERPLATE_PATH = os.getenv(
    'BOILERPLATE_PATH',
    os.path.realpath(os.path.join(os.path.dirname(__file__), 'boilerplate_data')))

TEMPLATES = TemplateLookup(directories=[BOILERPLATE_PATH], input_encoding='utf-8')


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
        subparser.set_defaults(recipe_class=cls)
        return subparser

    def __init__(self, args):
        self.name = args.name.lower().replace(' ', '')
        self.classname = args.name.title().replace(' ', '')
        self.year = datetime.date.today().year
        self.author = args.author
        self.email = args.email
        self.version = __version__
        self.login = False

    def write(self, filename, contents):
        return write(os.path.join(WEBOOB_MODULES, self.name, filename), contents)

    def template(self, name, **kwargs):
        if '.' not in name:
            name += '.pyt'
        return TEMPLATES.get_template(name) \
            .render(r=self,
                    # workaround, as it's also a mako directive
                    coding='# -*- coding: utf-8 -*-',
                    login=self.login,
                    **kwargs).strip() + u'\n'

    def generate(self):
        raise NotImplementedError()
