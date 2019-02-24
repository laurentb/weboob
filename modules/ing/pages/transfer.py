# -*- coding: utf-8 -*-

# Copyright(C) 2009-2014  Romain Bignon, Florent Fourcot
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

from datetime import datetime

from weboob.capabilities.bank import Recipient, Transfer, TransferInvalidAmount
from weboob.capabilities import NotAvailable
from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.standard import CleanText, CleanDecimal, Env
from weboob.browser.filters.html import Attr
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.capabilities.bank.iban import is_iban_valid
from weboob.tools.date import parse_french_date

from .login import INGVirtKeyboard


class MyRecipient(ItemElement):
    klass = Recipient

    def obj_enabled_at(self):
        return datetime.now().replace(microsecond=0)


class TransferPage(LoggedPage, HTMLPage):
    def able_to_transfer(self, origin):
        return [div for div in self.doc.xpath('//div[@id="internalAccounts"]//div[@data-acct-number]')
                if Attr('.', 'data-acct-number')(div) in origin.id and 'disabled' not in div.attrib['class']]

    @method
    class get_recipients(ListElement):
        class ExternalRecipients(ListElement):
            item_xpath = '//tr[@id="externalAccountsIsotopeWrapper"]//div[not(has-class("disabled")) and @data-acct-number]'

            class item(MyRecipient):

                obj_id = Attr('.', 'data-acct-number')
                obj_label = CleanText('.//span[@class="title"]')
                obj_category = u'Externe'
                obj_bank_name = CleanText(Attr('.//span[@class="bankname"]', 'title'))

                def obj_iban(self):
                    return self.obj_id(self) if is_iban_valid(self.obj_id(self)) else NotAvailable

        class InternalRecipients(ListElement):
            item_xpath = '//div[@id="internalAccounts"]//td/div[not(has-class("disabled"))]'

            class item(MyRecipient):

                obj_category = u'Interne'
                obj_currency = FrenchTransaction.Currency('.//span[@class="solde"]/label')
                obj_id = Env('id')
                obj_label = Env('label')
                obj_iban = Env('iban')
                obj_bank_name = u'ING'

                def parse(self, el):
                    _id = Attr('.', 'data-acct-number')(self)
                    accounts = [acc for acc in self.page.browser.get_accounts_list(fill_account=False, space=self.env['origin']._space) if _id in acc.id]
                    assert len(accounts) == 1
                    account = accounts[0]
                    self.env['id'] = account.id
                    self.env['label'] = account.label
                    self.env['iban'] = account.iban

    def get_origin_account_id(self, origin):
        return [Attr('.', 'data-acct-number')(div) for div in self.doc.xpath('//div[@id="internalAccounts"]//div[@data-acct-number]')
                if Attr('.', 'data-acct-number')(div) in origin.id][0]

    def update_origin_account_estimated_balance(self, origin):
        for div in self.doc.xpath('//div[@id="internalAccounts"]//div[@data-acct-number]'):
            if Attr('.', 'data-acct-number')(div) in origin.id:
                origin._estimated_balance = CleanDecimal('.//span[@class="solde"]', replace_dots=True, default=NotAvailable)(div)

    def update_origin_account_label(self, origin):
        # 'Compte Courant Joint' can become 'Compte Courant'
        # search for the account label used to do transfer
        for div in self.doc.xpath('//div[@id="internalAccounts"]//div[@data-acct-number]'):
            if Attr('.', 'data-acct-number')(div) in origin.id:
                origin._account_label = CleanText('.//span[@class="title"]', default=NotAvailable)(div)

    def update_recipient_account_label(self, recipient):
        # 'Compte Courant Joint' can become 'Compte Courant'
        # search for the account label used to do transfer
        for div in self.doc.xpath('//div[@id="internalAccounts"]//div[@data-acct-number]'):
            if Attr('.', 'data-acct-number')(div) in recipient.id:
                recipient._account_label = CleanText('.//span[@class="title"]', default=NotAvailable)(div)

    def get_transfer_form(self, txt):
        form = self.get_form(xpath='//form[script[contains(text(), "%s")]]' % txt)
        form['AJAXREQUEST'] = '_viewRoot'
        form['AJAX:EVENTS_COUNT'] = '1'
        param = Attr('//form[script[contains(text(), "RenderTransferDetail")]]/script[contains(text(), "%s")]' % txt, 'id')(self.doc)
        form[param] = param
        return form

    def go_to_recipient_selection(self, origin):
        form = self.get_transfer_form('SetScreenStep')
        form['screenStep'] = '1'
        form.submit()

        # update account estimated balance and account label for the origin account check on summary page
        self.update_origin_account_estimated_balance(origin)
        self.update_origin_account_label(origin)
        # Select debit account
        form = self.get_transfer_form('SetDebitAccount')
        form['selectedDebitAccountNumber'] = self.get_origin_account_id(origin)
        form.submit()

        # Render available accounts
        form = self.get_transfer_form('ReRenderAccountList')
        form.submit()

    def do_transfer(self, account, recipient, transfer):
        self.go_to_recipient_selection(account)

        # update recipient account label for the recipient check on summary page
        self.update_recipient_account_label(recipient)
        form = self.get_transfer_form('SetScreenStep')
        form['screenStep'] = '2'
        form.submit()

        form = self.get_transfer_form('SetCreditAccount')
        # intern id is like XX-XXXXXXXXXXXX but in request, only the second part is necessary
        form['selectedCreditAccountNumber'] = recipient.id.split('-')[-1]
        form.submit()

        form = self.get_transfer_form('ReRenderAccountList')
        form.submit()

        form = self.get_transfer_form('ReRenderStepTwo')
        form.submit()

        form = self.get_form()
        keys = [k for k in form if '_link_hidden' in k or 'j_idcl' in k]
        for k in keys:
            form.pop(k)
        form['AJAXREQUEST'] = "_viewRoot"
        form['AJAX:EVENTS_COUNT'] = "1"
        form["transfer_form:transferAmount"] = str(transfer.amount)
        form["transfer_form:validateDoTransfer"] = "needed"
        form['transfer_form:transferMotive'] = transfer.label
        form['transfer_form:ipt-date-exec'] = transfer.exec_date.strftime('%d/%m/%Y')
        form['transfer_form'] = 'transfer_form'
        form['transfer_form:valide'] = 'transfer_form:valide'
        form.submit()

    def continue_transfer(self, password):
        form = self.get_form(xpath='//form[h2[contains(text(), "Saisissez votre code secret pour valider la transaction")]]')
        vk = INGVirtKeyboard(self)
        for k in form:
            if 'mrltransfer' in k:
                form[k] = vk.get_coordinates(password)
        form.submit()

    def confirm(self, password):
        vk = INGVirtKeyboard(self)

        form = self.get_form(xpath='//form[h2[contains(text(), "Saisissez votre code secret pour valider la transaction")]]')
        for elem in form:
            if "_link_hidden_" in elem or "j_idcl" in elem:
                form.pop(elem)

        form['AJAXREQUEST'] = '_viewRoot'
        form['%s:mrgtransfer' % form.name] = '%s:mrgtransfer' % form.name
        form['%s:mrltransfer' % form.name] = vk.get_coordinates(password)
        form.submit()

    def recap(self, origin, recipient, transfer):
        error = CleanText(u'//div[@id="transfer_form:moveMoneyDetailsBody"]//span[@class="error"]', default=None)(self.doc) or \
                CleanText(u'//p[contains(text(), "Nous sommes désolés. Le solde de votre compte ne doit pas être inférieur au montant de votre découvert autorisé. Veuillez saisir un montant inférieur.")]', default=None)(self.doc)
        if error:
            raise TransferInvalidAmount(message=error)

        t = Transfer()
        t.label = transfer.label
        t.amount = CleanDecimal('//div[@id="transferSummary"]/div[@id="virementLabel"]\
                                 //label[@class="digits positive"]', replace_dots=True)(self.doc)
        t.currency = FrenchTransaction.Currency('//div[@id="transferSummary"]/div[@id="virementLabel"]\
                                                 //label[@class="digits positive"]')(self.doc)

        # check origin account balance
        origin_balance = CleanDecimal('//div[@id="transferSummary"]/div[has-class("debit")]\
                                       //label[has-class("digits")]', replace_dots=True)(self.doc)
        assert (origin_balance == origin.balance) or (origin_balance == origin._estimated_balance)
        t.account_balance = origin.balance

        # check account label for origin and recipient
        origin_label = CleanText('//div[@id="transferSummary"]/div[has-class("debit")]\
                                  //span[@class="title"]')(self.doc)
        recipient_label = CleanText('//div[@id="transferSummary"]/div[has-class("credit")]\
                                     //span[@class="title"]')(self.doc)
        assert (origin.label == origin_label) or (origin._account_label == origin_label)
        assert (recipient.label == recipient_label) or (recipient._account_label == recipient_label)

        t.account_label = origin.label
        t.account_iban = origin.iban
        t.account_id = origin.id

        t.recipient_label = recipient.label
        t.recipient_iban = recipient.iban
        t.recipient_id = recipient.id

        t.exec_date = parse_french_date(CleanText('//p[has-class("exec-date")]', children=False,
                                        replace=[('le', ''), (u'exécuté', ''), ('demain', ''), ('(', ''), (')', ''),
                                                 ("aujourd'hui", '')])(self.doc)).date()

        return t
