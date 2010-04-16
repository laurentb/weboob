# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Christophe Benz, Romain Bignon

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""

# Low performances
# v
# v
try:
    from .elementtidyparser import ElementTidyParser, ElementTidyParser as StandardParser
except ImportError:
    pass
# v
try:
    from .htmlparser import HTMLParser, HTMLParser as StandardParser
except ImportError:
    pass
# v
try:
    from .html5libparser import Html5libParser, Html5libParser as StandardParser
except ImportError:
    pass
# v
try:
    from .lxmlparser import LxmlHtmlParser, LxmlHtmlParser as StandardParser
except ImportError:
    pass
# v
# v
# High performances
