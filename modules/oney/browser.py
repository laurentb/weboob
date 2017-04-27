# -*- coding: utf-8 -*-

# Copyright(C) 2014 Budget Insight
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


from weboob.exceptions import BrowserIncorrectPassword
from weboob.browser import LoginBrowser, URL, need_login

from .pages import LoginPage, ClientPage, OperationsPage, ChoicePage


__all__ = ['OneyBrowser']


class OneyBrowser(LoginBrowser):
    BASEURL = 'https://www.oney.fr'

    choice =      URL(r'/site/s/multimarque/choixsite.html', ChoicePage)
    client =      URL(r'/oney/client', ClientPage)
    login =       URL(r'/site/s/login/login.html', LoginPage)
    operations =  URL(r'/oney/client', OperationsPage)
    card_page =   URL(r'/oney/client\?task=Synthese&process=SyntheseMultiCompte&indexSelectionne=(?P<acc_num>/d)')

    multi_site = False

    def do_login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        self.login.go()

        self.page.login(self.username, self.password)

        if not (self.client.is_here() or self.choice.is_here()):
            raise BrowserIncorrectPassword()
        if self.choice.is_here():
            self.multi_site = True

    @need_login
    def get_accounts_list(self):
        if self.multi_site:
            # other site is ignored for now
            accounts = self.open('/site/s/login/loginidentifiant.html',
                                    data={'selectedSite': 'ONEY_HISTO'}).page.iter_accounts()
        else:
            accounts = self.client.stay_or_go().iter_accounts()
        return accounts

    @need_login
    def iter_history(self, account):
        if account._num:
            self.card_page.go(acc_num=account._num)
        post = {'task': 'Synthese', 'process': 'SyntheseCompte', 'taskid': 'Releve'}
        self.operations.go(data=post)

        return self.page.iter_transactions(seen=set())

    @need_login
    def iter_coming(self, account):
        if account._num:
            self.card_page.go(acc_num=account._num)
        post = {'task': 'OperationRecente', 'process': 'OperationRecente', 'taskid': 'OperationRecente'}
        self.operations.go(data=post)

        return self.page.iter_transactions(seen=set())
