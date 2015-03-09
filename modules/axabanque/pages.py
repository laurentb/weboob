# -*- coding: utf-8 -*-

# Copyright(C) 2013 Romain Bignon
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
from decimal import Decimal, InvalidOperation
import re
import lxml.html

from weboob.deprecated.browser import Page as _BasePage, BrowserUnavailable, BrokenPageError
from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.captcha.virtkeyboard import MappedVirtKeyboard


class BasePage(_BasePage):
    def get_view_state(self):
        return self.document.xpath('//input[@name="javax.faces.ViewState"]')[0].attrib['value']

    def is_password_expired(self):
        return len(self.document.xpath('//div[@id="popup_client_modifier_code_confidentiel"]'))


class UnavailablePage(BasePage):
    def on_loaded(self):
        raise BrowserUnavailable()


class VirtKeyboard(MappedVirtKeyboard):

    margin = 2, 2, 2, 2

    symbols={'0':'e2df31c137e6c6cb214f92f7d6cd590a',
             '1':'6057c05937af4574ff453956fbbd2e0e',
             '2':'5ea5a38efacd3977f17bbc7af83a1943',
             '3':'560a86b430d2c77e1bd9688efa1b08f9',
             '4':'e6b6b156ea34a8ae9304526e091b2960',
             '5':'914483946ee0e55bcc732fce09a0b7c0',
             '6':'c2382b8f56a0d902e9b399037a9052b5',
             '7':'c5294f8154a1407560222ac894539d30',
             '8':'fa1f25a1d5a674dd7bc0d201413d7cfe',
             '9':'7658424ff8ab127d27e08b7b9b14d331'
            }

    color=(0xFF, 0xFF, 0xFF, 0x0)

    def check_color(self, pixel):
        step = 10
        return abs(pixel[0] - self.color[0]) < step and abs(pixel[1] - self.color[1]) < step and abs(pixel[2] - self.color[2]) < step

    def __init__(self, page):
        key = page.document.getroot().xpath('//input')[0].value
        page.browser.login_key = key
        img = page.document.getroot().xpath('//img')[0]
        img_url = 'https://www.axa.fr/.sendvirtualkeyboard.png?key=' + key
        img_file = page.browser.openurl(img_url)
        MappedVirtKeyboard.__init__(self, img_file, page.document, img, self.color)

        self.check_symbols(self.symbols, page.browser.responses_dirname)

    def get_symbol_code(self,md5sum):
        code = MappedVirtKeyboard.get_symbol_code(self,md5sum)
        return code[-3:-2]

    def get_string_code(self,string):
        code = ''
        for c in string:
            code += self.get_symbol_code(self.symbols[c])
        return code


class LoginPage(BasePage):
    def login(self, login, password):
        document = lxml.html.fromstring(self.document['html'])
        self.document = document.getroottree()

        vk = VirtKeyboard(self)

        args = {'login':        login,
                'password':     vk.get_string_code(password),
                'remeberMe':    'false',
                'key':          self.browser.login_key,
               }

        self.browser.location('https://www.axa.fr/.loginAxa.json', urllib.urlencode(args), no_login=True)

class PostLoginPage(BasePage):
    def redirect(self):
        if 'tokenBanque' not in self.document:
            return False
        url = 'https://www.axabanque.fr/webapp/axabanque/client/sso/connexion?token=%s' % self.document['tokenBanque']
        self.browser.location(url)
        self.browser.location('http://www.axabanque.fr/webapp/axabanque/jsp/panorama.faces')
        return True

