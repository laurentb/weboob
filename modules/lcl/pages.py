# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Romain Bignon, Pierre Mazière
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
import base64
from decimal import Decimal
from logging import error
import math
import random


from weboob.capabilities.bank import Account
from weboob.deprecated.browser import Page, BrowserUnavailable
from weboob.tools.captcha.virtkeyboard import MappedVirtKeyboard, VirtKeyboardError
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


class LCLVirtKeyboard(MappedVirtKeyboard):
    symbols={'0': '9da2724133f2221482013151735f033c',
             '1': '873ab0087447610841ae1332221be37b',
             '2': '93ce6c330393ff5980949d7b6c800f77',
             '3': 'b2d70c69693784e1bf1f0973d81223c0',
             '4': '498c8f5d885611938f94f1c746c32978',
             '5': '359bcd60a9b8565917a7bf34522052c3',
             '6': 'aba912172f21f78cd6da437cfc4cdbd0',
             '7': 'f710190d6b947869879ec02d8e851dfa',
             '8': 'b42cc25e1539a15f767aa7a641f3bfec',
             '9': 'cc60e5894a9d8e12ee0c2c104c1d5490'
            }

    url="/outil/UAUT/Clavier/creationClavier?random="

    color=(255,255,255,255)

    def __init__(self,basepage):
        img=basepage.document.find("//img[@id='idImageClavier']")
        random.seed()
        self.url+="%s"%str(long(math.floor(long(random.random()*1000000000000000000000))))
        MappedVirtKeyboard.__init__(self,basepage.browser.openurl(self.url),
                                    basepage.document,img,self.color,"id")
        self.check_symbols(self.symbols,basepage.browser.responses_dirname)

    def get_symbol_code(self,md5sum):
        code=MappedVirtKeyboard.get_symbol_code(self,md5sum)
        return code[-2:]

    def get_string_code(self,string):
        code=''
        for c in string:
            code+=self.get_symbol_code(self.symbols[c])
        return code


class SkipPage(Page):
    pass


class LoginPage(Page):
    def on_loaded(self):
        try:
            self.browser.select_form(name='form')
        except:
            try:
                self.browser.select_form(predicate=lambda x: x.attrs.get('id','')=='setInfosCGS')
            except:
                return

        self.browser.submit(nologin=True)

    def myXOR(self,value,seed):
        s=''
        for i in xrange(len(value)):
            s+=chr(seed^ord(value[i]))
        return s

    def login(self, login, passwd):
        try:
            vk=LCLVirtKeyboard(self)
        except VirtKeyboardError as err:
            error("Error: %s"%err)
            return False

        password=vk.get_string_code(passwd)

        seed=-1
        str="var aleatoire = "
        for script in self.document.findall("//script"):
            if(script.text is None or len(script.text)==0):
                continue
            offset=script.text.find(str)
            if offset!=-1:
                seed=int(script.text[offset+len(str)+1:offset+len(str)+2])
                break
        if seed==-1:
            error("Variable 'aleatoire' not found")
            return False

        self.browser.select_form(
            predicate=lambda x: x.attrs.get('id','')=='formAuthenticate')
        self.browser.form.set_all_readonly(False)
        self.browser['identifiant'] = login.encode('utf-8')
        self.browser['postClavierXor'] = base64.b64encode(self.myXOR(password,seed))
        try:
            self.browser['identifiantRouting'] = self.browser.IDENTIFIANT_ROUTING
        except AttributeError:
            pass

        try:
            self.browser.submit(nologin=True)
        except BrowserUnavailable:
            # Login is not valid
            return False
        return True

    def is_error(self):
        errors = self.document.xpath(u'//div[@class="erreur" or @class="messError"]')
        return len(errors) > 0


class ContractsPage(Page):
    def on_loaded(self):
        self.select_contract()

    def select_contract(self):
        # XXX We select automatically the default contract in list. We should let user
        # ask what contract he wants to see, or display accounts for all contracts.
        self.browser.select_form(nr=0)
        self.browser.submit(nologin=True)


