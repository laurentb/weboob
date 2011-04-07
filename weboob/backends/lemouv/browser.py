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


__all__ = ['lemouvBrowser']


class lemouvBrowser(BaseBrowser):
    DOMAIN = u'statique.lemouv.fr'
    PAGES  = {r'.*/files/rfPlayer/mouvRSS\.xml': XMLinfos}

    def get_current(self, radio):
        self.location('/files/rfPlayer/mouvRSS.xml')
        assert self.is_on_page(XMLinfos)

        return self.page.get_current()
