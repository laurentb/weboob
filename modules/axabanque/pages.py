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

from weboob.tools.browser import BasePage as _BasePage, BrowserUnavailable, BrokenPageError
from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.captcha.virtkeyboard import MappedVirtKeyboard


__all__ = ['LoginPage', 'AccountsPage', 'TransactionsPage', 'CBTransactionsPage', 'UnavailablePage']


class BasePage(_BasePage):
    def get_view_state(self):
        return self.document.xpath('//input[@name="javax.faces.ViewState"]')[0].attrib['value']


class UnavailablePage(BasePage):
    def on_loaded(self):
        raise BrowserUnavailable()


class VirtKeyboard(MappedVirtKeyboard):
    symbols={'0':'f47e48cfdf3abc6716a6b0aadf8eebe3',
             '1':'3495abaf658dc550e51c5c92ea56b60b',
             '2':'f57e7c70ddffb71d0efcc42f534165ae',
             '3':'bd08ced5162b033175e8cd37516c8258',
             '4':'45893a475208cdfc66cd83abde69b8d8',
             '5':'110008203b716a0de4fdacd7dc7666e6',
             '6':'4e7e8808d8f4eb22f1ee4086cbd02dcb',
             '7':'f92adf323b0b128a48a24b16ca10ec1e',
             '8':'0283c4e25656aed61a39117247f0d3f1',
             '9':'3de7491bba71baa8bed99ef624094af8'
            }

    color=(0x28, 0x41, 0x55)

    def check_color(self, pixel):
        # only dark blue pixels.
        return (pixel[0] < 100 and pixel[1] < 100 and pixel[2] < 200)

    def __init__(self, page):
        img = page.document.find("//img[@usemap='#mapPave']")
        img_file = page.browser.openurl(img.attrib['src'])
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
        vk = VirtKeyboard(self)

        form = self.document.xpath('//form[@name="_idJsp0"]')[0]
        args = {'login':                    login.encode(self.browser.ENCODING),
                'codepasse':                vk.get_string_code(password),
                'motDePasse':               vk.get_string_code(password),
                '_idJsp0_SUBMIT':           1,
                '_idJsp0:_idcl':            '',
                '_idJsp0:_link_hidden_':    '',
               }
        self.browser.location(form.attrib['action'], urllib.urlencode(args), no_login=True)


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
                if not 'paramNumCompte' in args:
                    try:
                        label = unicode(table.xpath('./caption')[0].text.strip())
                    except Exception:
                        label = 'Unable to determine'
                    self.logger.warning('Unable to get account ID for %r' % label)
                    continue

                account.id = args['paramNumCompte'] + args['paramNumContrat']
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
