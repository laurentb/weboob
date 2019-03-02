# -*- coding: utf-8 -*-

# Copyright(C) 2014      Oleg Plakhotniuk
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


from weboob.capabilities.bank import CapBank
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword

from .browser import WellsFargo


__all__ = ['WellsFargoModule']


class WellsFargoModule(Module, CapBank):
    NAME = 'wellsfargo'
    MAINTAINER = u'Oleg Plakhotniuk'
    EMAIL = 'olegus8@gmail.com'
    VERSION = '1.6'
    LICENSE = 'LGPLv3+'
    DESCRIPTION = u'Wells Fargo'
    CONFIG = BackendConfig(
        ValueBackendPassword('login',      label='Username', masked=False),
        ValueBackendPassword('password',   label='Password'),
        ValueBackendPassword('question1',  label='Question 1', masked=False),
        ValueBackendPassword('answer1',    label='Answer 1', masked=False),
        ValueBackendPassword('question2',  label='Question 2', masked=False),
        ValueBackendPassword('answer2',    label='Answer 2', masked=False),
        ValueBackendPassword('question3',  label='Question 3', masked=False),
        ValueBackendPassword('answer3',    label='Answer 3', masked=False),
        ValueBackendPassword('phone_last4', label='Last 4 digits of phone number to request access code to', masked=False),
        ValueBackendPassword('code_file', label='File to read access code from', masked=False))
    BROWSER = WellsFargo

    def create_default_browser(self):
        return self.create_browser(
            username = self.config['login'].get(),
            password = self.config['password'].get(),
            question1 = self.config['question1'].get(),
            answer1 = self.config['answer1'].get(),
            question2 = self.config['question2'].get(),
            answer2 = self.config['answer2'].get(),
            question3 = self.config['question3'].get(),
            answer3 = self.config['answer3'].get(),
            phone_last4 = self.config['phone_last4'].get(),
            code_file = self.config['code_file'].get())

    def iter_accounts(self):
        return self.browser.iter_accounts()

    def get_account(self, id_):
        return self.browser.get_account(id_)

    def iter_history(self, account):
        return self.browser.iter_history(account)
