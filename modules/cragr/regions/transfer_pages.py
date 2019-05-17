# -*- coding: utf-8 -*-

# Copyright(C) 2012-2019  Budget Insight
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


from __future__ import unicode_literals


from datetime import date as ddate, datetime
from decimal import Decimal
import re

from weboob.browser.pages import LoggedPage, HTMLPage, FormNotFound
from weboob.capabilities.base import Currency
from weboob.capabilities.bank import (
    Recipient, Transfer, TransferError, TransferBankError,
    AddRecipientBankError, RecipientInvalidOTP
)
from weboob.browser.filters.standard import (
    Date, CleanText, CleanDecimal, Currency as CleanCurrency, Regexp,
)
from weboob.browser.filters.html import Link


def get_text_lines(el):
    lines = [re.sub(r'\s+', ' ', line).strip() for line in el.text_content().split('\n')]
    return [l for l in lines if l]


def MyDate(*args, **kwargs):
    kwargs.update(dayfirst=True)
    return Date(*args, **kwargs)


class HandleErrorHTMLPage(HTMLPage):
    def get_error(self):
        error = CleanText('//h1[@class="h1-erreur"]')(self.doc)
        if error:
            self.logger.error('Error detected: %s', error)
            return error


class CollectePageMixin(object):
    """
    Multiple pages have the same url pattern: "/stb/collecteNI?fwkaid=...&fwkpid=...".
    Use some page text to determine which page it is.
    """

    IS_HERE_TEXT = None

    def is_here(self):
        for el in self.doc.xpath('//div[@class="boutons-act"]//h1'):
            labels = self.IS_HERE_TEXT
            if not isinstance(labels, (list, tuple)):
                labels = [labels]

            for label in labels:
                if label in CleanText('.')(el):
                    return True
        return False


class TransferInit(LoggedPage, HandleErrorHTMLPage):
    def iter_emitters(self):
        items = self.doc.xpath('//select[@name="VIR_VIR1_FR3_LE"]/option')
        return self.parse_recipients(items, assume_internal=True)

    def iter_recipients(self):
        items = self.doc.xpath('//select[@name="VIR_VIR1_FR3_LB"]/option')
        return self.parse_recipients(items)

    def parse_recipients(self, items, assume_internal=False):
        for opt in items:
            lines = get_text_lines(opt)

            if opt.attrib['value'].startswith('I') or assume_internal:
                for n, line in enumerate(lines):
                    if line.strip().startswith('n°'):
                        rcpt = Recipient()
                        rcpt._index = opt.attrib['value']
                        rcpt._raw_label = ' '.join(lines)
                        rcpt.category = 'Interne'
                        rcpt.id = CleanText().filter(line[2:].strip())
                        # we don't have iban here, use account number
                        rcpt.label = ' '.join(lines[:n])
                        rcpt.currency = Currency.get_currency(lines[-1])
                        rcpt.enabled_at = datetime.now().replace(microsecond=0)
                        yield rcpt
                        break
            elif opt.attrib['value'].startswith('E'):
                if len(lines) > 1:
                    # In some cases we observed beneficiaries without label, we skip them
                    rcpt = Recipient()
                    rcpt._index = opt.attrib['value']
                    rcpt._raw_label = ' '.join(lines)
                    rcpt.category = 'Externe'
                    rcpt.label = lines[0]
                    rcpt.iban = lines[1].upper()
                    rcpt.id = rcpt.iban
                    rcpt.enabled_at = datetime.now().replace(microsecond=0)
                    yield rcpt
                else:
                    self.logger.warning('The recipient associated with the iban %s has got no label' % lines[0])

    def submit_accounts(self, account_id, recipient_id, amount, currency):
        emitters = [rcpt for rcpt in self.iter_emitters() if rcpt.id == account_id and not rcpt.iban]
        if len(emitters) != 1:
            raise TransferError('Could not find emitter %r' % account_id)
        recipients = [rcpt for rcpt in self.iter_recipients() if rcpt.id and rcpt.id == recipient_id]
        # for recipient with same IBAN, first matched recipient is the default value
        if len(recipients) < 1:
            raise TransferError('Could not find recipient %r' % recipient_id)

        form = self.get_form(name='frm_fwk')
        assert amount > 0
        amount = str(amount.quantize(Decimal('0.00')))
        form['T3SEF_MTT_EURO'], form['T3SEF_MTT_CENT'] = amount.split('.')
        form['VIR_VIR1_FR3_LE'] = emitters[0]._index
        form['VIR_VIR1_FR3_LB'] = recipients[0]._index
        form['DEVISE'] = currency or emitters[0].currency
        form['VIR_VIR1_FR3_LE_HID'] = emitters[0]._raw_label
        form['VIR_VIR1_FR3_LB_HID'] = recipients[0]._raw_label
        form['fwkaction'] = 'Confirmer' # mandatory
        form['fwkcodeaction'] = 'Executer'
        form.submit()

    def url_list_recipients(self):
        return CleanText(u'(//a[contains(text(),"Liste des bénéficiaires")])[1]/@href')(self.doc)

    def add_recipient_is_allowed(self):
        return bool(self.doc.xpath('//a[text()="+ Saisir un autre compte bénéficiaire"]') or self.doc.xpath('//a[contains(text(),"Liste des bénéficiaires")]'))

    def url_add_recipient(self):
        link = Link('//a[text()="+ Saisir un autre compte bénéficiaire"]')(self.doc)
        return link + '&IDENT=LI_VIR_RIB1&VIR_VIR1_FR3_LE=0&T3SEF_MTT_EURO=&T3SEF_MTT_CENT=&VICrt_REFERENCE='


