# -*- coding: utf-8 -*-

# Copyright(C) 2009-2010  Romain Bignon
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


from weboob.tools.browser import BasePage
from weboob.capabilities.bank import Operation


__all__ = ['AccountHistory']


class AccountHistory(BasePage):
    def on_loaded(self):
        self.operations = []

        for tr in self.document.getiterator('tr'):
            if tr.attrib.get('class', '') == 'hdoc1' or tr.attrib.get('class', '') == 'hdotc1':
                tds = tr.findall('td')
                if len(tds) != 4:
                    continue
                date = u''
                date = tds[0].text
                label = u''
                label += tds[1].text
                label = label.replace(u'\xa0', u'')
                for child in tds[1].getchildren():
                    if child.text: label += child.text
                    if child.tail: label += child.tail
                if tds[1].tail: label += tds[1].tail
                label = label.strip()
                amount = tds[2].text.replace('.', '').replace(',', '.')
                # if we don't have exactly one '.', this is not a floatm try the next
                operation = Operation(len(self.operations))
                if amount.count('.') != 1:
                    amount = tds[3].text.replace('.', '').replace(',', '.')
                    operation.amount = float(amount)
                else:
                    operation.amount = - float(amount)

                operation.date = date
                operation.label = label
                self.operations.append(operation)

    def get_operations(self):
        return self.operations
