# -*- coding: utf-8 -*-

# Copyright(C) 2010-2014 Romain Bignon
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

import warnings

__all__ = ['html2text']


try:
    from html2text import HTML2Text

    def html2text(html):
        h = HTML2Text()
        h.unicode_snob = True
        h.skip_internal_links = True
        h.inline_links = False
        h.links_each_paragraph = True
        return unicode(h.handle(html))

except ImportError:
    # Older versions of html2text do not have a class, so we have
    # to configure the module globally.
    try:
        import html2text as h2t
        h2t.UNICODE_SNOB = 1
        h2t.SKIP_INTERNAL_LINKS = True
        h2t.INLINE_LINKS = False
        h2t.LINKS_EACH_PARAGRAPH = True
        html2text = h2t.html2text
    except ImportError:
        def html2text(html):
            warnings.warn('python-html2text is not present. HTML pages are not converted into text.', stacklevel=2)
            return html
