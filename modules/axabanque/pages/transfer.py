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


import re
import string
from io import BytesIO
from PIL import Image, ImageFilter
from datetime import date

from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.browser.filters.standard import CleanText, Date, Regexp, CleanDecimal, Currency
from weboob.capabilities.bank import Recipient, Transfer, TransferError
from weboob.tools.captcha.virtkeyboard import SimpleVirtualKeyboard


def remove_useless_form_params(form):
    # remove idJsp parameter in form
    for el in list(form):
        if 'idJsp' in el:
            form.pop(el)
    return form


class TransferVirtualKeyboard(SimpleVirtualKeyboard):
    margin = 1
    tile_margin = 10

    symbols = {'0': '715df9c139fc7b46829526229c415a67',
               '1': '12d398f7f389711c5f8298ee68a8af28',
               '2': 'f43ca3a5dd649d30bf02060ab65c4eff',
               '3': 'b6dd7864cfd941badb0784be37f7eeb3',
               '4': '7138d0a663eef56c699d85dc6c3ac639',
               '5': 'b71bd38e71ce0b611642a01b6900218f',
               '6': 'f71f7249413c189165da7b588c2f0493',
               '7': '81fc65230d7df341e80d02e414f183d4',
               '8': '8106671a6b24aee3475d6f12a650f59b',
               '9': 'e8c4567eb46dba5e2a92619076441a8a'
              }

    # Clean image
    def alter_image(self):
        # See ImageFilter.UnsharpMask from Pillow
        self.image = self.image.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
        # Convert to binary image
        self.image = Image.eval(self.image, lambda px: 0 if px <= 100 else 255)


class RecipientsPage(LoggedPage, HTMLPage):
    def get_extenal_recipient_ibans(self):
        ibans_xpath = '//table[@id="saisieBeneficiaireSepa:idBeneficiaireSepaListe:' \
                      'table-beneficiaires"]//td[@class="destIban"]'

        for iban in self.doc.xpath(ibans_xpath):
            yield CleanText('.', replace=[(' ', '')])(iban)


class RegisterTransferPage(LoggedPage, HTMLPage):
    def on_load(self):
        super(RegisterTransferPage, self).on_load()

        error_xpath = '//span[@class="erreur_phrase"]'
        if self.doc.xpath(error_xpath):
            error_msg = CleanText(error_xpath)(self.doc)
            raise TransferError(message=error_msg)

    def is_transfer_account(self, acc_id):
        valide_accounts_xpath = '//select[@id="compteEmetteurSelectionne"]//option[not(contains(@value,"vide0"))]'

        for valide_account in self.doc.xpath(valide_accounts_xpath):
            if acc_id == CleanText('./@value')(valide_account):
                return True
        return False

    # To get page with all recipients for an account
    def set_account(self, acc_id):
        form = self.get_form(id='idFormSaisieVirement')
        form['compteEmetteurSelectionne'] = acc_id
        form[':cq_csrf_token:'] = 'undefined'

        remove_useless_form_params(form)
        form.pop('effetVirementDiffere')
        form.pop('effetVirementPermanent')
        form.pop('periodicite')
        form.pop('fin')
        form.pop('idFormSaisieVirement:idBtnAnnuler')
        form.pop('idFormSaisieVirement:idBtnValider')

        form.submit()

    # Get all recipient for an account
    def get_recipients(self):
        recipients_xpath = '//select[@id="compteDestinataireSelectionne"]/option[not(contains(@selected, "selected"))]'

        for recipient in self.doc.xpath(recipients_xpath):
            rcpt = Recipient()

            rcpt.label = re.sub(r' - \w{2,}\d{6,}', '', CleanText('.')(recipient))
            rcpt.iban = CleanText('./@value')(recipient)
            rcpt.id = rcpt.iban
            rcpt.enabled_at = date.today()
            rcpt.category = u'INTERNE'

            yield rcpt

    # To do a transfer
    def fill_transfer_form(self, acc_id, recipient_iban, amount, reason, exec_date=None):
        form = self.get_form(id='idFormSaisieVirement')
        form['compteEmetteurSelectionne'] = acc_id
        form['compteDestinataireSelectionne'] = recipient_iban
        form['idFormSaisieVirement:montantVirement'] = str(amount).replace('.', ',')
        form['idFormSaisieVirement:libelleVirement'] = reason
        form['idFormSaisieVirement:idBtnValider'] = ' '

        form.pop('idFormSaisieVirement:idBtnAnnuler')
        form.pop('effetVirementPermanent')
        form.pop('periodicite')
        form.pop('fin')

        # Deferred transfer
        if exec_date:
            form['effetVirementDiffere'] = exec_date.strftime('%d/%m/%Y')
            form['typeVirement'] = 2

            form.submit()
            return

        form.pop('effetVirementDiffere')

        form.submit()


