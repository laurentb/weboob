# -*- coding: utf-8 -*-

# Copyright(C) 2018      Sylvie Ye
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

from __future__ import unicode_literals

import re
from datetime import date, timedelta

from weboob.browser.pages import HTMLPage, PartialHTMLPage, LoggedPage
from weboob.browser.elements import method, ListElement, ItemElement, SkipItem
from weboob.browser.filters.standard import (
    CleanText, Date, Regexp, CleanDecimal, Currency, Field, Env,
)
from weboob.capabilities.bank import Recipient, Transfer, TransferBankError, AddRecipientBankError
from weboob.capabilities.base import NotAvailable


class RecipientsPage(LoggedPage, HTMLPage):
    @method
    class iter_external_recipients(ListElement):
        # use list element because there are 4th for 7td in one tr
        item_xpath = '//div[@id="listeCompteExternes"]/table/tbody//tr[@class="ct"]'

        def condition(self):
            return 'Aucun compte externe enregistré' not in CleanText('.')(self)

        class item(ItemElement):
            klass = Recipient

            def obj_label(self):
                if Field('_custom_label')(self):
                    return '{} - {}'.format(Field('_recipient_name')(self), Field('_custom_label')(self))
                return Field('_recipient_name')(self)

            def obj_id(self):
                iban = CleanText('./td[6]', replace=[(' ', '')])(self)
                iban_number = re.search(r'(?<=IBAN:)(\w+)BIC', iban)
                if iban_number:
                    return iban_number.group(1)
                raise SkipItem('There is no IBAN for the recipient %s' % Field('label')(self))

            obj__recipient_name = CleanText('./td[2]')
            obj__custom_label = CleanText('./td[4]')
            obj_iban = NotAvailable
            obj_category = 'Externe'
            obj_enabled_at = date.today()
            obj_currency = 'EUR'
            obj_bank_name = CleanText('./td[1]')

    def check_external_iban_form(self, recipient):
        form = self.get_form(id='CompteExterneActionForm')
        form['codePaysBanque'] = recipient.iban[:2]
        form['codeIban'] = recipient.iban
        form.url = self.browser.BASEURL + '/fr/prive/verifier-compte-externe.jsp'
        form.submit()

    def check_recipient_iban(self):
        if not CleanText('//input[@name="codeBic"]/@value')(self.doc):
            raise AddRecipientBankError(message="Le bénéficiaire est déjà présent ou bien l'iban est incorrect")

    def fill_recipient_form(self, recipient) :
        form = self.get_form(id='CompteExterneActionForm')
        form['codePaysBanque'] = recipient.iban[:2]
        form['codeIban'] = recipient.iban
        form['libelleCompte'] = recipient.label
        form['nomTitulaireCompte'] = recipient.label
        form['methode'] = 'verifierAjout'
        form.submit()

    def get_new_recipient(self, recipient):
        recipient_xpath = '//form[@id="CompteExterneActionForm"]//ul'

        rcpt = Recipient()
        rcpt.label = Regexp(CleanText(
            recipient_xpath + '/li[contains(text(), "Nom du titulaire")]', replace=[(' ', '')]
        ), r'(?<=Nomdutitulaire:)(\w+)')(self.doc)
        rcpt.iban = Regexp(CleanText(
            recipient_xpath + '/li[contains(text(), "IBAN")]'
        ), r'IBAN : ([A-Za-z]{2}[\dA-Za-z]+)')(self.doc)
        rcpt.id = rcpt.iban
        rcpt.category = 'Externe'
        rcpt.enabled_at = date.today() + timedelta(1)
        rcpt.currency = 'EUR'
        return rcpt

    def get_send_code_form(self):
        return self.get_form(id='CompteExterneActionForm')


class RecipientSMSPage(LoggedPage, PartialHTMLPage):
    def on_load(self):
        if not self.doc.xpath('//input[@id="otp"]') and not self.doc.xpath('//div[@class="confirmationAjoutCompteExterne"]'):
            raise AddRecipientBankError(message=CleanText('//div[@id="aidesecuforte"]/p[contains("Nous vous invitons")]')(self.doc))

    def build_doc(self, content):
        content = '<form>' + content.decode('latin-1') + '</form>'
        return super(RecipientSMSPage, self).build_doc(content.encode('latin-1'))

    def get_send_code_form_input(self):
        form = self.get_form()
        return form

    def is_code_expired(self):
        return self.doc.xpath('//label[contains(text(), "Le code sécurité est expiré. Veuillez saisir le nouveau code reçu")]')

    def rcpt_after_sms(self):
        return self.doc.xpath('//div[@class="confirmationAjoutCompteExterne"]\
            /h2[contains(text(), "ajout de compte externe a bien été prise en compte")]')

    def get_error(self):
        return CleanText().filter(self.doc.xpath('//form[@id="CompteExterneActionForm"]//p[@class="container error"]//label[@class="error]'))


