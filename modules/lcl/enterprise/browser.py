# -*- coding: utf-8 -*-

# Copyright(C) 2010-2013  Romain Bignon, Pierre Mazière, Noé Rubinstein
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

from urllib import urlencode

from weboob.deprecated.browser import Browser, BrowserIncorrectPassword

from .pages import HomePage, MessagesPage, LogoutPage, LogoutOkPage, \
    AlreadyConnectedPage, ExpiredPage, MovementsPage, RootPage


__all__ = ['LCLEnterpriseBrowser']


class LCLEnterpriseBrowser(Browser):
    BASEURL = 'https://entreprises.secure.lcl.fr'
    CERTHASH = ['04e3509c20ac8bdbdb3d0ed37bc34db2dde5ed4bc4c30a3605f63403413099a9',
                '5fcf4a9ceeec25e406a04dffe0c6eacbdf72d11d394cd049701bfbaba3d853d9',
                '774ac6f1c419083541a27d95672a87a5edf5c82d948368008eab2764e65866f9',
                '3db256edfeb7ba255625724b7e62d4dab229557226336ba87b9753006721f16f']
    ENCODING = 'utf-8'
    USER_AGENT = Browser.USER_AGENTS['wget']

    def __init__(self, *args, **kwargs):
        BASEURL = self.BASEURL.rstrip('/')

        self.PROTOCOL, self.DOMAIN = BASEURL.split('://', 2)
        self.PAGES_REV = {
            LogoutPage: BASEURL + '/outil/IQEN/Authentication/logout',
            LogoutOkPage: BASEURL + '/outil/IQEN/Authentication/logoutOk',
            HomePage: BASEURL + '/indexcle.html',
            MessagesPage: BASEURL + '/outil/IQEN/Bureau/mesMessages',
            MovementsPage: BASEURL + '/outil/IQMT/mvt.Synthese/syntheseMouvementPerso',
        }
        self.PAGES = {
            self.PAGES_REV[HomePage]: HomePage,
            self.PAGES_REV[LogoutPage]: LogoutPage,
            self.PAGES_REV[LogoutOkPage]: LogoutOkPage,
            self.PAGES_REV[MessagesPage]: MessagesPage,
            self.PAGES_REV[MovementsPage]: MovementsPage,
            BASEURL + '/outil/IQMT/mvt.Synthese/paginerReleve': MovementsPage,
            BASEURL + '/': RootPage,
            BASEURL + '/outil/IQEN/Authentication/dejaConnecte': AlreadyConnectedPage,
            BASEURL + '/outil/IQEN/Authentication/sessionExpiree': ExpiredPage,
        }

        Browser.__init__(self, *args, **kwargs)
        self._logged = False

    def deinit(self):
        if self._logged:
            self.logout()

    def is_logged(self):
        if self.page:
            ID_XPATH = '//div[@id="headerIdentite"]'
            self._logged = bool(self.page.document.xpath(ID_XPATH))
            return self._logged
        return False

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        if not self.is_on_page(HomePage):
            self.location('/indexcle.html', no_login=True)

        self.page.login(self.username, self.password)

        if self.is_on_page(AlreadyConnectedPage):
            raise BrowserIncorrectPassword("Another session is already open. Please try again later.")
        if not self.is_logged():
            raise BrowserIncorrectPassword(
                "Invalid login/password.\n"
                "If you did not change anything, be sure to check for password renewal request\n"
                "on the original website.\n"
                "Automatic renewal will be implemented later.")

    def logout(self):
        self.location(self.PAGES_REV[LogoutPage], no_login=True)
        self.location(self.PAGES_REV[LogoutOkPage], no_login=True)
        assert self.is_on_page(LogoutOkPage)

    def get_accounts_list(self):
        return [self.get_account()]

    def get_account(self, id=None):
        if not self.is_on_page(MovementsPage):
            self.location(self.PAGES_REV[MovementsPage])

        return self.page.get_account()

    def get_history(self, account):
        if not self.is_on_page(MovementsPage):
            self.location(self.PAGES_REV[MovementsPage])

        for n in range(1, self.page.nb_pages()):
            self.location('/outil/IQMT/mvt.Synthese/paginerReleve',
                          urlencode({'numPage': str(n)}),
                          no_login=True)

            for tr in self.page.get_operations():
                yield tr


class LCLEspaceProBrowser(LCLEnterpriseBrowser):
    BASEURL = 'https://espacepro.secure.lcl.fr'
