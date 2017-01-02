# -*- coding: utf-8 -*-

# Copyright(C) 2016 Baptiste Delpey
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
import re
from cStringIO import StringIO
from logging import error
from weboob.tools.json import json

from weboob.browser.pages import LoggedPage
from weboob.browser.elements import method, ListElement, ItemElement
from weboob.capabilities.bank import Recipient, TransferError, Transfer
from weboob.capabilities.base import find_object, NotAvailable
from weboob.browser.filters.standard import CleanText, Regexp, CleanDecimal, \
                                            Env, Date
from weboob.browser.filters.html import Attr
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.ordereddict import OrderedDict

from ..captcha import Captcha, TileError
from .base import BasePage
from .login import PasswordPage


class MyRecipient(ItemElement):
    klass = Recipient

    # Assume all recipients currency is euros.
    obj_currency = u'EUR'

    def obj_enabled_at(self):
        return datetime.now().replace(microsecond=0)


class RecipientsPage(LoggedPage, BasePage):
    @method
    class iter_recipients(ListElement):
        item_xpath = '//div[@class="items-groups"]/a'

        class Item(MyRecipient):
            obj_id = obj_iban = CleanText('./div[1]/div[1]/span[1]')
            obj_bank_name = CleanText('./div[1]/div[2]/span[1]')
            obj_category = u'Externe'

            def obj_label(self):
                first_label = CleanText('./div[1]/div[3]/span[1]')(self)
                second_label = CleanText('./div[1]/div[3]/span[2]')(self)
                return first_label if first_label == second_label else ('%s %s' % (first_label, second_label)).strip()


