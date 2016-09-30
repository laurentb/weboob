# -*- coding: utf-8 -*-

# Copyright(C) 2013-2015  Romain Bignon
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

from datetime import date as ddate
from decimal import Decimal
from urlparse import urlparse
import re

from weboob.capabilities import NotAvailable
from weboob.capabilities.bank import Account, Investment
from weboob.deprecated.browser import Page, BrokenPageError, BrowserIncorrectPassword
from weboob.tools.capabilities.bank.transactions import FrenchTransaction as Transaction
from weboob.tools.date import parse_french_date, LinearDateGuesser
from weboob.browser.filters.standard import Date


class BasePage(Page):
    def on_loaded(self):
        self.get_current()

    def get_current(self):
        try:
            current_elem = self.document.xpath('//div[@id="libPerimetre_2"]/span[@class="textePerimetre_2"]')[0]
        except IndexError:
            self.logger.debug('Can\'t update current perimeter on this page (%s).', type(self).__name__)
            return False
        self.browser.current_perimeter = re.search('(.*)$', self.parser.tocleanstring(current_elem)).group(1).lower()
        return True

    def get_error(self):
        try:
            error = self.document.xpath('//h1[@class="h1-erreur"]')[0]
            self.logger.error('Error detected: %s', error.text_content().strip())
            return error
        except IndexError:
            return None


class HomePage(BasePage):
    def get_post_url(self):
        for script in self.document.xpath('//script'):
            text = script.text
            if text is None:
                continue

            m = re.search(r'var chemin = "([^"]+)"', text, re.MULTILINE)
            if m:
                return m.group(1)

        return None

    def go_to_auth(self):
        self.browser.select_form('bamaccess')
        self.browser.submit(no_login=True)


class LoginPage(BasePage):
    def on_loaded(self):
        if self.document.xpath('//font[@class="taille2"]'):
            raise BrowserIncorrectPassword()

    def login(self, username, password):
        password = password[:6]
        imgmap = {}
        for td in self.document.xpath('//table[@id="pave-saisie-code"]/tr/td'):
            a = td.find('a')
            num = a.text.strip()
            if num.isdigit():
                imgmap[num] = int(a.attrib['tabindex']) - 1

        self.browser.select_form(name='formulaire')
        self.browser.set_all_readonly(False)
        if self.browser.new_login:
            self.browser['CCPTE'] = username

        self.browser['CCCRYC'] = ','.join(['%02d' % imgmap[c] for c in password])
        self.browser['CCCRYC2'] = '0' * len(password)
        self.browser.submit(nologin=True)

    def get_result_url(self):
        return self.parser.tocleanstring(self.document.getroot())

    def get_accounts_url(self):
        for script in self.document.xpath('//script'):
            text = script.text
            if text is None:
                continue
            m = re.search(r'idSessionSag = "([^"]+)"', script.text)
            if m:
                idSessionSag = m.group(1)
        return '%s%s%s%s' % (self.url, '?sessionSAG=', idSessionSag, '&stbpg=pagePU&actCrt=Synthcomptes&stbzn=btn&act=Synthcomptes')

class UselessPage(BasePage):
    pass


class LoginErrorPage(BasePage):
    pass


class FirstVisitPage(BasePage):
    def on_loaded(self):
        raise BrowserIncorrectPassword(u'Veuillez vous connecter au site du Crédit Agricole pour valider vos données personnelles, et réessayer ensuite.')