class RecipientListPage(LoggedPage, HandleErrorHTMLPage):
    def url_add_recipient(self):
        return CleanText(u'//a[contains(text(),"Ajouter un compte destinataire")]/@href')(self.doc)


class RecipientAddingMixin(object):
    def submit_recipient(self, label, iban):
        try:
            form = self.get_form(name='frm_fwk')
        except FormNotFound:
            assert False, 'An error occurred before sending recipient'

        form['NOM_BENEF'] = label
        for i in range(9):
            form['CIBAN%d' % (i + 1)] = iban[i * 4:(i + 1) * 4]
        form['fwkaction'] = 'VerifCodeIBAN'
        form['fwkcodeaction'] = 'Executer'
        form.submit()


class TransferPage(RecipientAddingMixin, CollectePageMixin, LoggedPage, HandleErrorHTMLPage):
    IS_HERE_TEXT = 'Virement'

    ### for transfers
    def get_step(self):
        return CleanText('//div[@id="etapes"]//li[has-class("encours")]')(self.doc)

    def is_sent(self):
        return self.get_step().startswith('Récapitulatif')

    def is_confirm(self):
        return self.get_step().startswith('Confirmation')

    def is_reason(self):
        return self.get_step().startswith('Informations complémentaires')

    def get_transfer(self):
        transfer = Transfer()

        # FIXME all will probably fail if an account has a user-chosen label with "IBAN :" or "n°"

        amount_xpath = '//fieldset//p[has-class("montant")]'
        transfer.amount = CleanDecimal.French(amount_xpath)(self.doc)
        transfer.currency = CleanCurrency(amount_xpath)(self.doc)

        if self.is_sent():
            transfer.account_id = Regexp(CleanText('//p[@class="nomarge"][span[contains(text(),'
                                                   '"Compte émetteur")]]/text()'),
                                         r'n°(\d+)')(self.doc)

            base = CleanText('//fieldset//table[.//span[contains(text(), "Compte bénéficiaire")]]'
                             '//td[contains(text(),"n°") or contains(text(),"IBAN :")]//text()', newlines=False)(self.doc)
            transfer.recipient_id = Regexp(None, r'IBAN : ([^\n]+)|n°(\d+)').filter(base)
            transfer.recipient_id = transfer.recipient_id.replace(' ', '')
            if 'IBAN' in base:
                transfer.recipient_iban = transfer.recipient_id

            transfer.exec_date = MyDate(CleanText('//p[@class="nomarge"][span[contains(text(), "Date de l\'ordre")]]/text()'))(self.doc)
        else:
            transfer.account_id = Regexp(CleanText('//fieldset[.//h3[contains(text(), "Compte émetteur")]]//p'),
                                         r'n°(\d+)')(self.doc)

            base = CleanText('//fieldset[.//h3[contains(text(), "Compte bénéficiaire")]]//text()',
                             newlines=False)(self.doc)
            transfer.recipient_id = Regexp(None, r'IBAN : ([^\n]+)|n°(\d+)').filter(base)
            transfer.recipient_id = transfer.recipient_id.replace(' ', '')
            if 'IBAN' in base:
                transfer.recipient_iban = transfer.recipient_id

            transfer.exec_date = MyDate(CleanText('//fieldset//p[span[contains(text(), "Virement unique le :")]]/text()'))(self.doc)

        transfer.label = CleanText('//fieldset//p[span[contains(text(), "Référence opération")]]')(self.doc)
        transfer.label = re.sub(r'^Référence opération(?:\s*):', '', transfer.label).strip()

        return transfer

    def submit_more(self, label, date=None):
        if date is None:
            date = ddate.today()

        form = self.get_form(name='frm_fwk')
        form['VICrt_CDDOOR'] = label
        form['VICrtU_DATEVRT_JJ'] = date.strftime('%d')
        form['VICrtU_DATEVRT_MM'] = date.strftime('%m')
        form['VICrtU_DATEVRT_AAAA'] = date.strftime('%Y')
        form['DATEC'] = date.strftime('%d/%m/%Y')
        form['PERIODE'] = 'U'
        form['fwkaction'] = 'Confirmer'
        form['fwkcodeaction'] = 'Executer'
        form.submit()

    def submit_confirm(self):
        form = self.get_form(name='frm_fwk')
        form['fwkaction'] = 'Confirmer'
        form['fwkcodeaction'] = 'Executer'
        form.submit()

    def on_load(self):
        super(TransferPage, self).on_load()
        # warning: the "service indisponible" message (not catched here) is not a real BrowserUnavailable
        err = CleanText('//form//div[has-class("blc-choix-erreur")]//p', default='')(self.doc)
        if err:
            raise TransferBankError(message=err)

    ### add a recipient by faking a transfer
    def confirm_recipient(self):
        # pretend to make a transfer
        form = self.get_form(name='frm_fwk')
        form['AJOUT_BENEF_CHECK'] = 'on'
        form['fwkcodeaction'] = 'Executer'
        form['fwkaction'] = 'Suite'
        form['T3SEF_MTT_EURO'] = '1'
        form['DEVISE'] = 'EUR'
        form.submit()

    def check_error(self):
        # this is for transfer error, it's not a `AddRecipientBankError` but a `TransferBankError`

        msg = CleanText('//tr[@bgcolor="#C74545"]', default='')(self.doc) # there is no id, class or anything...
        if msg:
            raise TransferBankError(message=msg)

    def check_recipient_error(self):
        # this is a copy-paste from RecipientMiscPage, i can't test if it works on this page...
        # this is for add recipient by initiate transfer

        msg = CleanText('//tr[@bgcolor="#C74545"]', default='')(self.doc) # there is no id, class or anything...
        if msg:
            raise AddRecipientBankError(message=msg)