class AccountsPage(BasePage):
    ACCOUNT_TYPES = {'courant-titre':      Account.TYPE_CHECKING,
                    }

    def js2args(self, s):
        args = {}
        # For example:
        # noDoubleClic(this);;return oamSubmitForm('idPanorama','idPanorama:tableaux-comptes-courant-titre:0:tableaux-comptes-courant-titre-cartes:0:_idJsp321',null,[['paramCodeProduit','9'],['paramNumContrat','12234'],['paramNumCompte','12345678901'],['paramNumComptePassage','1234567890123456']]);
        for sub in re.findall("\['([^']+)','([^']+)'\]", s):
            args[sub[0]] = sub[1]

        args['idPanorama:_idcl'] = re.search("'(idPanorama:[^']+)'", s).group(1)
        args['idPanorama_SUBMIT'] = 1

        return args

    def get_list(self):
        for table in self.document.getroot().cssselect('div#table-panorama table.table-produit'):
            tds = table.xpath('./tbody/tr')[0].findall('td')
            if len(tds) < 3:
                continue

            boxes = table.xpath('./tbody//tr')
            foot = table.xpath('./tfoot//tr')

            for box in boxes:
                account = Account()

                if len(box.xpath('.//a')) != 0 and 'onclick' in box.xpath('.//a')[0].attrib:
                    args = self.js2args(box.xpath('.//a')[0].attrib['onclick'])
                    account.label =  u'{0} {1}'.format(unicode(table.xpath('./caption')[0].text.strip()), unicode(box.xpath('.//a')[0].text.strip()))
                elif len(foot[0].xpath('.//a')) != 0 and 'onclick' in foot[0].xpath('.//a')[0].attrib:
                    args = self.js2args(foot[0].xpath('.//a')[0].attrib['onclick'])
                    account.label =  unicode(table.xpath('./caption')[0].text.strip())
                else:
                    continue

                self.logger.debug('Args: %r' % args)
                if 'paramNumCompte' not in args:
                    try:
                        label = unicode(table.xpath('./caption')[0].text.strip())
                    except Exception:
                        label = 'Unable to determine'
                    self.logger.warning('Unable to get account ID for %r' % label)
                    continue
                try:
                    account.id = args['paramNumCompte'] + args['paramNumContrat']
                except KeyError:
                    account.id = args['paramNumCompte']
                account_type_str = table.attrib['class'].split(' ')[-1][len('tableaux-comptes-'):]
                account.type = self.ACCOUNT_TYPES.get(account_type_str, Account.TYPE_UNKNOWN)

                currency_title = table.xpath('./thead//th[@class="montant"]')[0].text.strip()
                m = re.match('Montant \((\w+)\)', currency_title)
                if not m:
                    self.logger.warning('Unable to parse currency %r' % currency_title)
                else:
                    account.currency = account.get_currency(m.group(1))

                try:
                    account.balance = Decimal(FrenchTransaction.clean_amount(u''.join([txt.strip() for txt in box.cssselect("td.montant")[0].itertext()])))
                except InvalidOperation:
                    #The account doesn't have a amount
                    pass
                account._args = args
                yield account


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile('^RET(RAIT) DAB (?P<dd>\d{2})/(?P<mm>\d{2}) (?P<text>.*)'),
                                                              FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^(CARTE|CB ETRANGER) (?P<dd>\d{2})/(?P<mm>\d{2}) (?P<text>.*)'),
                                                              FrenchTransaction.TYPE_CARD),
                (re.compile('^(?P<category>VIR(EMEN)?T? (SEPA)?(RECU|FAVEUR)?)( /FRM)?(?P<text>.*)'),
                                                              FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^PRLV (?P<text>.*)( \d+)?$'),    FrenchTransaction.TYPE_ORDER),
                (re.compile('^(CHQ|CHEQUE) .*$'),             FrenchTransaction.TYPE_CHECK),
                (re.compile('^(AGIOS /|FRAIS) (?P<text>.*)'), FrenchTransaction.TYPE_BANK),
                (re.compile('^(CONVENTION \d+ |F )?COTIS(ATION)? (?P<text>.*)'),
                                                              FrenchTransaction.TYPE_BANK),
                (re.compile('^REMISE (?P<text>.*)'),          FrenchTransaction.TYPE_DEPOSIT),
                (re.compile('^(?P<text>.*)( \d+)? QUITTANCE .*'),
                                                              FrenchTransaction.TYPE_ORDER),
                (re.compile('^.* LE (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{2})$'),
                                                              FrenchTransaction.TYPE_UNKNOWN),
               ]