class _AccountsPage(BasePage):
    COL_LABEL    = 0
    COL_ID       = 2
    COL_VALUE    = 4
    COL_CURRENCY = 5

    NB_COLS = 7

    TYPES = {u'CCHQ':       Account.TYPE_CHECKING, # par
             u'CCOU':       Account.TYPE_CHECKING, # pro
             u'DAV PEA':    Account.TYPE_CHECKING,
             u'LIV A':      Account.TYPE_SAVINGS,
             u'LDD':        Account.TYPE_SAVINGS,
             u'PEL':        Account.TYPE_SAVINGS,
             u'CEL':        Account.TYPE_SAVINGS,
             u'CODEBIS':    Account.TYPE_SAVINGS,
             u'LJMO':       Account.TYPE_SAVINGS,
             u'CSL':        Account.TYPE_SAVINGS,
             u'LEP':        Account.TYPE_SAVINGS,
             u'TIWI':       Account.TYPE_SAVINGS,
             u'CSL LSO':    Account.TYPE_SAVINGS,
             u'CSL CSP':    Account.TYPE_SAVINGS,
             u'ESPE INTEG': Account.TYPE_SAVINGS,
             u'DAV TIGERE': Account.TYPE_SAVINGS,
             u'CPTEXCPRO':  Account.TYPE_SAVINGS,
             u'PRET PERSO': Account.TYPE_LOAN,
             u'P. HABITAT': Account.TYPE_LOAN,
             u'PRET 0%':    Account.TYPE_LOAN,
             u'INV PRO':    Account.TYPE_LOAN,
             u'PEA':        Account.TYPE_MARKET,
             u'CPS':        Account.TYPE_MARKET,
             u'TITR':       Account.TYPE_MARKET,
             u'TITR CTD':   Account.TYPE_MARKET,
             u'réserves de crédit':     Account.TYPE_CHECKING,
             u'prêts personnels':       Account.TYPE_LOAN,
             u'crédits immobiliers':    Account.TYPE_LOAN,
             u'épargne disponible':     Account.TYPE_SAVINGS,
             u'épargne à terme':        Account.TYPE_DEPOSIT,
             u'épargne boursière':      Account.TYPE_MARKET,
             u'assurance vie et capitalisation': Account.TYPE_LIFE_INSURANCE,

            }

    def get_list(self):
        account_type = Account.TYPE_UNKNOWN

        for tr in self.document.xpath('//table[@class="ca-table"]/tr'):
            try:
                title = tr.xpath('.//h3/text()')[0].lower().strip()
            except IndexError:
                pass
            else:
                account_type = self.TYPES.get(title, Account.TYPE_UNKNOWN)

            if not tr.attrib.get('class', '').startswith('colcelligne'):
                continue

            cols = tr.findall('td')
            if not cols or len(cols) < self.NB_COLS:
                continue

            account = Account()
            account.id = self.parser.tocleanstring(cols[self.COL_ID])
            account.label = self.parser.tocleanstring(cols[self.COL_LABEL])
            account.type = self.TYPES.get(account.label, Account.TYPE_UNKNOWN) or account_type
            balance = self.parser.tocleanstring(cols[self.COL_VALUE])
            # we have to ignore those accounts, because using NotAvailable
            # makes boobank and probably many others crash
            if balance in ('indisponible', ''):
                continue
            account.balance = Decimal(Transaction.clean_amount(balance))
            account.currency = account.get_currency(self.parser.tocleanstring(cols[self.COL_CURRENCY]))
            account._link = None

            self.set_link(account, cols)

            account._perimeter = self.browser.current_perimeter
            yield account

        # Checking pagination
        next_link = self.document.xpath('//a[@class="btnsuiteliste"]/@href')
        if next_link:
            self.browser.location(next_link[0])
            for account in self.browser.page.get_list():
                yield account

    def set_link(self, account, cols):
        raise NotImplementedError()

    def cards_idelco_or_link(self, account_idelco=None):
        # Use a set because it is possible to see several times the same link.
        idelcos = set()
        for line in self.document.xpath('//table[@class="ca-table"]/tr[@class="ligne-connexe"]'):
            try:
                link = line.xpath('.//a/@href')[0]
            except IndexError:
                pass
            else:
                if not link.startswith('javascript:'):
                    if account_idelco and 'IDELCO=%s&' % account_idelco in link:
                        return link
                    m = re.search('IDELCO=(\d+)&', link)
                    if m:
                        idelcos.add(m.group(1))
        return idelcos

    def check_perimeters(self):
        return len(self.document.xpath('//a[@title="Espace Autres Comptes"]'))

