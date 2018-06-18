# -*- coding: utf-8 -*-

# Copyright(C) 2018 Arthur Huillet
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

from __future__ import unicode_literals


from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword

from .pages import LoginPage, AccountsList, InvestmentList, AccountHistory

__all__ = ['Suravenir']


class Suravenir(LoginBrowser):
    BASEURL = 'https://www.previ-direct.com/'
    broker_to_instance = { 'assurancevie.com' : 'Q4n1',
                           'linxea'           : 'S9o6',
                           'mes-placements.fr': '5yKs',
                           'epargnissimo'     : 'FtA1'}

    login_page = URL('/web/eclient-(?P<broker>.*)', LoginPage)
    accounts_page = URL('/group/eclient-(?P<broker>.*)/home$', AccountsList)
    summary_page = URL('/group/eclient.*tabulateur.tabulation.resume', None)
    investments_page = URL('/group/eclient.*tabulateur.tabulation.supports', InvestmentList)
    history_page = URL('/group/eclient.*tabulateur.tabulation.operations', AccountHistory)

#        detail_link does not contain the type of page. the suffix for the pages are:
#        résumé
#        _portletespaceClientmonCompte_WAR_portletespaceclient_INSTANCE_Q4n1_tabName=detailsContrat.tabulateur.tabulation.resume
#        mes supports
#        _portletespaceClientmonCompte_WAR_portletespaceclient_INSTANCE_Q4n1_tabName=detailsContrat.tabulateur.tabulation.supports
#        mes opérations
#        _portletespaceClientmonCompte_WAR_portletespaceclient_INSTANCE_Q4n1_tabName=detailsContrat.tabulateur.tabulation.operations

    def __init__(self, broker, *args, **kwargs):
        self.broker = broker
        LoginBrowser.__init__(self, *args, **kwargs)

    def do_login(self):
        self.login_page.stay_or_go(broker=self.broker).login(self.username, self.password)

        if self.login_page.is_here():
            raise BrowserIncorrectPassword()

    @need_login
    def get_accounts_list(self):
        self.accounts_page.stay_or_go(broker=self.broker)
        return self.page.get_contracts()

    def get_URI_for_account(self, account):
         return '%s&_portletespaceClientmonCompte_WAR_portletespaceclient_INSTANCE_%s_tabName=detailsContrat.tabulateur.tabulation' % (account._detail_link, self.broker_to_instance[self.broker])

    @need_login
    def iter_investments(self, account):
        self.location(self.get_URI_for_account(account) + '.supports')
        return self.page.iter_investments()

    @need_login
    def iter_history(self, account):
        self.location(self.get_URI_for_account(account) + '.operations')
        return self.page.iter_history()
