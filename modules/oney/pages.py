# -*- coding: utf-8 -*-

# Copyright(C) 2014 Budget Insight
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

import re
from decimal import Decimal

import requests

from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import FrenchTransaction, sorted_transactions
from weboob.browser.pages import HTMLPage, LoggedPage, pagination, XLSPage, PartialHTMLPage, JsonPage
from weboob.browser.elements import ListElement, ItemElement, method, DictElement
from weboob.browser.filters.standard import Env, CleanDecimal, CleanText, Field, Format, Currency, Date
from weboob.browser.filters.html import Attr
from weboob.browser.filters.json import Dict
from weboob.exceptions import BrowserIncorrectPassword
from weboob.tools.compat import urlparse, parse_qsl

class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(r'^(?P<text>Retrait .*?) - traité le \d+/\d+$'), FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(r'^(?P<text>(Prélèvement|Cotisation|C R C A M) .*?) - traité le \d+/\d+$'), FrenchTransaction.TYPE_ORDER),  # C R C A M is a bank it is hardcoded here because some client want it typed and it would be a mess to scrap it
                (re.compile(r"^(?P<text>(Frais sur achat à l'étranger|Facturation).*?) - traité le \d+/\d+$"), FrenchTransaction.TYPE_BANK),
                (re.compile(r'^Intérêts mensuels'), FrenchTransaction.TYPE_BANK),
                (re.compile(r'^(?P<text>(Avoir comptant|ANNULATION|Annulation) .*?) - traité le \d+/\d+$'), FrenchTransaction.TYPE_PAYBACK),
                (re.compile(r'^(?P<text>(RETRAIT )?DAB .*?) - traité le \d+/\d+$'), FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(r'^(?P<text>.*?)(, taux de change de(.*)?)? - traité le( (\d+|/\d+)*$|$)'), FrenchTransaction.TYPE_CARD)]  # some labels are really badly formed so the regex needs to be this nasty to catch all edge cases


class ContextInitPage(JsonPage):
    def get_client_id(self):
        return self.doc['context']['client_id']

    def get_success_url(self):
        return self.doc['context']['success_url']

    def get_customer_session_id(self):
        return self.doc['context']['customer_session_id']


class SendUsernamePage(JsonPage):
    def get_flow_id(self):
        return self.doc['authenticationFlowInit']['flow_id']


class SendPasswordPage(JsonPage):
    def get_token(self):
        return self.doc['completeAuthFlowStep']['token']

    def check_error(self):
        errors = self.doc['completeAuthFlowStep']['errors']
        if errors:
            raise BrowserIncorrectPassword(errors[0]['label'])


class CheckTokenPage(JsonPage):
    pass


class LoginPage(HTMLPage):
    def get_context_token(self):
        parameters = dict(parse_qsl(urlparse(self.url).query))
        return parameters.get('context_token', None)


class ChoicePage(LoggedPage, HTMLPage):
    def get_pages(self):
        for page_attrib in self.doc.xpath('//a[@data-site]/@data-site'):
            yield self.browser.open('/site/s/login/loginidentifiant.html',
                                    data={'selectedSite': page_attrib}).page


class DetailPage(LoggedPage, HTMLPage):

    def iter_accounts(self):
        return []


class ClientPage(LoggedPage, HTMLPage):
    is_here = "//div[@id='situation']"

    @method
    class iter_accounts(ListElement):
        item_xpath = '//div[@id="situation"]//div[@class="synthese-produit"]'

        class item(ItemElement):
            klass = Account

            obj_currency = u'EUR'
            obj_type = Account.TYPE_REVOLVING_CREDIT
            obj_label = Env('label')
            obj__num = Env('_num')
            obj_id = Env('id')
            obj_balance = Env('balance')
            obj__site = 'oney'

            def parse(self, el):
                self.env['label'] = CleanText('./h3/a')(self) or u'Carte Oney'
                self.env['_num'] = Attr('%s%s%s' % ('//option[contains(text(), "', Field('label')(self).replace('Ma ', ''), '")]'), 'value', default=u'')(self)
                self.env['id'] = Format('%s%s' % (self.page.browser.username, Field('_num')(self)))(self)

                # On the multiple accounts page, decimals are separated with dots, and separated with commas on single account page.
                amount_due = CleanDecimal('./p[@class = "somme-due"]/span[@class = "synthese-montant"]', default=None)(self)
                if amount_due is None:
                    amount_due = CleanDecimal('./div[@id = "total-sommes-dues"]/p[contains(text(), "sommes dues")]/span[@class = "montant"]', replace_dots=True)(self)
                self.env['balance'] = - amount_due


