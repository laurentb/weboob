# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012  Jeremy Monnet
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


from weboob.deprecated.browser import Browser, BrowserIncorrectPassword

from .pages import LoginPage, HomePage, RentedPage, HistoryPage, BookedPage


__all__ = ['AloesBrowser']


# Browser
class AloesBrowser(Browser):
    PROTOCOL = 'http'
    ENCODING = 'utf-8'
    USER_AGENT = Browser.USER_AGENTS['desktop_firefox']
    #DEBUG_HTTP = True
    DEBUG_HTTP = False
    PAGES = {
        'http://.*/index.aspx': LoginPage,
        'http://.*/index.aspx\?IdPage=1': HomePage,
        'http://.*/index.aspx\?IdPage=45': RentedPage,
        'http://.*/index.aspx\?IdPage=429': HistoryPage,
        'http://.*/index.aspx\?IdPage=44': BookedPage
        }

    def __init__(self, baseurl, *args, **kwargs):
        self.BASEURL = baseurl
        Browser.__init__(self, *args, **kwargs)

    def is_logged(self):

        return self.page \
                 and not self.page.document.getroot().xpath('//input[contains(@id, "ctl00_ContentPlaceHolder1_ctl00_ctl08_ctl00_TextSaisie")]')
        #return True

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        if not self.is_on_page(HomePage):
            self.location('%s://%s/index.aspx'
                          % (self.PROTOCOL, self.BASEURL),
                          no_login=True)
        if not self.page.login(self.username, self.password) or \
            not self.is_logged() or \
                (self.is_on_page(LoginPage) and self.page.is_error()):
            raise BrowserIncorrectPassword()

    def get_rented_books_list(self):
        if not self.is_on_page(RentedPage):
            self.location('%s://%s/index.aspx?IdPage=45'
                      % (self.PROTOCOL, self.BASEURL)
                      )
        return self.page.get_list()

    def get_booked_books_list(self):
        if not self.is_on_page(BookedPage):
            self.location('%s://%s/index.aspx?IdPage=44'
                          % (self.PROTOCOL, self.BASEURL))
        return self.page.get_list()