class PerimeterPage(BasePage):
    def check_multiple_perimeters(self):
        self.browser.perimeters = list()
        self.get_current()
        if self.browser.current_perimeter is None:
            return
        self.browser.perimeters.append(self.browser.current_perimeter)
        multiple = self.document.xpath(u'//p[span/a[contains(text(), "Accès")]]')
        if not multiple:
            if not len(self.document.xpath(u'//div[contains(text(), "Périmètre en cours de chargement. Merci de patienter quelques secondes.")]')):
                self.logger.debug('Possible error on this page.')
            # We change perimeter in this case to add the second one.
            self.browser.location(self.browser.chg_perimeter_url.format(self.browser.sag), no_login=True)
            if self.browser.page.get_error() is not None:
                self.browser.broken_perimeters.append('the other perimeter is broken')
                self.browser.login()
        else:
            for table in self.document.xpath('//table[@class]'):
                space = ' '.join(table.find('caption').text.lower().split())
                for perim in table.xpath('.//label'):
                    self.browser.perimeters.append(u'%s : %s' % (space, ' '.join(perim.text.lower().split())))

    def get_perimeter_link(self, perimeter):
        caption = perimeter.split(' : ')[0].title()
        perim = perimeter.split(' : ')[1]
        for table in self.document.xpath('//table[@class and caption[contains(text(), "%s")]]' % caption):
            for p in table.xpath(u'.//p[span/a[contains(text(), "Accès")]]'):
                if perim in ' '.join(p.find('label').text.lower().split()):
                    link = p.xpath('./span/a')[0].attrib['href']
                    return link


class ChgPerimeterPage(PerimeterPage):
    def on_loaded(self):
        if self.get_error() is not None:
            self.logger.debug('Error on ChgPerimeterPage')
            return
        self.get_current()
        if not self.browser.current_perimeter.lower() in [' '.join(p.lower().split()) for p in self.browser.perimeters]:
            assert len(self.browser.perimeters) == 1
            self.browser.perimeters.append(self.browser.current_perimeter)


class CardsPage(BasePage):
    def get_list(self):
        TABLE_XPATH = '//table[caption[@class="caption tdb-cartes-caption" or @class="ca-table caption"]]'

        cards_tables = self.document.xpath(TABLE_XPATH)

        currency = self.document.xpath('//table/caption//span/text()[starts-with(.,"Montants en ")]')[0].replace("Montants en ", "") or None
        if cards_tables:
            self.logger.debug('There are several cards')
            xpaths = {
                '_id': './caption/span[@class="tdb-cartes-num"]',
                'label1': './caption/span[contains(@class, "tdb-cartes-carte")]',
                'label2': './caption/span[@class="tdb-cartes-prop"]',
                'balance': './/tr/td[@class="cel-num"]',
                'currency': '//table/caption//span/text()[starts-with(.,"Montants en ")]',
                'link': './/tr//a/@href[contains(., "fwkaction=Detail")]',
            }
        else:
            self.logger.debug('There is only one card')
            xpaths = {
                '_id': './/tr/td[@class="cel-texte"]',
                'label1': './/tr[@class="ligne-impaire ligne-bleu"]/th',
                'label2': './caption/span[@class="tdb-cartes-prop"]/b',
                'balance': './/tr[last()-1]/td[@class="cel-num"] | .//tr[last()-2]/td[@class="cel-num"]',
                'currency': '//table/caption//span/text()[starts-with(.,"Montants en ")]',
            }
            TABLE_XPATH = '(//table[@class="ca-table"])[1]'
            cards_tables = self.document.xpath(TABLE_XPATH)


        for table in cards_tables:
            get = lambda name: self.parser.tocleanstring(table.xpath(xpaths[name])[0])

            account = Account()
            account.type = account.TYPE_CARD
            account.number = ''.join(get('_id').split()[1:])
            # account.number might be the same for two different cards ..
            account.id = '%s%s' % (account.number, get('label2').replace(' ', ''))
            account._id = ' '.join(get('_id').split()[1:])
            account.label = '%s - %s' % (get('label1'),
                                         re.sub('\s*-\s*$', '', get('label2')))
            try:
                account.balance = Decimal(Transaction.clean_amount(table.xpath(xpaths['balance'])[-1].text))
                account.currency = account.get_currency(self.document
                        .xpath(xpaths['currency'])[0].replace("Montants en ", ""))
                if not account.currency and currency:
                    account.currency = Account.get_currency(currency)
            except IndexError:
                account.balance = Decimal('0.0')

            if 'link' in xpaths:
                try:
                    account._link = table.xpath(xpaths['link'])[-1]
                except IndexError:
                    account._link = None
                else:
                    account._link = re.sub('[\n\r\t]+', '', account._link)
            else:
                account._link = self.url
            account._idelco = re.search('IDELCO=(\d+)&', self.url).group(1)
            account._perimeter = self.browser.current_perimeter
            yield account

    def get_next_url(self):
        links = self.document.xpath('//font[@class="btnsuiteliste"]')
        if len(links) < 1:
            return None

        a = links[-1].find('a')
        if a.attrib.get('class', '') == 'liennavigationcorpspage':
            return a.attrib['href']

        return None

    def get_history(self, date_guesser, state=None):
        seen = set()
        lines = self.document.xpath('(//table[@class="ca-table"])[2]/tr')
        debit_date = None
        for i, line in enumerate(lines):
            is_balance = line.xpath('./td/@class="cel-texte cel-neg"')

            # It is possible to have three or four columns.
            cols = [self.parser.tocleanstring(td) for td in line.xpath('./td')]
            date = cols[0]
            label = cols[1]
            amount = cols[-1]

            t = Transaction()
            t.set_amount(amount)
            t.label = t.raw = label

            if is_balance:
                m = re.search('(\d+ [^ ]+ \d+)', label)
                if not m:
                    raise BrokenPageError('Unable to read card balance in history: %r' % label)
                if state is None:
                    debit_date = parse_french_date(m.group(1))
                else:
                    debit_date = state

                # Skip the first line because it is balance
                if i == 0:
                    continue

                t.date = t.rdate = debit_date

                # Consider the second one as a positive amount to reset balance to 0.
                t.amount = -t.amount
                state = t.date
            else:
                day, month = map(int, date.split('/', 1))
                t.rdate = date_guesser.guess_date(day, month)
                t.date = debit_date

            t.type = t.TYPE_CARD
            try:
                t.id = t.unique_id(seen)
            except UnicodeEncodeError:
                self.logger.debug(t)
                self.logger.debug(t.label)
                raise

            yield state, t

    def is_on_right_detail(self, account):
        return len(self.document.xpath(u'//h1[contains(text(), "Cartes - détail")]')) and\
               len(self.document.xpath(u'//td[contains(text(), "%s")] | //td[contains(text(), "%s")] ' % (account.number, account._id)))