class ValidateTransferPage(LoggedPage, HTMLPage):
    is_here = '//p[contains(text(), "votre code confidentiel")]'

    def get_element_by_name(self, col_heads_name):
        # self.col_heads and self.col_contents have to be defined to use this function

        assert len(self.col_heads) > 0
        # self.col_heads and self.col_contents should have same length
        assert len(self.col_heads) == len(self.col_contents)

        for index, head in enumerate(self.col_heads):
            if col_heads_name in head:
                return self.col_contents[index]
        assert False

    def handle_response(self, account, recipient, amount, reason):
        tables_xpath = '//table[@id="table-confVrt" or @id="table-confDestinataire"]'

        # Summary is divided into 2 tables, we have to concat them
        # col_heads is a list of all header of the 2 tables (order is important)
        self.col_heads = [CleanText('.')(head) for head in self.doc.xpath(tables_xpath + '//td[@class="libColumn"]')]
        # col_contents is a list of all content of the 2 tables (order is important)
        self.col_contents = [CleanText('.')(content) for content in self.doc.xpath(tables_xpath + '//td[@class="contentColumn"]')]

        transfer = Transfer()

        transfer.currency = Currency().filter(self.get_element_by_name('Montant'))
        transfer.amount = CleanDecimal().filter(self.get_element_by_name('Montant'))

        date = Regexp(pattern=r'(\d+/\d+/\d+)').filter(self.get_element_by_name('Date du virement'))
        transfer.exec_date = Date(dayfirst=True).filter(date)

        account_label_id = self.get_element_by_name(u'Compte à débiter')
        transfer.account_id = (Regexp(pattern=r'(\d+)').filter(account_label_id))
        transfer.account_label = Regexp(pattern=r'([\w \.]+)').filter(account_label_id)
        # account iban is not in the summary page
        transfer.account_iban = account.iban

        transfer.recipient_id = recipient.id
        transfer.recipient_iban = self.get_element_by_name('IBAN').replace(' ', '')
        transfer.recipient_label = self.get_element_by_name(u'Nom du bénéficiaire')
        transfer.label = CleanText('//table[@id="table-confLibelle"]//p')(self.doc)

        return transfer

    def get_password(self, password):
        img_src = CleanText('//div[@id="paveNumTrans"]//img[contains(@id, "imagePave")]/@src')(self.doc)
        f = BytesIO(self.browser.open(img_src).content)

        vk = TransferVirtualKeyboard(file=f, cols=8, rows=3, matching_symbols=string.ascii_lowercase[:8*3])

        return vk.get_string_code(password)

    def validate_transfer(self, password):
        password = self.get_password(password)
        form = self.get_form(xpath='//div[@id="paveNumTrans"]/parent::form')

        # Get validation btn id because '_idJsp27' part may be not stable
        validation_btn_id = CleanText('//div[@id="paveNumTrans"]//input[contains(@id, "boutonValider")]/@id')(self.doc)

        form['codepasse'] = password
        form['motDePasse'] = password
        form[validation_btn_id] = ''
        form.submit()


class ConfirmTransferPage(LoggedPage, HTMLPage):
    def on_load(self):
        confirm_transfer_xpath = '//h2[contains(text(), "Virement enregistr")]'
        assert self.doc.xpath(confirm_transfer_xpath)
