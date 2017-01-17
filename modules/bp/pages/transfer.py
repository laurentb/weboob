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


from datetime import datetime

from weboob.capabilities.bank import TransferError, Recipient, NotAvailable, Transfer, TransferStep, AccountNotFound
from weboob.capabilities.base import find_object
from weboob.browser.pages import LoggedPage
from weboob.browser.filters.standard import CleanText, Env, Regexp, Date, CleanDecimal
from weboob.browser.filters.html import Attr
from weboob.browser.elements import ListElement, ItemElement, method, SkipItem
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.capabilities.bank.iban import is_iban_valid
from weboob.tools.value import Value

from .base import MyHTMLPage

class CheckTransferError(MyHTMLPage):
    def on_load(self):
        MyHTMLPage.on_load(self)
        error = CleanText(u'//span[@class="app_erreur"] | //p[@class="warning"] | //p[contains(text(), "Votre virement n\'a pas pu être enregistré")]')(self.doc)
        if error:
            raise TransferError(error)

class TransferChooseAccounts(LoggedPage, MyHTMLPage):
    def is_inner(self, text):
        for option in self.doc.xpath('//select[@id="donneesSaisie.idxCompteEmetteur"]/option'):
            if text == CleanText('.')(option):
                return True
        return False

    @method
    class iter_recipients(ListElement):
        def condition(self):
            return any(self.env['account_id'] in CleanText('.')(option) for option in self.page.doc.xpath('//select[@id="donneesSaisie.idxCompteEmetteur"]/option'))

        # You're not dreaming, this is real life
        item_xpath = '//select[@id="caca"]/option'

        class Item(ItemElement):
            klass = Recipient

            def condition(self):
                return self.el.attrib['value'] != '-1'

            def validate(self, obj):
                # Some international external recipients show those infos:
                # INT - CA - 0815304220511006                   - CEGEP CANADA
                # Skipping those for the moment.
                return not obj.iban or is_iban_valid(obj.iban)

            obj_category = Env('category')
            obj_label = Env('label')
            obj_id = Env('id')
            obj_currency = u'EUR'
            obj_iban = Env('iban')
            obj_bank_name = Env('bank_name')
            obj__value = Attr('.', 'value')

            def obj_enabled_at(self):
                return datetime.now().replace(microsecond=0)

            def parse(self, el):
                if any(s in CleanText('.')(el) for s in ['Avoir disponible', 'Solde']) or self.page.is_inner(CleanText('.')(el)):
                    self.env['category'] = u'Interne'
                else:
                    self.env['category'] = u'Externe'
                if self.env['category'] == u'Interne':
                    _id = Regexp(CleanText('.'), '- (.*?) -')(el)
                    if _id == self.env['account_id']:
                        raise SkipItem()
                    try:
                        account = find_object(self.page.browser.get_accounts_list(), id=_id, error=AccountNotFound)
                        self.env['id'] = _id
                        self.env['label'] = account.label
                        self.env['iban'] = account.iban
                    except AccountNotFound:
                        self.env['id'] = Regexp(CleanText('.'), '- (.*?) -')(el).replace(' ', '')
                        self.env['iban'] = NotAvailable
                        label = CleanText('.')(el).split('-')
                        holder = label[-1] if not any(string in label[-1] for string in ['Avoir disponible', 'Solde']) else label[-2]
                        self.env['label'] = '%s %s' % (label[0].strip(), holder.strip())
                    self.env['bank_name'] = u'La Banque Postale'

                else:
                    self.env['id'] = self.env['iban'] = Regexp(CleanText('.'), '- (.*?) -')(el).replace(' ', '')
                    self.env['label'] = CleanText('.')(el).split('-')[-1].strip()
                    first_part = CleanText('.')(el).split('-')[0].strip()
                    self.env['bank_name'] = u'La Banque Postale' if first_part in ['CCP', 'PEL'] else NotAvailable

    def init_transfer(self, account_id, recipient_value):
        matched_values = [Attr('.', 'value')(option) for option in self.doc.xpath('//select[@id="donneesSaisie.idxCompteEmetteur"]/option') \
                          if account_id in CleanText('.')(option)]
        assert len(matched_values) == 1
        form = self.get_form(xpath='//form[@class="formvirement"]')
        form['donneesSaisie.idxCompteReceveur'] = recipient_value
        form['donneesSaisie.idxCompteEmetteur'] = matched_values[0]
        form.submit()


class CompleteTransfer(LoggedPage, CheckTransferError):
    def complete_transfer(self, amount, label):
        form = self.get_form(xpath='//form[@method]')
        form['montant'] = amount
        if 'commentaire' in form and label:
            form['commentaire'] = label
        form.submit()


class TransferConfirm(LoggedPage, CheckTransferError):
    def is_here(self):
        return not CleanText('//p[contains(text(), "Vous pouvez le consulter dans le menu")]')(self.doc)

    def double_auth(self, transfer):
        code_needed = CleanText('//label[@for="code_securite"]')(self.doc)
        if code_needed:
            raise TransferStep(transfer, Value('code', label= code_needed))

    def confirm(self):
        form = self.get_form(id='formID')
        form.submit()

    def handle_response(self, account, recipient, amount, reason):
        account_txt = CleanText('//form//dl/dt[span[contains(text(), "biter")]]/following::dd[1]', replace=[(' ', '')])(self.doc)
        recipient_txt = CleanText('//form//dl/dt[span[contains(text(), "diter")]]/following::dd[1]', replace=[(' ', '')])(self.doc)
        try:
            assert account.id in account_txt or ''.join(account.label.split()) == account_txt
            assert recipient.id in recipient_txt or ''.join(recipient.label.split()) == recipient_txt
        except AssertionError:
            raise TransferError('Something went wrong')
        r_amount =  CleanDecimal('//form//dl/dt[span[contains(text(), "Montant")]]/following::dd[1]', replace_dots=True)(self.doc)
        exec_date = Date(CleanText('//form//dl/dt[span[contains(text(), "Date")]]/following::dd[1]'), dayfirst=True)(self.doc)
        currency = FrenchTransaction.Currency('//form//dl/dt[span[contains(text(), "Montant")]]/following::dd[1]')(self.doc)

        transfer = Transfer()
        transfer.currency = currency
        transfer.amount = r_amount
        transfer.account_iban = account.iban
        transfer.recipient_iban = recipient.iban
        transfer.account_id = account.id
        transfer.recipient_id = recipient.id
        transfer.exec_date = exec_date
        transfer.label = reason
        transfer.account_label = account.label
        transfer.recipient_label = recipient.label
        transfer.account_balance = account.balance
        return transfer


class TransferSummary(LoggedPage, CheckTransferError):
    def handle_response(self, transfer):
        transfer.id = Regexp(CleanText('//div[@class="bloc Tmargin"]'), 'Votre virement N.+ (\d+) ')(self.doc)
        return transfer