class AccountsPage(_AccountsPage):
    def set_link(self, account, cols):
        a = cols[0].find('a')
        if a is not None:
            account._link = a.attrib['href'].replace(' ', '%20')
            page = self.browser.get_page(self.browser.openurl(account._link))
            account._link = re.sub('sessionSAG=[^&]+', 'sessionSAG={0}', account._link)
            url = page.get_iban_url()
            if url:
                page = self.browser.get_page(self.browser.openurl(url))
                account.iban = page.get_iban()


class LoansPage(_AccountsPage):
    COL_ID = 1

    NB_COLS = 6

    def set_link(self, account, cols):
        account.balance = -abs(account.balance)


class SavingsPage(_AccountsPage):
    COL_ID = 1

    def set_link(self, account, cols):
        origin = urlparse(self.url)
        if not account._link:
            a = cols[0].xpath('descendant::a[contains(@href, "CATITRES")]')
            # Sometimes there is no link.
            if a or account.type == Account.TYPE_MARKET:
                url = 'https://%s/stb/entreeBam?sessionSAG=%%s&stbpg=pagePU&site=CATITRES&typeaction=reroutage_aller'
                account._link = url % origin.netloc

            a = cols[0].xpath("descendant::a[contains(@href, \"'PREDICA','CONTRAT'\")]")
            if a:
                account.type = Account.TYPE_LIFE_INSURANCE
                url = 'https://%s/stb/entreeBam?sessionSAG=%%s&stbpg=pagePU&site=PREDICA&' \
                      'typeaction=reroutage_aller&sdt=CONTRAT&parampartenaire=%s'
                account._link = url % (origin.netloc, account.id)
            a = cols[0].xpath('descendant::a[not(contains(@href, "javascript"))]')
            if len(a) == 1 and not account._link:
                account._link = a[0].attrib['href'].replace(' ', '%20')
                account._link = re.sub('sessionSAG=[^&]+', 'sessionSAG={0}', account._link)
            a = cols[0].xpath('descendant::a[(contains(@href, "javascript"))]')
            # This aims to handle bgpi-gestionprivee.
            if len(a) == 1 and not account._link:
                m = re.findall("'([^']*)'", a[0].attrib['href'])
                if len(m) == 3:
                    url = 'https://%s/stb/entreeBam?sessionSAG=%%s&stbpg=pagePU&typeaction=reroutage_aller&site=%s&sdt=%s&parampartenaire=%s'
                    account._link = url % (origin.netloc, m[0], m[1], m[2])


