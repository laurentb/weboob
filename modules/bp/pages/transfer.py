# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Nicolas Duhamel
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

from weboob.capabilities.bank import TransferError
from weboob.deprecated.browser import Page
from weboob.tools.misc import to_unicode


class TransferChooseAccounts(Page):
    def set_accouts(self, from_account, to_account):
        self.browser.select_form(name="AiguillageForm")
        self.browser["idxCompteEmetteur"] = [from_account.id]
        self.browser["idxCompteReceveur"] = [to_account.id]
        self.browser.submit()


class CompleteTransfer(Page):
    def complete_transfer(self, amount):
        self.browser.select_form(name="virement_unitaire_saisie_saisie_virement_sepa")
        self.browser["montant"] = str(amount)
        self.browser.submit()


class TransferConfirm(Page):
    def confirm(self):
        self.browser.location('https://voscomptesenligne.labanquepostale.fr/voscomptes/canalXHTML/virement/virementSafran_national/confirmerVirementNational-virementNational.ea')


class TransferSummary(Page):
    def get_transfer_id(self):
        p = self.document.xpath("//div[@id='main']/div/p")[0]

        #HACK for deal with bad encoding ...
        try:
            text = p.text
        except UnicodeDecodeError as error:
            text = error.object.strip()

        match = re.search("Votre virement N.+ ([0-9]+) ", text)
        if match:
            id_transfer = match.groups()[0]
            return id_transfer

        if text.startswith(u"Votre virement n'a pas pu"):
            if p.find('br') is not None:
                errmsg = to_unicode(p.find('br').tail).strip()
                raise TransferError('Unable to process transfer: %s' % errmsg)
            else:
                self.browser.logger.warning('Unable to find the error reason')

        self.browser.logger.error('Unable to parse the text result: %r' % text)
        raise TransferError('Unable to process transfer: %r' % text)
