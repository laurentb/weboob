# -*- coding: utf-8 -*-

# Copyright(C) 2010  Christophe Benz, Romain Bignon
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


import logging


__all__ = ['get_parser', 'NoParserFound']


class NoParserFound(Exception): pass

def load_lxml():
    from .lxmlparser import LxmlHtmlParser
    return LxmlHtmlParser

def load_lxmlsoup():
    from .lxmlsoupparser import LxmlSoupParser
    return LxmlSoupParser

def load_html5lib():
    from .html5libparser import Html5libParser
    return Html5libParser

def load_elementtidy():
    from .elementtidyparser import ElementTidyParser
    return ElementTidyParser

def load_builtin():
    from .htmlparser import HTMLParser
    return HTMLParser

def get_parser(preference_order=('lxml', 'lxmlsoup', 'html5lib', 'elementtidy', 'builtin')):
    """
    Get a parser from a preference order list.
    This allows Weboob to run on systems without lxml, which is the default parser.
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
