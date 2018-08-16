# -*- coding: utf-8 -*-

# Copyright(C) 2015      Romain Bignon
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

from weboob.exceptions import BrowserIncorrectPassword
from weboob.browser.pages import LoggedPage, HTMLPage, pagination
from weboob.browser.elements import method, ListElement, ItemElement
from weboob.capabilities.bank import Account
from weboob.capabilities.base import NotAvailable
from weboob.capabilities.profile import Profile
from weboob.browser.filters.standard import CleanText, CleanDecimal, Map, Async, AsyncLoad, Regexp, Join
from weboob.browser.filters.html import Attr, Link
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


class MyCleanText(CleanText):
    @classmethod
    def clean(cls, txt, children=True, newlines=True, normalize='NFC'):
        if not isinstance(txt, basestring):
            txt = u'\n'.join([t.strip() for t in txt.itertext()])

        return txt


class LoginPage(HTMLPage):
    def login(self, username, password):
        form = self.get_form()
        form['identifiant'] = username
        form['motpasse'] = password
        form.submit()


class LoginConfirmPage(HTMLPage):
    def on_load(self):
        error = CleanText('//td[has-class("ColonneLibelle")]')(self.doc)
        if len(error) > 0:
            raise BrowserIncorrectPassword(error)


class AccountsPage(LoggedPage, HTMLPage):
    def get_acc_link(self):
        msg = CleanText('//body[@class="message"]')(self.doc)
        if msg:
            acc_link = Link('//div[@class="Boutons"]/a', 'href')(self.doc)
            return acc_link

    @method
    class iter_accounts(ListElement):
        item_xpath = '//table[has-class("TableBicolore")]//tr[@id and count(td) > 4]'

        class item(ItemElement):
            klass = Account

            def condition(self):
                return CleanDecimal('./td[5]', replace_dots=True, default=NotAvailable)(self) is not NotAvailable

            TYPE = {'COMPTE COURANT ORDINAIRE': Account.TYPE_CHECKING,
                   }

            obj_id = CleanText('./td[1]')
            obj_label = CleanText('./td[2]')
            obj_currency = FrenchTransaction.Currency('./td[4]')
            obj_balance = CleanDecimal('./td[5]', replace_dots=True)
            obj_type = Map(CleanText('./td[3]'), TYPE, default=Account.TYPE_UNKNOWN)
            obj__link = Attr('./td[1]/a', 'href')
            obj__url = Link('./td[last()]/a[img[starts-with(@alt, "RIB")]]', default=None)

            load_iban = Link('./td[last()]/a[img[starts-with(@alt, "RIB")]]', default=None) & AsyncLoad

            def obj_iban(self):
                return Async('iban', Join('', Regexp(CleanText('//td[has-class("ColonneCode")][starts-with(text(), "IBAN")]'), r'\b((?!IBAN)[A-Z0-9]+)\b', nth='*')))(self) or NotAvailable


