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


from weboob.tools.browser import BaseBrowser, BrowserIncorrectPassword

from .pages import HomePage, MessagesPage, LogoutPage, LogoutOkPage, \
                   AlreadyConnectedPage, ExpiredPage, MovementsPage, RootPage


__all__ = ['LCLEnterpriseBrowser']


class LCLEnterpriseBrowser(BaseBrowser):
    PROTOCOL = 'https'
    DOMAIN = 'entreprises.secure.lcl.fr'
    #TODO: CERTHASH = ['ddfafa91c3e4dba2e6730df723ab5559ae55db351307ea1190d09bd025f74cce', '430814d3713cf2556e74749335e9d7ad8bb2a9350a1969ee539d1e9e9492a59a']
    ENCODING = 'utf-8'
    USER_AGENT = BaseBrowser.USER_AGENTS['wget']

    PAGES_REV = {
        LogoutPage: 'https://entreprises.secure.lcl.fr/outil/IQEN/Authentication/logout',
        LogoutOkPage: 'https://entreprises.secure.lcl.fr/outil/IQEN/Authentication/logoutOk',
        HomePage: 'https://entreprises.secure.lcl.fr/indexcle.html',
        MessagesPage: 'https://entreprises.secure.lcl.fr/outil/IQEN/Bureau/mesMessages',
        MovementsPage: 'https://entreprises.secure.lcl.fr/outil/IQMT/mvt.Synthese/syntheseMouvementPerso',
    }
    PAGES = {
        PAGES_REV[HomePage]: HomePage,
        PAGES_REV[LogoutPage]: LogoutPage,
        PAGES_REV[LogoutOkPage]: LogoutOkPage,
        PAGES_REV[MessagesPage]: MessagesPage,
        PAGES_REV[MovementsPage]: MovementsPage,
        'https://entreprises.secure.lcl.fr/': RootPage,
        'https://entreprises.secure.lcl.fr/outil/IQEN/Authentication/dejaConnecte': AlreadyConnectedPage,
        'https://entreprises.secure.lcl.fr/outil/IQEN/Authentication/sessionExpiree': ExpiredPage,
    }

    def __init__(self, *args, **kwargs):
        BaseBrowser.__init__(self, *args, **kwargs)
        self._logged = False

    def deinit(self):
        if self._logged:
            self.logout()

    def is_logged(self):
        ID_XPATH = '//div[@id="headerIdentite"]'
        self._logged = bool(self.page.document.xpath(ID_XPATH))
        return self._logged

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        if not self.is_on_page(HomePage):
            self.location('/indexcle.html', no_login=True)

        self.page.login(self.username, self.password)

        if self.is_on_page(AlreadyConnectedPage):
            raise BrowserIncorrectPassword("Another session is already open. Please try again later.")
        if not self.is_logged():
            raise BrowserIncorrectPassword("invalid login/password.\nIf you did not change anything, be sure to check for password renewal request\non the original web site.\nAutomatic renewal will be implemented later.")

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

        for tr in self.page.get_operations():
            yield tr
