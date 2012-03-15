# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Florent Fourcot
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


from weboob.tools.browser import BaseBrowser, BrowserIncorrectPassword

from .pages import LoginPage, HomePage, HistoryPage, RentedPage


__all__ = ['ChampslibresBrowser']


# Browser
class ChampslibresBrowser(BaseBrowser):
    PROTOCOL = 'http'
    ENCODING = None
    PAGES = {
        '.*login.*': LoginPage,
        '.*home\?lang=frf.*': HomePage,
        'http://.*/index.aspx\?IdPage=429': HistoryPage,
        '.*patroninfo.*': RentedPage,
        }

    def __init__(self, *args, **kwargs):
        BaseBrowser.__init__(self, *args, **kwargs)

    def is_logged(self):

        return self.page \
                 and not self.page.document.getroot().xpath('//input[contains(@id, "pin")]')

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        if not self.is_on_page(HomePage):
            self.location('https://sbib.si.leschampslibres.fr/iii/cas/login?null', no_login=True)
        self.page.login(self.username, self.password)
        if not self.is_logged():
            raise BrowserIncorrectPassword()
        # Get home and get ID
        self.location('http://opac.si.leschampslibres.fr/iii/encore/home?lang=frf')
        self.id = self.page.get_id()
        self.logger.debug('Get ID ' + self.id)

    def get_rented_books_list(self):
        if not self.is_on_page(RentedPage):
            self.location('https://sbib.si.leschampslibres.fr/patroninfo~S1*frf/1123477/items')
        return self.page.get_list()

    # TODO
    def get_booked_books_list(self):
        return []