class TransactionsPage(BasePage):
    COL_DATE = 0
    COL_TEXT = 1
    COL_DEBIT = 2
    COL_CREDIT = 3

    def more_history(self):
        link = None
        for a in self.document.xpath('.//a'):
            if a.text is not None and a.text.strip() == 'Sur les 6 derniers mois':
                link = a
                break

        if link is None:
            # this is a check account
            args = {'categorieMouvementSelectionnePagination': 'afficherTout',
                    'nbLigneParPageSelectionneHautPagination': -1,
                    'nbLigneParPageSelectionneBasPagination': -1,
                    'periodeMouvementSelectionneComponent': '',
                    'categorieMouvementSelectionneComponent': '',
                    'nbLigneParPageSelectionneComponent': -1,
                    'idDetail:btnRechercherParNbLigneParPage': '',
                    'idDetail_SUBMIT': 1,
                    'paramNumComptePassage': '',
                    'codeEtablissement': '',
                    'paramNumCodeSousProduit': '',
                    'idDetail:_idcl': '',
                    'idDetail:scroll_banqueHaut': '',
                    'paramNumContrat': '',
                    'paramCodeProduit': '',
                    'paramNumCompte': '',
                    'codeAgence': '',
                    'idDetail:_link_hidden_': '',
                    'paramCodeFamille': '',
                    'javax.faces.ViewState': self.get_view_state(),
                   }
        else:
            # something like a PEA or so
            value = link.attrib['id']
            id = value.split(':')[0]
            args = {'%s:_idcl' % id: value,
                    '%s:_link_hidden_' % id: '',
                    '%s_SUBMIT' % id: 1,
                    'javax.faces.ViewState': self.get_view_state(),
                    'paramNumCompte': '',
                   }

        form = self.document.xpath('//form')[-1]
        self.browser.location(form.attrib['action'], urllib.urlencode(args))

    def get_history(self):
        tables = self.document.xpath('//table[@id="table-detail-operation"]')
        if len(tables) == 0:
            tables = self.document.xpath('//table[@id="table-detail"]')
        if len(tables) == 0:
            tables = self.document.getroot().cssselect('table.table-detail')
        if len(tables) == 0:
            try:
                self.parser.select(self.document.getroot(), 'td.no-result', 1)
            except BrokenPageError:
                raise BrokenPageError('Unable to find table?')
            else:
                return

        for tr in tables[0].xpath('.//tr'):
            tds = tr.findall('td')
            if len(tds) < 4:
                continue

            t = Transaction(0)
            date = u''.join([txt.strip() for txt in tds[self.COL_DATE].itertext()])
            raw = u''.join([txt.strip() for txt in tds[self.COL_TEXT].itertext()])
            debit = u''.join([txt.strip() for txt in tds[self.COL_DEBIT].itertext()])
            credit = u''.join([txt.strip() for txt in tds[self.COL_CREDIT].itertext()])

            t.parse(date, re.sub(r'[ ]+', ' ', raw))
            t.set_amount(credit, debit)

            yield t


class CBTransactionsPage(TransactionsPage):
    COL_CB_CREDIT = 2

    def get_history(self):
        tables = self.document.xpath('//table[@id="idDetail:dataCumulAchat"]')
        transactions =list()

        if len(tables) == 0:
            return transactions
        for tr in tables[0].xpath('.//tr'):
            tds = tr.findall('td')
            if len(tds) < 3:
                continue

            t = Transaction(0)
            date = u''.join([txt.strip() for txt in tds[self.COL_DATE].itertext()])
            raw = u''.join([txt.strip() for txt in tds[self.COL_TEXT].itertext()])
            credit = u''.join([txt.strip() for txt in tds[self.COL_CB_CREDIT].itertext()])
            debit = ""

            t.parse(date, re.sub(r'[ ]+', ' ', raw))
            t.set_amount(credit, debit)
            transactions.append(t)

        for histo in super(CBTransactionsPage, self).get_history():
            transactions.append(histo)

        transactions.sort(key=lambda transaction: transaction.date, reverse=True)
        return iter(transactions)