class TransactionsPage(BasePage):
    def get_iban_url(self):
        for link in self.document.xpath('//a[contains(text(), "RIB")] | //a[contains(text(), "IBAN")]'):
            m = re.search("\('([^']+)'", link.get('href', ''))
            if m:
                return m.group(1)

        return None

    def get_iban(self):
        s = ''
        for font in self.document.xpath('(//td[font/b/text()="IBAN"])[1]/table//font'):
            s += self.parser.tocleanstring(font)
        return s

    def get_next_url(self):
        links = self.document.xpath('//span[@class="pager"]/a[@class="liennavigationcorpspage"]')
        if len(links) < 1:
            return None

        img = links[-1].find('img')
        if img.attrib.get('alt', '') == 'Page suivante':
            return links[-1].attrib['href']

        return None

    COL_DATE  = 0
    COL_TEXT  = 1
    COL_DEBIT = None
    COL_CREDIT = -1

    TYPES = {'Paiement Par Carte':          Transaction.TYPE_CARD,
             'Remise Carte':                Transaction.TYPE_CARD,
             'Retrait Au Distributeur':     Transaction.TYPE_WITHDRAWAL,
             'Frais':                       Transaction.TYPE_BANK,
             'Cotisation':                  Transaction.TYPE_BANK,
             'Virement Emis':               Transaction.TYPE_TRANSFER,
             'Virement':                    Transaction.TYPE_TRANSFER,
             'Cheque Emis':                 Transaction.TYPE_CHECK,
             'Remise De Cheque':            Transaction.TYPE_DEPOSIT,
             'Prelevement':                 Transaction.TYPE_ORDER,
             'Prelevt':                     Transaction.TYPE_ORDER,
             'Prelevmnt':                   Transaction.TYPE_ORDER,
             'Remboursement De Pret':       Transaction.TYPE_LOAN_PAYMENT,
            }

    def get_history(self, date_guesser):
        trs = self.document.xpath('//table[@class="ca-table" and @summary]//tr')
        if trs:
            self.COL_TEXT += 1
        else:
            trs = self.document.xpath('//table[@class="ca-table"]//tr')
        for tr in trs:
            parent = tr.getparent()
            while parent is not None and parent.tag != 'table':
                parent = parent.getparent()

            if parent.attrib.get('class', '') != 'ca-table':
                continue

            if tr.attrib.get('class', '') == 'tr-thead':
                heads = tr.findall('th')
                for i, head in enumerate(heads):
                    key = self.parser.tocleanstring(head)
                    if key == u'Débit':
                        self.COL_DEBIT = i - len(heads)
                    if key == u'Crédit':
                        self.COL_CREDIT = i - len(heads)
                    if key == u'Libellé':
                        self.COL_TEXT = i

            if not tr.attrib.get('class', '').startswith('ligne-'):
                continue

            cols = tr.findall('td')

            # On loan accounts, there is a ca-table with a summary. Skip it.
            if tr.find('th') is not None or len(cols) < 3:
                continue

            # On PEL, skip summary.
            if len(cols[0].findall('span')) == 6:
                continue

            t = Transaction()

            col_text = cols[self.COL_TEXT]
            if len(col_text.xpath('.//br')) == 0:
                col_text = cols[self.COL_TEXT+1]

            raw = self.parser.tocleanstring(col_text)
            date = self.parser.tocleanstring(cols[self.COL_DATE])
            credit = self.parser.tocleanstring(cols[self.COL_CREDIT])
            if self.COL_DEBIT is not None:
                debit =  self.parser.tocleanstring(cols[self.COL_DEBIT])
            else:
                debit = ''

            if date.count('/') == 1:
                day, month = map(int, date.split('/', 1))
                t.date = date_guesser.guess_date(day, month)
            elif date.count('/') == 2:
                t.date = Date(dayfirst=True).filter(date)
            t.rdate = t.date
            t.raw = raw

            # On some accounts' history page, there is a <font> tag in columns.
            if col_text.find('font') is not None:
                col_text = col_text.find('font')

            t.category = unicode(col_text.text.strip())
            t.label = re.sub('(.*)  (.*)', r'\2', t.category).strip()

            sub_label = col_text.find('br').tail
            if sub_label is not None and (len(t.label) < 3 or t.label == t.category or len(re.findall('[^\w\s]', sub_label))/float(len(sub_label)) < len(re.findall('\d', t.label))/float(len(t.label))):
                t.label = unicode(sub_label.strip())
            # Sometimes, the category contains the label, even if there is another line with it again.
            t.category = re.sub('(.*)  .*', r'\1', t.category).strip()

            t.type = self.TYPES.get(t.category, t.TYPE_UNKNOWN)

            # Parse operation date in label (for card transactions for example)
            m = re.match('(?P<text>.*) (?P<dd>[0-3]\d)/(?P<mm>[0-1]\d)$', t.label)
            if not m:
                m = re.match('^(?P<dd>[0-3]\d)/(?P<mm>[0-1]\d) (?P<text>.*)$', t.label)
            if m:
                if t.type in (t.TYPE_CARD, t.TYPE_WITHDRAWAL):
                    t.rdate = date_guesser.guess_date(int(m.groupdict()['dd']), int(m.groupdict()['mm']), change_current_date=False)
                t.label = m.groupdict()['text'].strip()

            # Strip city or other useless information from label.
            t.label = re.sub('(.*)  .*', r'\1', t.label).strip()
            t.set_amount(credit, debit)
            yield t



