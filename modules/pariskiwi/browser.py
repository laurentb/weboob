# -*- coding: utf-8 -*-

# Copyright(C) 2013      Vincent A
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


from weboob.deprecated.browser import Browser

from .pages import PageList, PageList2, PageEvent


__all__ = ['ParisKiwiBrowser']


class ParisKiwiBrowser(Browser):
    PROTOCOL = 'http'
    DOMAIN = 'pariskiwi.org'
    ENCODING = 'utf-8'

    PAGES = {
        'http://pariskiwi.org/~parislagrise/mediawiki/index.php/Agenda': PageList,
        'http://pariskiwi.org/~parislagrise/mediawiki/index.php/Agenda/Detruire_Ennui_Paris/.+': PageEvent,
        r'http://pariskiwi.org/~parislagrise/mediawiki/api.php\?action=query&list=allpages.*': PageList2,
    }

    def __init__(self, *a, **kw):
        kw['parser'] = 'raw'
        Browser.__init__(self, *a, **kw)

    def list_events_all(self):
        self.location('http://pariskiwi.org/~parislagrise/mediawiki/api.php?action=query&list=allpages&apprefix=Agenda%2FDetruire_Ennui_Paris&aplimit=500&format=json')
        assert self.is_on_page(PageList2)
        return self.page.list_events()

    def get_event(self, _id):
        self.location('http://pariskiwi.org/~parislagrise/mediawiki/index.php/Agenda/Detruire_Ennui_Paris/%s' % _id)
        assert self.is_on_page(PageEvent)
        return self.page.get_event()
