# -*- coding: utf-8 -*-

# Copyright(C) 2012 Romain Bignon
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
import ast
import re, requests

from weboob.browser.pages import HTMLPage, LoggedPage, pagination
from weboob.browser.elements import method, TableElement, ItemElement
from weboob.browser.filters.standard import Env, CleanText, CleanDecimal, Field, Regexp
from weboob.browser.filters.html import Attr, Link
from weboob.browser.filters.javascript import JSVar
from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.capabilities.base import NotAvailable


class LoginPage(HTMLPage):
    def login(self, login, passwd):
        tab = re.search(r'tab = (\[[\d,\s]*\])', self.content).group(1)
        number_list = ast.literal_eval(tab)
        key_map = {}
        for i, number in enumerate(number_list):
            if number < 10:
                key_map[number] = chr(ord('A') + i)
        pass_string = ''.join(key_map[int(n)] for n in passwd)
        form = self.get_form(name='loginForm')
        form['username'] = login
        form['password'] = pass_string
        form.submit()


class AccountsPage(LoggedPage, HTMLPage):
    ACCOUNT_TYPES = {u'Solde des comptes bancaires - Groupama Banque':  Account.TYPE_CHECKING,
                     u'Solde des comptes bancaires':                    Account.TYPE_CHECKING,
                     u'Epargne bancaire constituée - Groupama Banque':  Account.TYPE_SAVINGS,
                     u'Epargne bancaire constituée':                    Account.TYPE_CHECKING,
                     u'Mes crédits':                                    Account.TYPE_LOAN,
                     u'Assurance Vie':                                  Account.TYPE_LIFE_INSURANCE}

    @method
    class get_list(TableElement):
        item_xpath = "//div[@class='finance']/form/table[@class='ecli']/tr[td]"
        head_xpath = "//div[@class='finance']/form/table[@class='ecli']/tr[@class='entete']/th"

        class item(ItemElement):
            klass = Account

            def obj_label(self):
                return CleanText('.//td[1]', replace=[(u'\u2022', u'')])(self).lstrip()

            def obj_number(self):
                return CleanText().filter(re.findall('(\d+)', Field('label')(self))).replace(u' ', u'')

            def obj_type(self):
                return self.page.ACCOUNT_TYPES.get(CleanText('.//parent::table/tr[1]/th[1]')(self), Account.TYPE_UNKNOWN)

            def obj_balance(self):
                balance = CleanDecimal('./td[3]', replace_dots=True, default=NotAvailable)(self)
                return -abs(balance) if Field('type')(self) == Account.TYPE_LOAN else balance

            obj_currency = u"EUR"
            obj_id = Regexp(Field('label'), u'N° (\w+)')

            def obj__link(self):
                if Field('type')(self) is not Account.TYPE_LIFE_INSURANCE:
                    m = re.search(r"javascript:submitForm\(([\w_]+),'([^']+)'\);", Attr('.//a', 'onclick')(self))

                    return m.group(2) if m else None
                else:
                    return Link('.//a')(self)

    def refresh_link(self, account):
        if account.type is not Account.TYPE_LIFE_INSURANCE:
            m = re.search(r"javascript:submitForm\(([\w_]+),'([^']+)'\);", Attr('.//a[contains(text(), "%s")]' % account.id, 'onclick')(self.doc))
            account._link =  m.group(2) if m else None