class RecipientMiscPage(RecipientAddingMixin, CollectePageMixin, LoggedPage, HandleErrorHTMLPage):
    IS_HERE_TEXT = 'Liste des comptes bénéficiaires'

    ### for adding recipients
    def send_sms(self):
        form = self.get_form(name='frm_fwk')

        assert 'code' not in form
        form['fwkaction'] = 'DemandeCodeSMSVerifID'
        form['fwkcodeaction'] = 'Executer'
        form.submit()

    def get_sms_error(self):
        return CleanText('//div[@class="blc-choix-wrap-erreur"]')(self.doc)

    def confirm_recipient(self):
        try:
            form = self.get_form(name='frm_fwk')
        except FormNotFound:
            assert False, 'An error occurred before finishing adding recipient'

        form['fwkaction'] = 'ConfirmerAjout'
        form['fwkcodeaction'] = 'Executer'
        form.submit()

    def check_recipient_error(self):
        msg = CleanText('//tr[@bgcolor="#C74545"]', default='')(self.doc) # there is no id, class or anything...
        if msg:
            raise AddRecipientBankError(message=msg)

    def get_iban_col(self):
        for index, td in enumerate(self.doc.xpath('//table[starts-with(@summary,"Nom et IBAN")]//th')):
            if 'Numéro de compte' in CleanText('.')(td):
                # index start at 0
                return index + 1

    def find_recipient(self, iban):
        iban = iban.upper()
        iban_col = self.get_iban_col()

        for tr in self.doc.xpath('//table[starts-with(@summary,"Nom et IBAN")]/tbody/tr'):
            iban_text = re.sub(r'\s', '', CleanText('./td[%s]' % iban_col)(tr))
            if iban_text.upper() == 'IBAN:%s' % iban:
                res = Recipient()
                res.iban = iban
                res.id = iban
                res.label = CleanText('./td[%s]' % (iban_col-1))(tr)
                return res


