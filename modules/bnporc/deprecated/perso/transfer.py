# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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


import re

from weboob.deprecated.browser import Page, BrowserPasswordExpired
from weboob.tools.ordereddict import OrderedDict
from weboob.capabilities.bank import TransferError


class Account(object):
    def __init__(self, id, label, send_checkbox, receive_checkbox):
        self.id = id
        self.label = label
        self.send_checkbox = send_checkbox
        self.receive_checkbox = receive_checkbox


class TransferPage(Page):
    def on_loaded(self):
        for td in self.document.xpath('//td[@class="hdvon1"]'):
            if td.text and 'Vous avez atteint le seuil de' in td.text:
                raise BrowserPasswordExpired(td.text.strip())

    def get_accounts(self):
        accounts = OrderedDict()
        for table in self.document.getiterator('table'):
            if table.attrib.get('cellspacing') == '2':
                for tr in table.cssselect('tr.hdoc1, tr.hdotc1'):
                    tds = tr.findall('td')
                    id = tds[1].text.replace(u'\xa0', u'')
                    label = tds[0].text
                    if label is None and tds[0].find('nobr') is not None:
                        label = tds[0].find('nobr').text
                    send_checkbox =    tds[4].find('input').attrib['value'] if tds[4].find('input') is not None else None
                    receive_checkbox = tds[5].find('input').attrib['value'] if tds[5].find('input') is not None else None
                    account = Account(id, label, send_checkbox, receive_checkbox)
                    accounts[id] = account
        return accounts

    def transfer(self, from_id, to_id, amount, reason):
        accounts = self.get_accounts()

        # Transform RIBs to short IDs
        if len(str(from_id)) == 23:
            from_id = str(from_id)[5:21]
        if len(str(to_id)) == 23:
            to_id = str(to_id)[5:21]

        try:
            sender = accounts[from_id]
        except KeyError:
            raise TransferError('Account %s not found' % from_id)

        try:
            recipient = accounts[to_id]
        except KeyError:
            raise TransferError('Recipient %s not found' % to_id)

        if sender.send_checkbox is None:
            raise TransferError('Unable to make a transfer from %s' % sender.label)
        if recipient.receive_checkbox is None:
            raise TransferError('Unable to make a transfer to %s' % recipient.label)

        self.browser.select_form(nr=0)
        self.browser['C1'] = [sender.send_checkbox]
        self.browser['C2'] = [recipient.receive_checkbox]
        self.browser['T6'] = str(amount).replace('.', ',')
        if reason:
            self.browser['T5'] = reason.encode('utf-8')
        self.browser.submit()


class TransferConfirmPage(Page):
    def on_loaded(self):
        for td in self.document.getroot().cssselect('td#size2'):
            raise TransferError(td.text.strip())

        for a in self.document.getiterator('a'):
            m = re.match('/NSFR\?Action=VIRDA&stp=(\d+)', a.attrib['href'])
            if m:
                self.browser.location('/NS_VIRDA?stp=%s' % m.group(1))
                return


class TransferCompletePage(Page):
    def get_id(self):
        return self.group_dict['id']