class TransferPage(LoggedPage, BasePage, PasswordPage):
    def on_load(self):
        error_msg = CleanText('//span[@class="error_msg"]')(self.doc)
        if error_msg:
            raise TransferError(error_msg)

    @method
    class iter_recipients(ListElement):
        item_xpath = '//select[@id="SelectDest"]/optgroup[@label="Vos comptes"]/option | //select[@id="SelectDest"]/optgroup[@label="Procurations"]/option'

        class Item(MyRecipient):
            validate = lambda self, obj: self.obj_id(self) != self.env['account_id']

            obj_id = Env('id')
            obj_label = Env('label')
            obj_bank_name = u'Société Générale'
            obj_category = u'Interne'
            obj_iban = Env('iban')

            def parse(self, el):
                _id = Regexp(CleanText('.', replace=[(' ', '')]), '(\d+)', default=NotAvailable)(self)
                if _id:
                    account = find_object(self.page.browser.get_accounts_list(), id=_id)
                    self.env['id'] = _id
                else:
                    account = find_object(self.page.browser.get_accounts_list(), label=Regexp(CleanText('.'), '- (.*)')(self))
                    self.env['id']= account.id
                self.env['label'] = account.label
                self.env['iban'] = account.iban

    def get_params(self, _id, _type):
        for script in [sc for sc in self.doc.xpath('//script') if sc.text]:
            accounts = re.findall('TableauComptes%s.*?\)' % _type, script.text)
            if accounts:
                break
        for account in accounts:
            params = re.findall('"(.*?)"', account)
            if params[2] + params[3] == _id or params[3] + params[4] == _id or params[-2] == _id:
                return params

    def get_account_value(self, _id):
        for option in self.doc.xpath('//select[@id="SelectEmet"]//option'):
            if _id in CleanText('.', replace=[(' ', '')])(option):
                attr = Attr('.', 'value')(option)
                return attr

    def init_transfer(self, account, recipient, transfer):
        try:
            assert account.currency == recipient.currency == 'EUR'
        except AssertionError:
            raise TransferError('wrong currency')
        origin_params = self.get_params(account.id, 'Emetteurs')
        recipient_params = self.get_params(recipient.id, 'Destinataires')
        data = OrderedDict()
        value = self.get_account_value(account.id)
        data['dup'] = re.search('dup=(.*?)(&|$)', value).group(1)
        data['src'] = re.search('src=(.*?)(&|$)', value).group(1)
        data['sign'] = re.search('sign=(.*?)(&|$)', value).group(1)

        data['cdbqem'] = origin_params[1]
        data['cdguem'] = origin_params[2]
        data['nucpem'] = origin_params[3]
        data['clriem'] = origin_params[4]
        data['libeem'] = origin_params[5]
        data['grroem'] = origin_params[6]
        data['cdprem'] = origin_params[7]
        data['liprem'] = origin_params[8]

        # This one seem to be set in stone.
        data['inrili'] = 'N'
        data['toprib'] = '0' if recipient_params[0] == 'pic_a_recuperer' else '1'

        if recipient_params[1]:
            data['idprde'] = recipient_params[1]
        data['cdbqde'] = recipient_params[2]
        data['cdgude'] = recipient_params[3]
        data['nucpde'] = recipient_params[4]
        data['clride'] = recipient_params[5]
        data['libede'] = recipient_params[6]
        data['grrode'] = recipient_params[7]
        if recipient_params[8]:
            data['cdprde'] = recipient_params[8]
        if recipient_params[9]:
            data['liprde'] = recipient_params[9]
        if recipient_params[10]:
            data['tycpde'] = recipient_params[10]
        data['formatCompteBenef'] = recipient_params[12]
        data['nomBenef'] = recipient_params[13]
        data['codeBICBenef'] = recipient_params[15]
        data['codeIBANBenef'] = recipient_params[16]
        # This needs the currency to be euro.
        data['mntval'] = transfer.amount * 100
        data['mntcdc'] = '2'
        data['mntcdv'] = 'EUR'
        data['datvir'] = transfer.exec_date.strftime('%Y%m%d')
        data['motvir'] = transfer.label
        # Initiate transfer
        self.browser.location('/lgn/url.html?%s' % '&'.join(['%s=%s' % (k, v) for k, v in data.iteritems()]))

    def check_data_consistency(self, account, recipient, transfer):
        try:
            assert transfer.amount == CleanDecimal('.//td[@headers="virement montant"]', replace_dots=True)(self.doc)
            assert transfer.exec_date == Date(CleanText('.//td[@headers="virement date"]'), dayfirst=True)(self.doc)
            assert transfer.label in CleanText('.//td[@headers="virement motif"]')(self.doc)
        except AssertionError:
            raise TransferError('data consistency failed.')

    def create_transfer(self, account, recipient, transfer):
        transfer = Transfer()
        transfer.currency = FrenchTransaction.Currency('.//td[@headers="virement montant"]')(self.doc)
        transfer.amount = CleanDecimal('.//td[@headers="virement montant"]', replace_dots=True)(self.doc)
        transfer.account_iban = CleanText('//td[@headers="emetteur IBAN"]', replace=[(' ', '')])(self.doc)
        transfer.recipient_iban = CleanText('//td[@headers="beneficiaire IBAN"]', replace=[(' ','')])(self.doc)
        transfer.account_id = account.id
        transfer.recipient_id = recipient.id
        transfer.exec_date = Date(CleanText('.//td[@headers="virement date"]'), dayfirst=True)(self.doc)
        transfer.label = CleanText('.//td[@headers="virement motif"]')(self.doc)
        transfer.account_label = account.label
        transfer.recipient_label = recipient.label
        transfer._account = account
        transfer._recipient = recipient
        transfer.account_balance = account.balance
        return transfer

    def confirm(self):
        form = self.get_form(id='authentification')

        url = self.browser.BASEURL + '//sec/vkm/gen_crypto?estSession=0'
        infos_data = self.browser.open(url).content
        infos_data = re.match('^_vkCallback\((.*)\);$', infos_data).group(1)
        infos = json.loads(infos_data.replace("'", '"'))
        infos['grid'] = self.decode_grid(infos)
        url = self.browser.BASEURL + '/sec/vkm/gen_ui?modeClavier=0&cryptogramme=' + infos["crypto"]
        content = self.browser.open(url).content
        img = Captcha(StringIO(content), infos)

        try:
            img.build_tiles()
        except TileError as err:
            error("Error: %s" % err)
            if err.tile:
                err.tile.display()

        pwd = img.get_codes(self.browser.password[:6])
        t = pwd.split(',')
        newpwd = ','.join([t[self.strange_map[j]] for j in xrange(6)])
        form['codsec'] = newpwd
        form['cryptocvcs'] = infos["crypto"].encode('iso-8859-1')
        form['vkm_op'] = 'sign'
        form.submit()
