# -*- coding: utf-8 -*-

# Copyright(C) 2010-2014 Romain Bignon
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

from weboob.tools.compat import unicode

__all__ = ['html2text']


from html2text import HTML2Text


def html2text(html, **options):
    h = HTML2Text()
    defaults = dict(
        unicode_snob=True,
        skip_internal_links=True,
        inline_links=False,
        links_each_paragraph=True,
    )
    defaults.update(options)
    for k, v in defaults.items():
        setattr(h, k, v)
    return unicode(h.handle(html))
