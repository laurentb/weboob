# -*- coding: utf-8 -*-

# Copyright(C) 2010  Nicolas Duhamel
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


from weboob.capabilities.bank import TransferError
from weboob.tools.browser import BasePage

import re

__all__ = ['TransferChooseAccounts', 'CompleteTransfer', 'TransferConfirm', 'TransferSummary']


class TransferChooseAccounts(BasePage):

    def set_accouts(self, from_account, to_account):
        self.browser.select_form(name="AiguillageForm")
        self.browser["idxCompteEmetteur"] = [from_account.id]
        self.browser["idxCompteReceveur"] = [to_account.id]
        self.browser.submit()


class CompleteTransfer(BasePage):

    def complete_transfer(self, amount):
        self.browser.select_form(name="VirementNationalForm")
        self.browser["montant"] = str(amount)
        self.browser.submit()

class TransferConfirm(BasePage):

    def confirm(self):
        self.browser.location("https://voscomptesenligne.labanquepostale.fr/voscomptes/canalXHTML/virementsafran/virementnational/4-virementNational.ea")

class TransferSummary(BasePage):

    def get_transfer_id(self):
        pattern = "Votre virement N.+ ([0-9]+) "
        regex = re.compile(pattern)
        #HACK for deal with bad encoding ...
        try:
            text = self.document.xpath("//form/div/p")[0].text
        except UnicodeDecodeError, error:
            text = error.object
        match = regex.search(text)
        if not match:
            self.browser.logger.error('Unable to parse the text result: %r' % text)
            raise TransferError('Unable to process transfer: %r' % text)

        id_transfer = match.groups()[0]
        return id_transfer