class RegisterTransferPage(LoggedPage, HTMLPage):
    @method
    class iter_internal_recipients(ListElement):
        item_xpath = '//select[@name="compteACrediter"]/option[not(@selected)]'

        class item(ItemElement):
            klass = Recipient

            obj_id = CleanText('./@value')
            obj_iban = NotAvailable
            obj_label = CleanText('.')
            obj__recipient_name = CleanText('.')
            obj_category = 'Interne'
            obj_enabled_at = date.today()
            obj_currency = 'EUR'
            obj_bank_name = 'FORTUNEO'

            def condition(self):
                # external recipient id contains 43 characters
                return len(Field('id')(self)) < 40 and Env('origin_account_id')(self) != Field('id')(self)

    def is_account_transferable(self, origin_account):
        for account in self.doc.xpath('//select[@name="compteADebiter"]/option[not(@selected)]'):
            if origin_account.id in CleanText('.')(account):
                return True
        return False

    def get_recipient_transfer_id(self, recipient):
        for account in self.doc.xpath('//select[@name="compteACrediter"]/option[not(@selected)]'):
            recipient_transfer_id = CleanText('./@value')(account)

            if (recipient.id == recipient_transfer_id
                or recipient.id in CleanText('.', replace=[(' ', '')])(account)
            ):
                return recipient_transfer_id

    def fill_transfer_form(self, account, recipient, amount, label, exec_date):
        recipient_transfer_id = self.get_recipient_transfer_id(recipient)
        assert recipient_transfer_id

        form = self.get_form(id='SaisieVirementForm')
        form['compteADebiter'] = account.id
        form['libelleCompteADebiter'] = CleanText(
            '//select[@name="compteADebiter"]/option[@value="%s"]' % account.id
        )(self.doc)
        form['compteACrediter'] = recipient_transfer_id
        form['libelleCompteACrediter'] = CleanText(
            '//select[@name="compteACrediter"]/option[@value="%s"]' % recipient_transfer_id
        )(self.doc)
        form['nomBeneficiaire'] = recipient._recipient_name
        form['libellePopupDoublon'] = recipient._recipient_name
        form['destinationEconomiqueFonds'] = ''
        form['periodicite'] = 1
        form['typeDeVirement'] = 'VI'
        form['dateDeVirement'] = exec_date.strftime('%d/%m/%Y')
        form['montantVirement'] = amount
        form['libelleVirementSaisie'] = label
        form.submit()


class ValidateTransferPage(LoggedPage, HTMLPage):
    def on_load(self):
        if self.doc.xpath('//form[@id="SaisieVirementForm"]/p[has-class("error")]'):
            raise TransferBankError(CleanText(
                '//form[@id="SaisieVirementForm"]/p[has-class("error")]/label'
            )(self.doc))

    def check_transfer_data(self, transfer_data):
        for t_data in transfer_data:
            assert t_data in transfer_data[t_data], '%s not found in transfer summary %s' % (t_data, transfer_data[t_data])

    def handle_response(self, account, recipient, amount, label, exec_date):
        summary_xpath = '//div[@id="as_verifVirement.do_"]//ul'

        transfer = Transfer()

        transfer_data = {
            account.id: CleanText(
                summary_xpath + '/li[contains(text(), "Compte à débiter")]'
            )(self.doc),
            recipient.id: CleanText(
                summary_xpath + '/li[contains(text(), "Compte à créditer")]', replace=[(' ', '')]
            )(self.doc),
            recipient._recipient_name: CleanText(
                summary_xpath + '/li[contains(text(), "Nom du bénéficiaire")]'
            )(self.doc),
            label: CleanText(summary_xpath + '/li[contains(text(), "Motif")]')(self.doc),
        }
        self.check_transfer_data(transfer_data)

        transfer.account_id = account.id
        transfer.account_label = account.label
        transfer.account_iban = account.iban

        transfer.recipient_id = recipient.id
        transfer.recipient_label = recipient.label
        transfer.recipient_iban = recipient.iban

        transfer.label = label
        transfer.currency = Currency(summary_xpath + '/li[contains(text(), "Montant")]')(self.doc)
        transfer.amount = CleanDecimal(
            Regexp(CleanText(summary_xpath + '/li[contains(text(), "Montant")]'), r'((\d+)\.?(\d+)?)')
        )(self.doc)
        transfer.exec_date = Date(Regexp(CleanText(
            summary_xpath + '/li[contains(text(), "Date de virement")]'
        ), r'(\d+/\d+/\d+)'), dayfirst=True)(self.doc)

        return transfer

    def validate_transfer(self):
        form = self.get_form(id='SaisieVirementForm')
        form['methode'] = 'valider'
        form.submit()


class ConfirmTransferPage(LoggedPage, HTMLPage):
    def confirm_transfer(self):
        confirm_transfer_url = '/fr/prive/mes-comptes/compte-courant/realiser-operations/effectuer-virement/confirmer-saisie-virement.jsp'
        self.browser.location(self.browser.BASEURL + confirm_transfer_url, data={'operationTempsReel': 'true'})

    def transfer_confirmation(self, transfer):
        if self.doc.xpath('//div[@class="confirmation_virement"]/h2[contains(text(), "virement a bien été enregistrée")]'):
            return transfer
