# -*- coding: utf-8 -*-

# Copyright(C) 2012 Lucien Loiseau
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


from weboob.browser import PagesBrowser, URL
from .pages import TranslatePage


__all__ = ['WordReferenceBrowser']


class WordReferenceBrowser(PagesBrowser):
    BASEURL = 'http://www.wordreference.com'
    translation_page = URL('(?P<sl>[a-z]{2})(?P<tl>[a-z]{2})/(?P<pattern>.*)', TranslatePage)

    def translate(self, source, to, text):
        """
        translate 'text' from 'source' language to 'to' language
        """

        return self.translation_page.go(sl=source.encode('utf-8'),
                                        tl=to.encode('utf-8'),
                                        pattern=text.encode('utf-8')).get_translation()