class MarketPage(BasePage):
    COL_ID = 1
    COL_QUANTITY = 2
    COL_UNITVALUE = 3
    COL_VALUATION = 4
    COL_UNITPRICE = 5
    COL_DIFF = 6

    def iter_investment(self):
        for line in self.document.xpath('//table[contains(@class, "ca-data-table")]/descendant::tr[count(td)>=7]'):
            for sub in line.xpath('./td[@class="info-produit"]'):
                sub.drop_tree()
            cells = line.findall('td')

            if cells[self.COL_ID].find('div/a') is None:
                continue
            inv = Investment()
            inv.label = unicode(cells[self.COL_ID].find('div/a').text.strip())
            inv.code = cells[self.COL_ID].find('div/br').tail.strip().split(' ')[0].split(u'\xa0')[0].split(u'\xc2\xa0')[0]
            inv.quantity = self.parse_decimal(cells[self.COL_QUANTITY].find('span').text)
            inv.valuation = self.parse_decimal(cells[self.COL_VALUATION].text)
            inv.diff = self.parse_decimal(cells[self.COL_DIFF].text_content())
            if "%" in cells[self.COL_UNITPRICE].text and "%" in cells[self.COL_UNITVALUE].text:
                inv.unitvalue = inv.valuation / inv.quantity
                inv.unitprice = (inv.valuation - inv.diff) / inv.quantity
            else:
                inv.unitprice = self.parse_decimal(re.search('([^(]+)', cells[self.COL_UNITPRICE].text).group(1))
                inv.unitvalue = self.parse_decimal(cells[self.COL_UNITVALUE].text)
            date = cells[self.COL_UNITVALUE].find('span').text
            if ':' in date:
                inv.vdate = ddate.today()
            else:
                day, month = map(int, date.split('/'))[:2]
                date_guesser = LinearDateGuesser()
                inv.vdate = date_guesser.guess_date(day, month)

            yield inv

    def parse_decimal(self, value):
        v = value.strip()
        if v == '-' or v == '' or v == '_':
            return NotAvailable
        return Decimal(Transaction.clean_amount(value))


