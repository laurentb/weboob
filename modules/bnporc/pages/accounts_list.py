# -*- coding: utf-8 -*-

# Copyright(C) 2009-2011  Romain Bignon
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


from weboob.capabilities.bank import Account
from weboob.capabilities.base import NotAvailable
from weboob.tools.browser import BasePage

from ..errors import PasswordExpired


__all__ = ['AccountsList']


class AccountsList(BasePage):
    def on_loaded(self):
        pass

    def get_list(self):
        l = []
        for tr in self.document.getiterator('tr'):
            if not 'class' in tr.attrib and tr.find('td') is not None and tr.find('td').attrib.get('class', '') == 'typeTitulaire':
                account = Account()
                account.id = tr.xpath('.//td[@class="libelleCompte"]/input')[0].attrib['id'][len('libelleCompte'):]
                account.link_id = account.id
                if len(str(account.id)) == 23:
                    account.id = str(account.id)[5:21]

                account.label = tr.xpath('.//td[@class="libelleCompte"]/a')[0].text.strip()

                tds = tr.findall('td')
                account.balance = float(tds[3].find('a').text.replace('.','').replace(',','.').strip(u' \t\u20ac\xa0€\n\r'))
                if tds[4].find('a') is not None:
                    account.coming = float(tds[4].find('a').text.replace('.','').replace(',','.').strip(u' \t\u20ac\xa0€\n\r'))
                else:
                    account.coming = NotAvailable
                l.append(account)

        if len(l) == 0:
            # oops, no accounts? check if we have not exhausted the allowed use
            # of this password
            for img in self.document.getroot().cssselect('img[align="middle"]'):
                if img.attrib.get('alt', '') == 'Changez votre code secret':
                    raise PasswordExpired('Your password has expired')
        return l

    def get_execution_id(self):
        return self.document.xpath('//input[@name="execution"]')[0].attrib['value']