class RibPage(LoggedPage, HTMLPage):
    def get_profile(self):
        profile = Profile()

        # profile is inside a <td> separated with a simple <br> without <span> or <div>
        profile_txt = MyCleanText('//div[@class="TableauAffichage"]/table/tr[3]/td[1]')(self.doc).split('\n')
        i_name = 0
        profile.name = u''
        # name can be on one, two, (more ?) lines, so we stop when line start by a number, we suppose it's the address number
        while not re.search('^\d', profile_txt[i_name]):
            profile.name += ' ' + profile_txt[i_name]
            i_name += 1

        profile.name = profile.name.strip()
        profile.address = u''
        # address is not always on two lines, so we consider every lines from here to before last are address, (last one is country)
        for i in range(i_name, len(profile_txt)-1):
            profile.address += ' ' + profile_txt[i]

        profile.address = profile.address.strip()
        profile.country = profile_txt[-1]

        profile.name = profile.name.replace('MONSIEUR ', '').replace('MADAME ', '')

        return profile


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(r'^VIR(EMENT)?( SEPA)? (?P<text>.*)'),                      FrenchTransaction.TYPE_TRANSFER),
                (re.compile(r'^PRLV (?P<text>.*)'),                                     FrenchTransaction.TYPE_ORDER),
                (re.compile(r'^(?P<text>.*) CARTE \d+ PAIEMENT CB\s+(?P<dd>\d{2})(?P<mm>\d{2}) ?(.*)$'),
                                                                                       FrenchTransaction.TYPE_CARD),
                (re.compile(r'^RETRAIT DAB (?P<dd>\d{2})(?P<mm>\d{2}) (?P<text>.*) CARTE [\*\d]+'),
                                                                                       FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(r'^CHEQUE( (?P<text>.*))?$'),                               FrenchTransaction.TYPE_CHECK),
                (re.compile(r'^(F )?COTIS\.? (?P<text>.*)'),                            FrenchTransaction.TYPE_BANK),
                (re.compile(r'^(REMISE|REM.CHQ) (?P<text>.*)'),                         FrenchTransaction.TYPE_DEPOSIT),
                (re.compile(r'^(?P<text>.*) CARTE BLEUE'),                              FrenchTransaction.TYPE_CARD),
                (re.compile(r'^PRVL SEPA (?P<text>.*)'),                                FrenchTransaction.TYPE_ORDER),
                (re.compile(r'^(?P<text>(INT. DEBITEURS).*)'),                          FrenchTransaction.TYPE_BANK),
                (re.compile(r'^(?P<text>.*(VIR EMIS).*)'),                              FrenchTransaction.TYPE_TRANSFER),
                (re.compile(r'^(?P<text>.*(\bMOUVEMENT\b).*)'),                         FrenchTransaction.TYPE_TRANSFER),
                (re.compile(r'^(?P<text>.*(ARRETE TRIM.).*)'),                          FrenchTransaction.TYPE_BANK),
                (re.compile(r'^(?P<text>.*(TENUE DE DOSSIE).*)'),                       FrenchTransaction.TYPE_BANK),
                (re.compile(r'^(?P<text>.*(RELEVE LCR ECH).*)'),                        FrenchTransaction.TYPE_ORDER),
                (re.compile(r'^(?P<text>.*(\+ FORT DECOUVERT).*)'),                     FrenchTransaction.TYPE_BANK),
                (re.compile(r'^(?P<text>.*(EXTRANET @THEMI).*)'),                       FrenchTransaction.TYPE_BANK),
                (re.compile(r'^(?P<text>.*(REL CPT DEBITEU).*)'),                       FrenchTransaction.TYPE_ORDER),
                (re.compile(r"^(?P<text>.*(\bAFFRANCHISSEMENT\b).*)"),                  FrenchTransaction.TYPE_BANK),
                (re.compile(r"^(?P<text>.*(REMISE VIREMENTS MAGNE).*)"),                FrenchTransaction.TYPE_TRANSFER),
                (re.compile(r"^(?P<text>.*(\bEFFET\b).*)"),                             FrenchTransaction.TYPE_BANK),
                (re.compile(r"^(?P<text>.*(\bMANIP\.\b).*)"),                           FrenchTransaction.TYPE_BANK),
                (re.compile(r"^(?P<text>.*(INTERETS SUR REMISE PTF).*)"),               FrenchTransaction.TYPE_BANK),
                (re.compile(r"^(?P<text>.*(REMISE ESCOMPTE PTF).*)"),                   FrenchTransaction.TYPE_BANK),
                (re.compile(r"^(?P<text>.*(RETENUE DE GARANTIE).*)"),                   FrenchTransaction.TYPE_BANK),
                (re.compile(r"^(?P<text>.*(RESTITUTION RETENUE GARANTIE).*)"),          FrenchTransaction.TYPE_BANK),
                (re.compile(r"^(?P<text>.*(\bAMENDES\b).*)"),                           FrenchTransaction.TYPE_TRANSFER),
                (re.compile(r"^(?P<text>.*(\bOA\b).*)"),                                FrenchTransaction.TYPE_BANK),
                (re.compile(r"^.* COTIS ANN (?P<text>.*)"),                             FrenchTransaction.TYPE_BANK),
                (re.compile(r"^(?P<text>.*(FORFAIT CENT\.RE).*)"),                      FrenchTransaction.TYPE_BANK),
                (re.compile(r"^(?P<text>.*(ENVOI CB).*)"),                              FrenchTransaction.TYPE_BANK),
                (re.compile(r"^(?P<text>.*(RET\.SDD).*)"),                              FrenchTransaction.TYPE_BANK),
                (re.compile(r"^(?P<text>.*(RETOUR PVL ACD EXPERTISE).*)"),              FrenchTransaction.TYPE_BANK),
                (re.compile(r"^(?P<text>.*(Annulation PAR REJ\/CHQ).*)"),               FrenchTransaction.TYPE_BANK),
                (re.compile(r"^(?P<text>.*(REJET CHEQUE).*)"),                          FrenchTransaction.TYPE_BANK),
                (re.compile(r"^(?P<text>.*(CHQ PAYE INFRAC).*)"),                       FrenchTransaction.TYPE_BANK),
                (re.compile(r"^(?P<text>^(CHQ IRREGULIER).*)"),                         FrenchTransaction.TYPE_BANK),
                (re.compile(r"^(?P<text>.*(ERREUR REMISE C).*)"),                       FrenchTransaction.TYPE_BANK),
                (re.compile(r"^(?P<text>^(\bREMCHQ\b).*)"),                             FrenchTransaction.TYPE_DEPOSIT),
                (re.compile(r"^(?P<text>^(RETOUR PVL).*)"),                             FrenchTransaction.TYPE_TRANSFER),
                (re.compile(r"^(?P<text>.*(\bTRANSFERT\b).*)"),                         FrenchTransaction.TYPE_BANK),
                (re.compile(r"^(?P<text>.*(\bCONFIRMATION\b).*)"),                      FrenchTransaction.TYPE_BANK),
                (re.compile(r"^(?P<text>.*(CAUTION AVEC GAGE).*)"),                     FrenchTransaction.TYPE_BANK),
                (re.compile(r"^(?P<text>.*(\bRAPATRIEMENT\b).*)"),                      FrenchTransaction.TYPE_BANK),
                (re.compile(r"^(?P<text>.*(CHANGE REF).*)"),                            FrenchTransaction.TYPE_BANK),
               ]


class HistoryPage(LoggedPage, HTMLPage):
    @pagination
    @method
    class get_operations(Transaction.TransactionsElement):
        def next_page(self):
            for script in self.page.doc.xpath('//script'):
                m = re.search(r"getCodePagination\('(\d+)','(\d+)','([^']+)'.*", script.text or '', re.MULTILINE)
                if m:
                    cur_page = int(m.group(1))
                    nb_pages = int(m.group(2))
                    baseurl = m.group(3)

                    if cur_page < nb_pages:
                        return baseurl + '&numeroPage=%s&nbrPage=%s' % (cur_page + 1, nb_pages)

        head_xpath = '//div[has-class("TableauBicolore")]/table/tr[not(@id)]/td'
        item_xpath = '//div[has-class("TableauBicolore")]/table/tr[@id and count(td) > 4]'

        col_date = ['Date comptable']
        col_vdate = ['Date de valeur']
        col_raw = [u'Libellé de l\'opération']

        class item(Transaction.TransactionElement):
            pass