class RecipientPage(LoggedPage, HandleErrorHTMLPage):
    def can_send_code(self):
        form = self.get_form(name='frm_fwk')
        return 'code' in form

    def send_sms(self):
        form = self.get_form(name='frm_fwk')

        if 'code' in form:
            # a code is still pending, ask a new one
            form['fwkaction'] = 'NouvelleDemandeCodeSMS'
            form['fwkcodeaction'] = 'Executer'
            new_page = form.submit().page
            assert isinstance(new_page, TransferPage) or isinstance(new_page, SendSMSPage)
            return new_page.send_sms()
        else:
            form['fwkaction'] = 'DemandeCodeSMSVerifID'

        form['fwkcodeaction'] = 'Executer'
        form.submit()

    def submit_code(self, code):
        form = self.get_form(name='frm_fwk')
        form['fwkaction'] = 'Confirmer'
        form['fwkcodeaction'] = 'Executer'
        form['code'] = code
        form.submit()


class SendSMSPage(LoggedPage, CollectePageMixin, HandleErrorHTMLPage):
    IS_HERE_TEXT = 'Authentification par sms - demande'

    def on_load(self):
        # if the otp is incorrect
        error_msg = CleanText('//div[has-class("blc-choix-erreur")]//span')(self.doc)
        if error_msg:
            raise AddRecipientBankError(message=error_msg)

    def send_sms(self):
        # when a code is still pending
        # resend sms to validate recipient
        form = self.get_form(name='frm_fwk')
        form['fwkaction'] = 'DemandeCodeSMSVerifID'
        form['fwkcodeaction'] = 'Executer'
        form.submit()


class SubmitSMSPage(LoggedPage, RecipientAddingMixin, HandleErrorHTMLPage):
    IS_HERE_TEXT = 'Authentification par sms - code'


class SendSMSErrorPage(LoggedPage, CollectePageMixin, HTMLPage):
    IS_HERE_TEXT = 'Authentification par sms - erreur code'

    def on_load(self):
        error_msg = CleanText('//font[contains(text(), "Le code SMS saisi n\'est pas exploitable")]')(self.doc)
        raise RecipientInvalidOTP(message=error_msg)
