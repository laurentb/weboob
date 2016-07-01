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

from .pages import LoginPage, IndexPage, OperationsPage


__all__ = ['OneyBrowser']


class OneyBrowser(LoginBrowser):
    BASEURL = 'https://www.oney.fr'
    VERIFY = False

    index =      URL(r'/oney/client', IndexPage)
    login =      URL(r'/site/s/login/login.html', LoginPage)
    operations = URL(r'/oney/client', OperationsPage)
    card_page =  URL(r'/oney/client\?task=Synthese&process=SyntheseMultiCompte&indexSelectionne=(?P<acc_num>/d)')

    def do_login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        self.login.go()

        self.page.login(self.username, self.password)

        if not self.index.is_here():
            raise BrowserIncorrectPassword()

    @need_login
    def get_accounts_list(self):
        return self.index.stay_or_go().iter_accounts()

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
