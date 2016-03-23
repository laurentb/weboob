# -*- coding: utf-8 -*-

# Copyright(C) 2013      Laurent Bachelier
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

import urllib
from logging import error
import re
from decimal import Decimal
from datetime import datetime

from weboob.deprecated.browser import Page
from weboob.tools.json import json
from weboob.deprecated.mech import ClientForm
from weboob.tools.misc import to_unicode

from weboob.capabilities.bank import Account
from weboob.capabilities.base import NotAvailable
from weboob.tools.capabilities.bank.transactions import FrenchTransaction

from ..captcha import Captcha, TileError


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(r'^CARTE \w+ RETRAIT DAB.* (?P<dd>\d{2})/(?P<mm>\d{2})( (?P<HH>\d+)H(?P<MM>\d+))? (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(r'^CARTE \w+ (?P<dd>\d{2})/(?P<mm>\d{2})( A (?P<HH>\d+)H(?P<MM>\d+))? RETRAIT DAB (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(r'^CARTE \w+ REMBT (?P<dd>\d{2})/(?P<mm>\d{2})( A (?P<HH>\d+)H(?P<MM>\d+))? (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_PAYBACK),
                (re.compile(r'^(?P<category>CARTE) \w+ (?P<dd>\d{2})/(?P<mm>\d{2}) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile(r'^(?P<dd>\d{2})(?P<mm>\d{2})/(?P<text>.*?)/?(-[\d,]+)?$'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile(r'^(?P<category>(COTISATION|PRELEVEMENT|TELEREGLEMENT|TIP)) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_ORDER),
                (re.compile(r'^(\d+ )?VIR (PERM )?POUR: (.*?) (REF: \d+ )?MOTIF: (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_TRANSFER),
                (re.compile(r'^(?P<category>VIR(EMEN)?T? \w+) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_TRANSFER),
                (re.compile(r'^(CHEQUE) (?P<text>.*)'),     FrenchTransaction.TYPE_CHECK),
                (re.compile(r'^(FRAIS) (?P<text>.*)'),      FrenchTransaction.TYPE_BANK),
                (re.compile(r'^(?P<category>ECHEANCEPRET)(?P<text>.*)'),
                                                            FrenchTransaction.TYPE_LOAN_PAYMENT),
                (re.compile(r'^(?P<category>REMISE CHEQUES)(?P<text>.*)'),
                                                            FrenchTransaction.TYPE_DEPOSIT),
                (re.compile(r'^CARTE RETRAIT (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
               ]
    _coming = False


class SGPEPage(Page):
    def get_error(self):
        err = self.document.getroot().cssselect('div.ngo_mire_reco_message') \
            or self.document.getroot().cssselect('#nge_zone_centre .nge_cadre_message_utilisateur') \
            or self.document.xpath(u'//div[contains(text(), "Echec de connexion à l\'espace Entreprises")]') \
            or self.document.xpath(u'//div[contains(@class, "waitAuthJetonMsg")]')
        if err:
            return err[0].text.strip()


class ErrorPage(SGPEPage):
    def get_error(self):
        return SGPEPage.get_error(self) or 'Unknown error'


class LoginPage(SGPEPage):
    def login(self, login, password):
        DOMAIN = self.browser.DOMAIN

        url_login = 'https://' + DOMAIN + '/'

        base_url = 'https://' + DOMAIN
        url = base_url + '//sec/vk/gen_crypto?estSession=0'
        headers = {'Referer': url_login}
        request = self.browser.request_class(url, None, headers)
        infos_data = self.browser.readurl(request)

        infos_data = re.match('^_vkCallback\((.*)\);$', infos_data).group(1)

        infos = json.loads(infos_data.replace("'", '"'))

        url = base_url + '//sec/vk/gen_ui?modeClavier=0&cryptogramme=' + infos["crypto"]

        self.browser.readurl(url)
        img = Captcha(self.browser.openurl(url), infos)

        try:
            img.build_tiles()
        except TileError as err:
            error("Error: %s" % err)
            if err.tile:
                err.tile.display()

        self.browser.select_form(self.browser.LOGIN_FORM)
        self.browser.controls.append(ClientForm.TextControl('text', 'codsec', {'value': ''}))
        self.browser.controls.append(ClientForm.TextControl('text', 'cryptocvcs', {'value': ''}))
        self.browser.controls.append(ClientForm.TextControl('text', 'vk_op', {'value': 'auth'}))
        self.browser.set_all_readonly(False)

        self.browser['user_id'] = login.encode(self.browser.ENCODING)
        self.browser['codsec'] = img.get_codes(password[:6])
        self.browser['cryptocvcs'] = infos["crypto"]
        self.browser.form.action = base_url + '/authent.html'
        self.browser.submit(nologin=True)


class AccountsPage(SGPEPage):
    TYPES = {u'COMPTE COURANT':      Account.TYPE_CHECKING,
             u'COMPTE PERSONNEL':    Account.TYPE_CHECKING,
             u'CPTE PRO':            Account.TYPE_CHECKING,
             u'CPTE PERSO':          Account.TYPE_CHECKING,
             u'CODEVI':              Account.TYPE_SAVINGS,
             u'CEL':                 Account.TYPE_SAVINGS,
             u'Ldd':                 Account.TYPE_SAVINGS,
             u'Livret':              Account.TYPE_SAVINGS,
             u'PEA':                 Account.TYPE_SAVINGS,
             u'PEL':                 Account.TYPE_SAVINGS,
             u'Plan Epargne':        Account.TYPE_SAVINGS,
             u'Prêt':                Account.TYPE_LOAN,
            }

    def get_list(self):
        table = self.parser.select(self.document.getroot(), '#tab-corps', 1)
        for tr in self.parser.select(table, 'tr', 'many'):
            tdname, tdid, tdagency, tdbalance = [td.text_content().strip()
                                                 for td
                                                 in self.parser.select(tr, 'td', 4)]
            # it has empty rows - ignore those without the necessary info
            if all((tdname, tdid, tdbalance)):
                account = Account()
                account.label = to_unicode(tdname)
                for wording, acc_type in self.TYPES.iteritems():
                    if wording in account.label:
                        account.type = acc_type
                account.id = to_unicode(tdid.replace(u'\xa0', '').replace(' ', ''))
                account._agency = to_unicode(tdagency)
                account._is_card = False
                account.balance = Decimal(Transaction.clean_amount(tdbalance))
                account.currency = account.get_currency(tdbalance)
                yield account


class CardsPage(SGPEPage):
    COL_ID = 0
    COL_LABEL = 1
    COL_BALANCE = 2

    def get_list(self):
        rib = None
        currency = None
        for script in self.document.xpath('//script'):
            if script.text is None:
                continue

            m = re.search('var rib = "(\d+)"', script.text)
            if m:
                rib = m.group(1)
            m = re.search("var devise='(\w+)'", script.text)
            if m:
                currency = m.group(1)

            if all((rib, currency)):
                break

        if not all((rib, currency)):
            self.logger.error('Unable to find rib or currency')

        for tr in self.document.xpath('//table[@id="tab-corps"]//tr'):
            tds = tr.findall('td')

            if len(tds) != 3:
                continue

            account = Account()
            account.type = Account.TYPE_CARD
            account.label = self.parser.tocleanstring(tds[self.COL_LABEL])
            if len(account.label) == 0:
                continue

            link = tds[self.COL_ID].xpath('.//a')[0]
            m = re.match(r"changeCarte\('(\d+)','(\d+)','([^']+)'\);.*", link.attrib['onclick'])
            if not m:
                self.logger.error('Unable to parse link %r' % link.attrib['onclick'])
                continue
            account._link_num = m.group(1) #useless
            account._link = m.group(2)
            account.id = m.group(2) + account._link_num
            account._link_date = urllib.quote(m.group(3))
            account._link_rib = rib
            account._link_currency = currency
            account._is_card = True
            tdbalance = self.parser.tocleanstring(tds[self.COL_BALANCE])
            account.balance = - Decimal(Transaction.clean_amount(tdbalance))
            account.currency = account.get_currency(tdbalance)
            yield account


class HistoryPage(SGPEPage):
    def iter_transactions(self, account, basecount):
        table = self.parser.select(self.document.getroot(), '#tab-corps', 1)
        for i, tr in enumerate(self.parser.select(table, 'tr', 'many'), basecount):
            # td colspan=5
            if len(self.parser.select(tr, 'td')) == 1:
                continue
            tddate, tdlabel, tddebit, tdcredit, tdval, tdbal = [td.text_content().strip()
                                                                for td
                                                                in self.parser.select(tr, 'td', 6)]
            tdamount = tddebit or tdcredit
            # not sure it has empty rows like AccountsPage, but check anyway
            if all((tddate, tdlabel, tdamount)):
                t = Transaction()
                t._index = i
                t.set_amount(tdamount)
                date = datetime.strptime(tddate, '%d/%m/%Y')
                val = datetime.strptime(tdval, '%d/%m/%Y')
                # so that first line is separated by parse()
                # also clean up tabs, spaces, etc.
                l1, _, l2 = tdlabel.partition('\n')
                l1 = ' '.join(l1.split())
                l2 = ' '.join(l2.split())
                t.parse(date, l1 + '  ' + l2)
                t.vdate = val
                yield t

    def has_next(self):
        for n in self.parser.select(self.document.getroot(), '#numPageBloc'):
            cur = int(self.parser.select(n, '#numPage', 1).value)
            for end in self.parser.select(n, '.contenu3-lien'):
                return end.text != '/' and int(end.text.replace('/', '')) > cur
        return False


class CardHistoryPage(SGPEPage):
    COL_DATE = 0
    COL_LABEL = 1
    COL_AMOUNT = -1

    def iter_transactions(self):
        table = self.parser.select(self.document.getroot(), '#tab-corps', 1)
        for i, tr in enumerate(self.parser.select(table, 'tr', 'many')):

            tds = tr.findall('td')

            date = self.parser.tocleanstring(tds[self.COL_DATE])
            raw = self.parser.tocleanstring(tds[self.COL_LABEL])
            amount = self.parser.tocleanstring(tds[self.COL_AMOUNT])

            if len(date) == 0:
                continue

            t = Transaction()
            t._index = i
            t.parse(date, raw)
            t.set_amount(amount)
            yield t

    def has_next(self):
        current = None
        total = None
        for script in self.document.xpath('//script'):
            if script.text is None:
                continue

            m = re.search('var pageActive\s+= (\d+)', script.text)
            if m:
                current = int(m.group(1))
            m = re.search("var nombrePage\s+= (\d+)", script.text)
            if m:
                total = int(m.group(1))

        if all((current, total)) and current < total:
            return True

        return False


class OrderPage(Page):
    def get_iban(self, acc_id):
        for acc in self.document['donnees']:
            if acc_id in acc['ibanCompte']:
                return unicode(acc['ibanCompte'])

        return NotAvailable

    def get_error(self):
        # Maybe later we need to implement this
        return None