class OperationsPage(LoggedPage, HTMLPage):
    is_here = "//div[@id='releve-reserve-credit'] | //div[@id='operations-recentes'] | //select[@id='periode']"

    @pagination
    @method
    class iter_transactions(ListElement):
        item_xpath = '//table[@class="tableau-releve"]/tbody/tr[not(node()//span[@class="solde-initial"])]'
        flush_at_end = True

        def flush(self):
            # As transactions are unordered on the page, we flush only at end
            # the sorted list of them.
            return sorted_transactions(self.objects.values())

        def store(self, obj):
            # It stores only objects with an ID. To be sure it works, use the
            # uid of transaction as object ID.
            obj.id = obj.unique_id(seen=self.env['seen'])
            return ListElement.store(self, obj)

        class credit(ItemElement):
            klass = Transaction
            obj_type = Transaction.TYPE_CARD
            obj_date = Transaction.Date('./td[1]')
            obj_raw = Transaction.Raw('./td[2]')
            obj_amount = Env('amount')

            def condition(self):
                self.env['amount'] = Transaction.Amount('./td[3]')(self.el)
                return self.env['amount'] > 0

        class debit(ItemElement):
            klass = Transaction
            obj_type = Transaction.TYPE_CARD
            obj_date = Transaction.Date('./td[1]')
            obj_raw = Transaction.Raw('./td[2]')
            obj_amount = Env('amount')

            def condition(self):
                self.env['amount'] = Transaction.Amount('', './td[4]')(self.el)
                return self.env['amount'] < 0

        def next_page(self):
            options = self.page.doc.xpath('//select[@id="periode"]//option[@selected="selected"]/preceding-sibling::option[1]')
            if options:
                data = {
                    'numReleve': options[0].values(),
                    'task': 'Releve',
                    'process': 'Releve',
                    'eventid': 'select',
                    'taskid': '',
                    'hrefid': '',
                    'hrefext': '',
                }
                return requests.Request("POST", self.page.url, data=data)


class CreditHome(LoggedPage, HTMLPage):
    def get_accounts_ids(self):
        ids = []
        for elem in self.doc.xpath('//li[@id="menu-n2-mesproduits"]//a/@onclick'):
            regex_result = re.search(r"afficherDetailCompte\('(\d+)'\)", elem)
            if not regex_result:
                continue
            acc_id = regex_result.group(1)
            if acc_id not in ids:
                ids.append(acc_id)
        return ids

    def get_label(self):
        # 'Ma carte Alinea', 'Mon Prêt Oney', ...
        return CleanText('//div[@class="conteneur"]/h1')(self.doc)

    @method
    class get_loan(ItemElement):
        klass = Account

        obj_type = Account.TYPE_LOAN
        obj__site = 'other'
        obj_label = CleanText('//div[@class="conteneur"]/h1')
        obj_number = obj_id = CleanText('//td[contains(text(), "Mon numéro de compte")]/following-sibling::td', replace=[(' ', '')])
        obj_coming = CleanDecimal.US('//td[strong[contains(text(), "Montant de la")]]/following-sibling::td/strong')


class CreditAccountPage(LoggedPage, HTMLPage):
    @method
    class get_account(ItemElement):
        klass = Account

        obj_type = Account.TYPE_CHECKING
        obj__site = 'other'
        obj_balance = 0
        obj_number = obj_id = CleanText('//tr[td[text()="Mon numéro de compte"]]/td[@class="droite"]', replace=[(' ', '')])
        obj_coming = CleanDecimal('//div[@id="mod-paiementcomptant"]//tr[td[contains(text(),"débité le")]]/td[@class="droite"]', sign=lambda _: -1, default=0)
        obj_currency = Currency('//div[@id="mod-paiementcomptant"]//tr[td[starts-with(normalize-space(text()),"Montant disponible")]]/td[@class="droite"]')


class CreditHistory(LoggedPage, XLSPage):
    # this history doesn't contain the monthly recharges, so the balance isn't consistent with the transactions?
    def build_doc(self, content):
        lines = super(CreditHistory, self).build_doc(content)
        dict_list = list()
        header = [element.strip() for element in lines[0]]
        for line in lines[1:][::-1]:
            dict_list.append(dict(zip(header, line)))
        return dict_list

    @method
    class iter_history(DictElement):
        class item(ItemElement):
            klass = Transaction

            obj_raw = Transaction.Raw(CleanText(Dict("Libellé de l'opération")))

            def obj_amount(self):
                assert not (Dict('Débit')(self) and Dict('Credit')(self)), "cannot have both debit and credit"
                return Decimal(Dict('Credit')(self) or 0) - abs(Decimal(Dict('Débit')(self) or 0))

            obj_date = Date(Dict('Date'), dayfirst=True)


class LastHistoryPage(LoggedPage, PartialHTMLPage):
    def has_transactions(self):
        return not CleanText('//h2[contains(text(), "Vous n\'avez pas effectué d\'opération depuis votre dernier relevé de compte.")]')(self.doc)
