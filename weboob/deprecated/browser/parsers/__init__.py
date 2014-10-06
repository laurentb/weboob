# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Christophe Benz, Romain Bignon
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


import logging


__all__ = ['get_parser', 'NoParserFound']


class NoParserFound(Exception):
    pass


def load_lxml():
    from .lxmlparser import LxmlHtmlParser
    return LxmlHtmlParser


def load_lxmlsoup():
    from .lxmlsoupparser import LxmlSoupParser
    return LxmlSoupParser


def load_xml():
    from .lxmlparser import LxmlXmlParser
    return LxmlXmlParser


def load_json():
    # This parser doesn't read HTML, don't include it in the
    # preference_order default value below.
    from .jsonparser import JsonParser
    return JsonParser


def load_csv():
    # This parser doesn't read HTML, don't include it in the
    # preference_order default value below.
    from .csvparser import CsvParser
    return CsvParser


def load_raw():
    # This parser doesn't read HTML, don't include it in the
    # preference_order default value below.
    from .iparser import RawParser
    return RawParser


def get_parser(preference_order=('lxml', 'lxmlsoup')):
    """
    Get a parser from a preference order list.
    Return a parser implementing IParser.
    """
    if not isinstance(preference_order, (tuple, list)):
        preference_order = [preference_order]

    for kind in preference_order:
        if not 'load_%s' % kind in globals():
            continue

        try:
            return globals()['load_%s' % kind]()
        except ImportError:
            logging.debug('%s is not installed.' % kind)

    raise NoParserFound("No parser found (%s)" % ','.join(preference_order))
