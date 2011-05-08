# * -*- coding: utf-8 -*-

# Copyright(C) 2011  Johann Broudin
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


from weboob.tools.browser import BaseBrowser

from .pages import XMLinfos


__all__ = ['FranceInterBrowser']


class FranceInterBrowser(BaseBrowser):
    DOMAIN = u'metadatas.tv-radio.com'
    ENCODING = 'iso-8859-1'
    PAGES  = {r'.*metadatas/franceinterRSS\.xml': XMLinfos}

    def get_current(self, radio):
        self.location('/metadatas/franceinterRSS.xml')
        assert self.is_on_page(XMLinfos)

        return self.page.get_current()
