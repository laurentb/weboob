#!/usr/bin/env python3

# Copyright(C) 2017  Vincent A
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

import ast
import fnmatch
import os
import traceback

import lxml.etree
from weboob.browser.filters import standard


class Error(SyntaxError):
    def __init__(self, file, line, message):
        super(Error, self).__init__('%s:%s: %s' % (file, line, message))
        self.file = file
        self.line = line


def do_visits(*funcs):
    def wrapper(self, node):
        for func in funcs:
            func(self, node)
        self.generic_visit(node)
    return wrapper


class Visitor(ast.NodeVisitor):
    def __init__(self, file, *args, **kwargs):
        self.warnings = kwargs.pop('warnings', False)
        super(Visitor, self).__init__(*args, **kwargs)
        self.file = file

        self.filters = []
        self.filters.extend(f for f in dir(standard) if isinstance(getattr(standard, f), type) and issubclass(getattr(standard, f), standard.CleanText))
        self.filters.extend(['Regexp', 'XPath', 'Attr', 'Link'])

        self.element_context = []

    def check_xpath(self, s, lineno):
        try:
            lxml.etree.XPath(s)
        except lxml.etree.XPathSyntaxError as exc:
            raise Error(self.file, lineno, exc)

        if self.warnings:
            if not s.lstrip('(').startswith('.') and len(self.element_context) >= 2:
                if self.element_context[-1] == 'ItemElement' and self.element_context[-2] in ('TableElement', 'ListElement'):
                    print('%s:%s: probable missing "." at start of XPath' % (self.file, lineno))

    def _item_xpath(self, node):
        try:
            target, = node.targets
        except ValueError:
            return
        if not isinstance(target, ast.Name) or target.id != 'item_xpath':
            return
        try:
            if self.element_context[-1] not in ('TableElement', 'ListElement'):
                return
        except IndexError:
            return
        if not isinstance(node.value, ast.Str):
            return

        self.check_xpath(node.value.s, node.lineno)

    visit_Assign = do_visits(_item_xpath)

    def _xpath_call(self, node):
        if not isinstance(node.func, ast.Attribute):
            return
        if node.func.attr != 'xpath':
            return
        try:
            if not isinstance(node.args[0], ast.Str):
                return
        except IndexError:
            return

        self.check_xpath(node.args[0].s, node.lineno)

    def _filter_call(self, node):
        if not isinstance(node.func, ast.Name):
            return
        if node.func.id not in self.filters:
            return
        try:
            if not isinstance(node.args[0], ast.Str):
                return
        except IndexError:
            return

        self.check_xpath(node.args[0].s, node.lineno)

    visit_Call = do_visits(_xpath_call, _filter_call)

    def visit_ClassDef(self, node):
        has_element = False

        for basenode in node.bases:
            if isinstance(basenode, ast.Name) and basenode.id in ('ListElement', 'ItemElement', 'TableElement'):
                self.element_context.append(basenode.id)
                has_element = True
                break

        self.generic_visit(node)

        if has_element:
            self.element_context.pop()


def search_py(root):
    for path, dirs, files in os.walk(root):
        dirs.sort()
        for f in fnmatch.filter(files, '*.py'):
            yield os.path.join(path, f)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Check XPath definitions")
    parser.add_argument('-w', '--warnings', action='store_true')
    args = parser.parse_args()

    modpath = os.getenv('WEBOOB_MODULES', os.path.normpath(os.path.dirname(__file__) + '/../modules'))
    for fn in search_py(modpath):
        with open(fn) as fd:
            try:
                node = ast.parse(fd.read(), fn)
            except SyntaxError as exc:
                print('In file', fn)
                traceback.print_exc(exc)
        try:
            Visitor(fn, warnings=args.warnings).visit(node)
        except SyntaxError as exc:
            print(exc)
