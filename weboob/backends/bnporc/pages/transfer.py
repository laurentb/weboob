# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

import re

from weboob.tools.browser import BasePage
from weboob.capabilities.bank import TransferError


__all__ = ['TransferPage', 'TransferConfirmPage', 'TransferCompletePage']


class TransferPage(BasePage):
    def transfer(self, from_id, to_id, amount, reason):
        self.browser.select_form(nr=0)
        from_found = False
        to_found = False
        for table in self.document.getiterator('table'):
            if table.attrib.get('cellspacing') == '2':
                for tr in table.cssselect('tr.hdoc1, tr.hdotc1'):
                    tds = tr.findall('td')
                    id = tds[1].text.replace(u'\xa0', u'')
                    if id == from_id:
                        if tds[4].find('input') is None:
                            raise TransferError("Unable to make a transfer from %s" % from_id)
                        self.browser['C1'] = [tds[4].find('input').attrib['value']]
                        from_found = True
                    elif id == to_id:
                        if tds[5].find('input') is None:
                            raise TransferError("Unable to make a transfer to %s" % from_id)
                        self.browser['C2'] = [tds[5].find('input').attrib['value']]
                        to_found = True

        if not from_found:
            raise TransferError('Account %s not found' % from_id)

        if not to_found:
            raise TransferError('Recipient %s not found' % to_id)

        self.browser['T6'] = str(amount).replace('.', ',')
        if reason:
            self.browser['T5'] = reason
        self.browser.submit()

class TransferConfirmPage(BasePage):
    def on_loaded(self):
        for td in self.document.getroot().cssselect('td#size2'):
            raise TransferError(td.text.strip())

        for a in self.document.getiterator('a'):
            m = re.match('/NSFR\?Action=VIRDA&stp=(\d+)', a.attrib['href'])
            if m:
                self.browser.location('/NS_VIRDA?stp=%s' % m.group(1))
                return

class TransferCompletePage(BasePage):
    def get_id(self):
        return self.group_dict['id']