class AccountDetailsPage(LoggedPage, HTMLPage):
    def get_rivage(self):
        if Attr('//iframe[@id="frame1"]', 'src', default=NotAvailable)(self.doc) is NotAvailable:
            return None
        return {'link': 'https://secure-rivage.groupama.fr/contratVie.rivage.syntheseContratEparUc.gsi', \
                'data': {'gfr_idFMC': Attr('//input[@name="gfr_idFMC"]', 'value')(self.doc),
                         'gfr_idCaisse': Attr('//input[@name="gfr_idCaisse"]', 'value')(self.doc),
                         'gfr_idGRC': Attr('//input[@name="gfr_idGRC"]', 'value')(self.doc),
                         'gfr_mailperso': Attr('//input[@name="gfr_mailperso"]', 'value')(self.doc),
                         'gfr_optin': Attr('//input[@name="gfr_optin"]', 'value')(self.doc),
                         'gfr_pgRetourGfr': Attr('//input[@name="gfr_pgRetourGfr"]', 'value')(self.doc),
                         'gfr_nom': Attr('//input[@name="gfr_nom"]', 'value')(self.doc),
                         'gfr_prenom': Attr('//input[@name="gfr_prenom"]', 'value')(self.doc),
                         'gfr_civilite': Attr('//input[@name="gfr_civilite"]', 'value')(self.doc),
                         'gfr_cgu': 1,
                         'gfr_emailAgent': Attr('//input[@name="gfr_emailAgent"]', 'value')(self.doc),
                         'gfr_numeroContrat': JSVar(CleanText('//script'), var='numContrat')(self.doc),
                         'gfr_data': JSVar(CleanText('//script'), var='pCryptage')(self.doc),
                         'gfr_adrSite': 'https://espaceclient.groupama.fr'
                        }
        }

    def fill_rivage_account_details(self, account):
        account.balance = CleanDecimal(u'//p[contains(., "Épargne constituée") and contains(., "€")]/span')(self.doc)

    def fill_account_details(self, account):
        account.balance = CleanDecimal(u'//p[contains(., "épargne") and contains(., "€")]', replace_dots=True)(self.doc)


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile('^Facture (?P<dd>\d{2})/(?P<mm>\d{2})-(?P<text>.*) carte .*'),
                                                                FrenchTransaction.TYPE_CARD),
                (re.compile(u'^(Prlv( de)?|Ech(éance|\.)) (?P<text>.*)'),
                                                                FrenchTransaction.TYPE_ORDER),
                (re.compile('^(Vir|VIR)( de)? (?P<text>.*)'),
                                                                FrenchTransaction.TYPE_TRANSFER),
                (re.compile(u'^CHEQUE.*? (N° \w+)?$'),          FrenchTransaction.TYPE_CHECK),
                (re.compile('^Cotis(ation)? (?P<text>.*)'),
                                                                FrenchTransaction.TYPE_BANK),
                (re.compile('(?P<text>Int .*)'),                FrenchTransaction.TYPE_BANK),
               ]


class TransactionsPage(LoggedPage, HTMLPage):
    @pagination
    @method
    class get_history(Transaction.TransactionsElement):
        head_xpath = '//table[@id="releve_operation"]//tr/th'
        item_xpath = '//table[@id="releve_operation"]//tr'

        col_date =       [u'Date opé', 'Date', u'Date d\'opé', u'Date opération']
        col_vdate =      [u'Date valeur']
        col_credit =     [u'Crédit', u'Montant', u'Valeur']
        col_debit =      [u'Débit']

        def next_page(self):
            url = Attr('//a[contains(text(), "Page suivante")]', 'onclick', default=None)(self)
            if url:
                m = re.search('\'([^\']+).*([\d]+)', url)
                return requests.Request("POST", m.group(1), data={'numCompte': Env('accid')(self), \
                                        'vue': "ReleveOperations", 'tri': "DateOperation", 'sens': \
                                        "DESC", 'page': m.group(2), 'nb_element': "25"})

        class item(Transaction.TransactionElement):
            def condition(self):
                return len(self.el.xpath('./td')) > 3

    def get_coming_link(self):
        try:
            a = self.doc.getroot().cssselect('div#sous_nav ul li a.bt_sans_off')[0]
        except IndexError:
            return None
        return re.sub('[ \t\r\n]+', '', a.attrib['href'])

    def fill_account_iban(self, account):
        account.iban = CleanText('(.//font[b[contains(text(), "IBAN")]])[1]', replace=[(' ', '')])(self.doc)[5:]

    def get_iban_link(self):
        onclick = Attr('.//a[@class="rib"]', 'onclick', default=None)(self.doc)
        if onclick:
            m = re.search(r"envoyer\('(\d+)','(.*)'\);", onclick)
            return '%s?paramNumCpt=%s' % (m.group(2), m.group(1))
