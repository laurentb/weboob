# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Jocelyn Jaubert
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


from decimal import Decimal

from weboob.capabilities.base import NotAvailable
from weboob.browser.pages import HTMLPage
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.browser.filters.standard import CleanText


class BasePage(HTMLPage):
    def on_load(self):
        if self.doc.xpath('//script[contains(text(), "gdpr/recueil")]'):
            self.browser.open('https://particuliers.secure.societegenerale.fr/icd/gdpr/data/gdpr-update-compteur-clicks-client.json')

    def get_error(self):
        try:
            return self.doc.xpath('//span[@class="error_msg"]')[0].text.strip()
        except IndexError:
            return None

    def parse_decimal(self, td):
        value = CleanText('.')(td)
        if value:
            return Decimal(FrenchTransaction.clean_amount(value))
        else:
            return NotAvailable
