# -*- coding: utf-8 -*-

# Copyright(C) 2012 Gilles-Alexandre Quenot
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


from datetime import date
from dateutil.relativedelta import relativedelta

from weboob.deprecated.browser import Browser, BrowserIncorrectPassword

from .pages.login import LoginPage
from .pages.accounts_list import GlobalAccountsList, AccountsList, AccountHistoryPage, InvestmentHistoryPage, PeaHistoryPage

__all__ = ['Fortuneo']


class Fortuneo(Browser):
    DOMAIN_LOGIN = 'www.fortuneo.fr'
    DOMAIN = 'www.fortuneo.fr'
    PROTOCOL = 'https'
    CERTHASH = ['4ff0301115f80f18c4e81a136ca28829b46d416d404174945b1ae48abd0634e2']
    ENCODING = None # refer to the HTML encoding
    PAGES = {
            '.*identification\.jsp.*' :                                                         LoginPage,

            '.*prive/default\.jsp.*' :                                                          AccountsList,
            '.*/prive/mes-comptes/synthese-mes-comptes\.jsp' :                                  AccountsList,
            '.*/prive/mes-comptes/synthese-globale/synthese-mes-comptes\.jsp' :                 GlobalAccountsList,

            '.*/prive/mes-comptes/livret/consulter-situation/consulter-solde\.jsp.*' :          AccountHistoryPage,
            '.*/prive/mes-comptes/compte-courant/consulter-situation/consulter-solde\.jsp.*' :  AccountHistoryPage,
            '.*/prive/mes-comptes/compte-titres-.*':                                            InvestmentHistoryPage,
            '.*/prive/mes-comptes/assurance-vie.*':                                             InvestmentHistoryPage,
            '.*/prive/mes-comptes/pea.*':                                                       PeaHistoryPage,
            '.*/prive/mes-comptes/compte-especes.*':                                            InvestmentHistoryPage,
            }

    def __init__(self, *args, **kwargs):
        Browser.__init__(self, *args, **kwargs)

    def home(self):
        """main page (login)"""

        self.login()

    def is_logged(self):
        """Return True if we are logged on website"""

        return self.page is not None and not self.is_on_page(LoginPage)

    def login(self):
        """Login to the website.
        This function is called when is_logged() returns False and the
        password attribute is not None."""

        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        if not self.is_on_page(LoginPage):
            self.location('https://' + self.DOMAIN_LOGIN + '/fr/identification.jsp', no_login=True)

        self.page.login(self.username, self.password)

        if self.is_on_page(LoginPage):
            raise BrowserIncorrectPassword()

        self.location('https://' + self.DOMAIN_LOGIN + '/fr/prive/mes-comptes/synthese-mes-comptes.jsp')

        if self.is_on_page(AccountsList) and self.page.need_reload():
            self.location('/ReloadContext?action=1&')

    def get_investments(self, account):
        self.location(account._link_id)

        return self.page.get_investments()

    def get_history(self, account):
        self.location(account._link_id)

        if self.is_on_page(AccountHistoryPage):
            self.select_form(name='ConsultationHistoriqueOperationsForm')
            self.set_all_readonly(False)
            self['dateRechercheDebut'] = (date.today() - relativedelta(years=1)).strftime('%d/%m/%Y')
            self['nbrEltsParPage'] = '100'
            self.submit()

        return self.page.get_operations(account)

    def get_accounts_list(self):
        """accounts list"""

        if not self.is_on_page(AccountsList):
            self.location('https://' + self.DOMAIN_LOGIN + '/fr/prive/mes-comptes/synthese-mes-comptes.jsp')

        return self.page.get_list()

    def get_account(self, id):
        """Get an account from its ID"""

        assert isinstance(id, basestring)
        l = self.get_accounts_list()

        for a in l:
            if a.id == id:
                return a

        return None

# vim:ts=4:sw=4