class MarketHomePage(MarketPage):
    COL_ID_LABEL = 1
    COL_VALUATION = 5
    def update(self, accounts):
        for line in self.document.xpath('//table[contains(@class, "tableau_comptes_details")]/tbody/tr'):
            cells = line.findall('td')

            id  = cells[self.COL_ID_LABEL].find('div[2]').text.strip()
            for account in accounts:
                if account.id == id:
                    account.label = unicode(cells[self.COL_ID_LABEL].find('div/b').text.strip())
                    account.balance = self.parse_decimal(cells[self.COL_VALUATION].text)


class LifeInsurancePage(MarketPage):
    COL_ID = 0
    COL_QUANTITY = 3
    COL_UNITVALUE = 1
    COL_VALUATION = 4

    def go_on_detail(self, account_id):
        # Sometimes this page is a synthesis, so we need to go on detail.
        if len(self.document.xpath(u'//h1[contains(text(), "Synthèse de vos contrats d\'assurance vie, de capitalisation et de prévoyance")]')) == 1:
            self.browser.select_form('frm_fwk')
            self.browser.set_all_readonly(False)
            self.browser['ID_CNT_CAR'] = account_id
            self.browser['fwkaction'] = 'Enchainer'
            self.browser['fwkcodeaction'] = 'Executer'
            self.browser['puCible'] = 'SEPPU'
            self.browser.submit()
            self.browser.location('https://assurance-personnes.credit-agricole.fr/filiale/entreeBam?sessionSAG=%s&stbpg=pagePU&act=SEPPU&stbzn=bnt&actCrt=SEPPU' % self.browser.sag)

    def iter_investment(self):

        for line in self.document.xpath('//table[@summary and count(descendant::td) > 1]/tbody/tr'):
            cells = line.findall('td')
            if len(cells) < 5:
                continue

            inv = Investment()
            inv.label = unicode(cells[self.COL_ID].text_content().strip())
            a = cells[self.COL_ID].find('a')
            if a is not None:
                try:
                    inv.code = a.attrib['id'].split(' ')[0].split(u'\xa0')[0].split(u'\xc2\xa0')[0]
                except KeyError:
                    #For "Mandat d'arbitrage" which is a recapitulatif of more investement
                    continue
            else:
                inv.code = NotAvailable
            inv.quantity = self.parse_decimal(cells[self.COL_QUANTITY].text_content())
            inv.unitvalue = self.parse_decimal(cells[self.COL_UNITVALUE].text_content())
            inv.valuation = self.parse_decimal(cells[self.COL_VALUATION].text_content())
            inv.unitprice = NotAvailable
            inv.diff = NotAvailable

            yield inv


class BGPIPage(MarketPage):
    COL_ID = 0
    COL_QUANTITY = 1
    COL_UNITPRICE = 2
    COL_UNITVALUE = 3
    COL_VALUATION = 4
    COL_PORTFOLIO = 5
    COL_DIFF = 6

    def iter_investment(self):
        for line in self.document.xpath('//table[contains(@class, "PuTableauLarge")]/tr[contains(@class, "PuLigne")]'):
            cells = line.findall('td')
            inv = Investment()

            inv.label = unicode(cells[self.COL_ID].find('span').text_content().strip())
            a = cells[self.COL_ID].find('a')
            if a is not None:
                inv.code = unicode(a.text_content().strip())
            else:
                inv.code = NotAvailable
            inv.quantity = self.parse_decimal(cells[self.COL_QUANTITY].text_content())
            inv.unitvalue = self.parse_decimal(cells[self.COL_UNITVALUE].text_content())
            inv.valuation = self.parse_decimal(cells[self.COL_VALUATION].text_content())
            inv.unitprice = self.parse_decimal(cells[self.COL_UNITPRICE].text_content())
            inv.diff = self.parse_decimal(cells[self.COL_DIFF].text_content())
            inv.portfolio_share = self.parse_decimal(cells[self.COL_PORTFOLIO].text_content())/100

            yield inv

    def go_on(self, link):
        origin = urlparse(self.url)
        self.browser.location('https://%s%s' % (origin.netloc, link))

    def go_detail(self):
        link = self.document.xpath(u'.//a[contains(text(), "Détail")]')
        return self.go_on(link[0].attrib['href']) if link else False

    def go_back(self):
        self.go_on(self.document.xpath(u'.//a[contains(text(), "Retour à mes comptes")]')[0].attrib['href'])
        self.browser.select_form('formulaire')
        self.browser.submit()