class AccountsPage(Page):
    def on_loaded(self):
        warn = self.document.xpath('//div[@id="attTxt"]')
        if len(warn) > 0:
            raise BrowserUnavailable(warn[0].text)

    def get_list(self):
        l = []
        ids = set()
        for a in self.document.getiterator('a'):
            link=a.attrib.get('href')
            if link is None:
                continue
            if link.startswith("/outil/UWLM/ListeMouvements"):
                account = Account()
                #by default the website propose the last 7 days or last 45 days but we can force to have the last 55days
                account._link_id=link+"&mode=55"
                account._coming_links = []
                parameters=link.split("?").pop().split("&")
                for parameter in parameters:
                    list=parameter.split("=")
                    value=list.pop()
                    name=list.pop()
                    if name=="agence":
                        account.id=value
                    elif name=="compte":
                        account.id+=value
                    elif name=="nature":
                        # TODO parse this string to get the right Account.TYPE_* to
                        # store in account.type.
                        account._type=value

                if account.id in ids:
                    continue

                ids.add(account.id)
                div = a.getparent().getprevious()
                if not div.text.strip():
                    div = div.find('div')
                account.label=u''+div.text.strip()
                balance = FrenchTransaction.clean_amount(a.text)
                if '-' in balance:
                    balance='-'+balance.replace('-', '')
                account.balance=Decimal(balance)
                account.currency = account.get_currency(a.text)
                self.logger.debug('%s Type: %s' % (account.label, account._type))
                l.append(account)
            if link.startswith('/outil/UWCB/UWCBEncours'):
                if len(l) == 0:
                    self.logger.warning('There is a card account but not any check account')
                    continue

                account = l[-1]

                coming = FrenchTransaction.clean_amount(a.text)
                if '-' in coming:
                    coming = '-'+coming.replace('-', '')
                if not account.coming:
                    account.coming = Decimal('0')
                account.coming += Decimal(coming)
                account._coming_links.append(link)

        return l


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile('^(?P<category>CB)  (?P<text>RETRAIT) DU  (?P<dd>\d+)/(?P<mm>\d+)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^(?P<category>(PRLV|PE)) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_ORDER),
                (re.compile('^(?P<category>CHQ\.) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_CHECK),
                (re.compile('^(?P<category>RELEVE CB) AU (?P<dd>\d+)/(?P<mm>\d+)/(?P<yy>\d+)'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile('^(?P<category>CB) (?P<text>.*) (?P<dd>\d+)/(?P<mm>\d+)/(?P<yy>\d+)'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile('^(?P<category>(PRELEVEMENT|TELEREGLEMENT|TIP)) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_ORDER),
                (re.compile('^(?P<category>(ECHEANCE\s*)?PRET)(?P<text>.*)'),   FrenchTransaction.TYPE_LOAN_PAYMENT),
                (re.compile('^(?P<category>(EVI|VIR(EM(EN)?)?T?)(.PERMANENT)? ((RECU|FAVEUR) TIERS|SEPA RECU)?)( /FRM)?(?P<text>.*)'),
                                                            FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^(?P<category>REMBOURST)(?P<text>.*)'),     FrenchTransaction.TYPE_PAYBACK),
                (re.compile('^(?P<category>COM(MISSIONS?)?)(?P<text>.*)'),   FrenchTransaction.TYPE_BANK),
                (re.compile('^(?P<text>(?P<category>REMUNERATION).*)'),   FrenchTransaction.TYPE_BANK),
                (re.compile('^(?P<text>(?P<category>ABON.*?)\s*.*)'),   FrenchTransaction.TYPE_BANK),
                (re.compile('^(?P<text>(?P<category>RESULTAT .*?)\s*.*)'),   FrenchTransaction.TYPE_BANK),
                (re.compile('^(?P<text>(?P<category>TRAIT\..*?)\s*.*)'),   FrenchTransaction.TYPE_BANK),
                (re.compile('^(?P<category>REM CHQ) (?P<text>.*)'), FrenchTransaction.TYPE_DEPOSIT),
               ]


class AccountHistoryPage(Page):
    def get_table(self):
        tables=self.document.findall("//table[@class='tagTab pyjama']")
        for table in tables:
            # Look for the relevant table in the Pro version
            header=table.getprevious()
            while header is not None and str(header.tag) != 'div':
                header=header.getprevious()
            if header is not None:
                header=header.find("div")
            if header is not None:
                header=header.find("span")

            if header is not None and \
               header.text.strip().startswith("Opérations effectuées".decode('utf-8')):
                return table

            # Look for the relevant table in the Particulier version
            header=table.find("thead").find("tr").find("th[@class='titleTab titleTableft']")
            if header is not None and\
               header.text.strip().startswith("Solde au"):
                return table

    def strip_label(self, s):
        return s

    def get_operations(self):
        table = self.get_table()
        operations = []

        if table is None:
            return operations

        for tr in table.iter('tr'):
            # skip headers and empty rows
            if len(tr.findall("th"))!=0 or\
               len(tr.findall("td"))<=1:
                continue
            mntColumn = 0

            date = None
            raw = None
            credit = ''
            debit = ''
            for td in tr.iter('td'):
                value = td.attrib.get('id')
                if value is None:
                    # if tag has no id nor class, assume it's a label
                    value = td.attrib.get('class', 'opLib')

                if value.startswith("date") or value.endswith('center'):
                    # some transaction are included in a <strong> tag
                    date = u''.join([txt.strip() for txt in td.itertext()])
                elif value.startswith("lib") or value.startswith("opLib"):
                    # misclosed A tag requires to grab text from td
                    tooltip = td.xpath('./div[@class="autoTooltip"]')
                    if len(tooltip) > 0:
                        td.remove(tooltip[0])
                    raw = self.parser.tocleanstring(td)
                elif value.startswith("solde") or value.startswith("mnt") or \
                     value.startswith('debit') or value.startswith('credit'):
                    mntColumn += 1
                    amount = u''.join([txt.strip() for txt in td.itertext()])
                    if amount != "":
                        if value.startswith("soldeDeb") or value.startswith('debit') or mntColumn==1:
                            debit = amount
                        else:
                            credit = amount

            if date is None:
                # skip non-transaction
                continue

            operation = Transaction(len(operations))
            operation.parse(date, raw)
            operation.set_amount(credit, debit)

            if operation.category == 'RELEVE CB':
                # strip that transaction which is detailled in CBListPage.
                continue

            operations.append(operation)
        return operations


class CBHistoryPage(AccountHistoryPage):
    def get_table(self):
        # there is only one table on the page
        try:
            return self.document.findall("//table[@class='tagTab pyjama']")[0]
        except IndexError:
            return None

    def strip_label(self, label):
        # prevent to be considered as a category if there are two spaces.
        return re.sub(r'[ ]+', ' ', label).strip()

    def get_operations(self):
        for tr in AccountHistoryPage.get_operations(self):
            tr.type = tr.TYPE_CARD
            yield tr


class CBListPage(CBHistoryPage):
    def get_cards(self):
        cards = []
        for a in self.document.getiterator('a'):
            link = a.attrib.get('href', '')
            if link.startswith('/outil/UWCB/UWCBEncours') and 'listeOperations' in link:
                cards.append(link)
        return cards
