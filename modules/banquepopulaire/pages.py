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


import datetime
from urlparse import urlsplit, parse_qsl
from decimal import Decimal
import re
import urllib
from mechanize import Cookie, FormNotFoundError


from weboob.browser.filters.standard import CleanText
from weboob.exceptions import BrowserUnavailable, BrowserIncorrectPassword
from weboob.deprecated.browser import Page as _BasePage, BrokenPageError
from weboob.capabilities.bank import Account, Investment
from weboob.capabilities import NotAvailable, UserError
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.json import json
from weboob.tools.pdf import decompress_pdf


class WikipediaARC4(object):
    def __init__(self, key=None):
        self.state = range(256)
        self.x = self.y = 0

        if key is not None:
            self.init(key)

    def init(self, key):
        for i in range(256):
            self.x = (ord(key[i % len(key)]) + self.state[i] + self.x) & 0xFF
            self.state[i], self.state[self.x] = self.state[self.x], self.state[i]
        self.x = 0

    def crypt(self, input):
        output = [None]*len(input)
        for i in xrange(len(input)):
            self.x = (self.x + 1) & 0xFF
            self.y = (self.state[self.x] + self.y) & 0xFF
            self.state[self.x], self.state[self.y] = self.state[self.y], self.state[self.x]
            output[i] = chr((ord(input[i]) ^ self.state[(self.state[self.x] + self.state[self.y]) & 0xFF]))
        return ''.join(output)


class BasePage(_BasePage):
    def get_token(self):
        try:
            token = self.parser.select(self.document.getroot(), '//form//input[@name="token"]', 1, 'xpath').attrib['value']
        except BrokenPageError:
            token = self.parser.select(self.document.getroot(), '//body', 1, 'xpath').attrib['onload']
            token = re.search(r"saveToken\('(.*?)'", token).group(1)
        return token

    def on_loaded(self):
        if not self.is_error():
            self.browser.token = self.get_token()
            self.logger.debug('Update token to %s', self.browser.token)

    def is_error(self):
        return False

    def build_token(self, token):
        """
        These fucking faggots have introduced a new protection on the token.

        Each time there is a call to SAB (selectActionButton), the token
        available in the form is modified with a key available in JS:

        ipsff(function(){TW().ipthk([12, 25, 17, 5, 23, 26, 15, 30, 6]);});

        Each value of the array is an index for the current token to append the
        char at this position at the end of the token.
        """
        table = None
        for script in self.document.xpath('//script'):
            if script.text is None:
                continue
            m = re.search(r'ipthk\(([^\)]+)\)', script.text, flags=re.MULTILINE)
            if m:
                table = json.loads(m.group(1))
        if table is None:
            return token

        for i in table:
            token += token[i]
        return token

    def get_params(self):
        params = {}
        for field in self.document.xpath('//input'):
            params[field.attrib['name']] = field.attrib.get('value', '')
        return params

    def get_button_actions(self):
        actions = {}
        for script in self.document.xpath('//script'):
            if script.text is None:
                continue

            for id, action, strategy in re.findall(r'''attEvt\(window,"(?P<id>[^"]+)","click","sab\('(?P<action>[^']+)','(?P<strategy>[^']+)'\);"''', script.text, re.MULTILINE):
                actions[id] = {'dialogActionPerformed': action,
                               'validationStrategy': strategy,
                              }
        return actions


class RedirectPage(BasePage):
    """
    var i = 'lyhrnu551jo42yfzx0jm0sqk';
    setCookie('i', i);
    var welcomeMessage = decodeURI('M MACHIN');
    var lastConnectionDate = decodeURI('17 Mai 2013');
    var lastConnectionTime = decodeURI('14h27');
    var userId = '12345678';
    var userCat = '1';
    setCookie('uwm', $.rc4EncryptStr(welcomeMessage, i));
    setCookie('ulcd', $.rc4EncryptStr(lastConnectionDate, i));
    setCookie('ulct', $.rc4EncryptStr(lastConnectionTime, i));
    setCookie('uid', $.rc4EncryptStr(userId, i));
    setCookie('uc', $.rc4EncryptStr(userCat, i));
    var agentCivility = 'Mlle';
    var agentFirstName = decodeURI('Jeanne');
    var agentLastName = decodeURI('Machin');
    var agentMail = decodeURI('gary@example.org');
    setCookie('ac', $.rc4EncryptStr(agentCivility, i));
    setCookie('afn', $.rc4EncryptStr(agentFirstName, i));
    setCookie('aln', $.rc4EncryptStr(agentLastName, i));
    setCookie('am', $.rc4EncryptStr(agentMail, i));
    var agencyLabel = decodeURI('DTC');
    var agencyPhoneNumber = decodeURI('0123456789');
    setCookie('al', $.rc4EncryptStr(agencyLabel, i));
    setCookie('apn', $.rc4EncryptStr(agencyPhoneNumber, i));

    Note: that cookies are useless to login on website
    """

    def add_cookie(self, name, value):
        c = Cookie(0, name, value,
                      None, False,
                      '.' + self.browser.DOMAIN, True, True,
                      '/', False,
                      False,
                      None,
                      False,
                      None,
                      None,
                      {})
        cookiejar = self.browser._ua_handlers["_cookies"].cookiejar
        cookiejar.set_cookie(c)

    def on_loaded(self):
        redirect_url = None
        args = {}
        RC4 = None
        for script in self.document.xpath('//script'):
            if script.text is None:
                continue

            m = re.search('window.location=\'([^\']+)\'', script.text, flags=re.MULTILINE)
            if m:
                redirect_url = m.group(1)

            for line in script.text.split('\r\n'):
                m = re.match("^var (\w+) = [^']*'([^']*)'.*", line)
                if m:
                    args[m.group(1)] = m.group(2)

                m = re.match("^setCookie\('([^']+)', (\w+)\);", line)
                if m:
                    self.add_cookie(m.group(1), args[m.group(2)])

                m = re.match("^setCookie\('([^']+)', .*rc4EncryptStr\((\w+), \w+\)", line)
                if m:
                    self.add_cookie(m.group(1), RC4.crypt(args[m.group(2)]).encode('hex'))

                if RC4 is None and 'i' in args:
                    RC4 = WikipediaARC4(args['i'])

        if redirect_url is not None:
            self.browser.location(self.browser.request_class(self.browser.absurl(redirect_url), None, {'Referer': self.url}))

        try:
            self.browser.select_form(name="CyberIngtegrationPostForm")
        except FormNotFoundError:
            pass
        else:
            self.browser.submit(nologin=True)


class ErrorPage(BasePage):
    def get_token(self):
        try:
            buf = self.document.xpath('//body/@onload')[0]
        except IndexError:
            return
        else:
            m = re.search("saveToken\('([^']+)'\)", buf)
            if m:
                return m.group(1)

class UnavailablePage(BasePage):
    def on_loaded(self):
        try:
            a = self.document.xpath('//a[@class="btn"]')[0]
        except IndexError:
            raise BrowserUnavailable()
        else:
            self.browser.location(a.attrib['href'], nologin=True)


class LoginPage(BasePage):
    def on_loaded(self):
        try:
            h1 = self.parser.select(self.document.getroot(), 'h1', 1)
        except BrokenPageError:
            pass

        if h1.text is not None and h1.text.startswith('Le service est moment'):
            try:
                raise BrowserUnavailable(self.document.xpath('//h4')[0].text)
            except KeyError:
                raise BrowserUnavailable(h1.text)

    def login(self, login, passwd):
        self.browser.select_form(name='Login')
        self.browser['IDToken1'] = login.encode(self.browser.ENCODING)
        self.browser['IDToken2'] = passwd.encode(self.browser.ENCODING)
        self.browser.submit(nologin=True)


class Login2Page(LoginPage):
    @property
    def request_url(self):
        transactionID = self.group_dict['transactionID']
        return 'https://www.icgauth.banquepopulaire.fr/dacswebssoissuer/api/v1u0/transaction/%s' % transactionID

    def on_loaded(self):
        r = self.browser.openurl(self.request_url)
        doc = json.load(r)
        self.form_id = doc['step']['validationUnits'][0]['PASSWORD_LOOKUP'][0]['id']

    def login(self, login, password):
        payload = {'validate': {'PASSWORD_LOOKUP': [{'id': self.form_id,
                                                     'login': login.encode(self.browser.ENCODING).upper(),
                                                     'password': password.encode(self.browser.ENCODING),
                                                     'type': 'PASSWORD_LOOKUP'
                                                    }]
                               }
                  }
        req = self.browser.request_class(self.request_url + '/step')
        req.add_header('Content-Type', 'application/json')
        r = self.browser.openurl(req, json.dumps(payload))

        doc = json.load(r)
        self.logger.debug(doc)
        if 'phase' in doc and doc['phase']['state'] == 'TERMS_OF_USE':
            # Got:
            # {u'phase': {u'state': u'TERMS_OF_USE'}, u'validationUnits': [{u'LIST_OF_TERMS': [{u'type': u'TERMS', u'id': u'b7f28f91-7aa0-48aa-8028-deec13ae341b', u'reference': u'CGU_CYBERPLUS'}]}]}
            if 'reference' in doc['validationUnits'][0]:
                del doc['validationUnits'][0]['reference']
            payload = {'validate': doc['validationUnits'][0]}
            req = self.browser.request_class(self.request_url + '/step')
            req.add_header('Content-Type', 'application/json')
            r = self.browser.openurl(req, json.dumps(payload))
            doc = json.load(r)
            self.logger.debug(doc)

        if ('phase' in doc and doc['phase']['previousResult'] == 'FAILED_AUTHENTICATION') or \
           doc['response']['status'] != 'AUTHENTICATION_SUCCESS':
            raise BrowserIncorrectPassword()

        self.browser.location(doc['response']['saml2_post']['action'], urllib.urlencode({'SAMLResponse': doc['response']['saml2_post']['samlResponse']}))


class IndexPage(BasePage):
    def get_token(self):
        url = self.document.getroot().xpath('//frame[@name="portalHeader"]')[0].attrib['src']
        v = urlsplit(url)
        args = dict(parse_qsl(v.query))
        return args['token']


class HomePage(BasePage):
    def get_token(self):
        vary = None
        if self.group_dict.get('vary', None) is not None:
            vary = self.group_dict['vary']
        else:
            for script in self.document.xpath('//script'):
                if script.text is None:
                    continue

                m = re.search("'vary', '([\d-]+)'\)", script.text)
                if m:
                    vary = m.group(1)
                    break

        r = self.browser.openurl(self.browser.request_class(self.browser.buildurl(self.browser.absurl('/portailinternet/Transactionnel/Pages/CyberIntegrationPage.aspx'), vary=vary), 'taskId=aUniversMesComptes', {'Referer': self.url}))
        if not int(r.info().get('Content-Length', '')):
            r = self.browser.openurl(self.browser.request_class(self.browser.buildurl(self.browser.absurl('/portailinternet/Transactionnel/Pages/CyberIntegrationPage.aspx')), 'taskId=aUniversMesComptes', {'Referer': self.url}))
        doc = self.browser.get_document(r)
        date = None
        for script in doc.xpath('//script'):
            if script.text is None:
                continue

            m = re.search('lastConnectionDate":"([^"]*)"', script.text)
            if m:
                date = m.group(1)

        r = self.browser.openurl(self.browser.request_class(self.browser.absurl('/cyber/ibp/ate/portal/integratedInternet.jsp'), 'session%%3Aate.lastConnectionDate=%s&taskId=aUniversMesComptes' % date, {'Referer': r.geturl()}))
        v = urlsplit(r.geturl())
        args = dict(parse_qsl(v.query))
        return args['token']


class AccountsPage(BasePage):
    ACCOUNT_TYPES = {u'Mes comptes d\'épargne':        Account.TYPE_SAVINGS,
                     u'Mon épargne':                   Account.TYPE_SAVINGS,
                     u'Placements':                    Account.TYPE_SAVINGS,
                     u'Liste complète de mon épargne': Account.TYPE_SAVINGS,
                     u'Mes comptes':                   Account.TYPE_CHECKING,
                     u'Comptes en euros':              Account.TYPE_CHECKING,
                     u'Liste complète de mes comptes': Account.TYPE_CHECKING,
                     u'Mes emprunts':                  Account.TYPE_LOAN,
                     u'Liste complète de mes emprunts':Account.TYPE_LOAN,
                     u'Financements':                  Account.TYPE_LOAN,
                     u'Mes services':                  None,    # ignore this kind of accounts (no bank ones)
                     u'Équipements':                   None,    # ignore this kind of accounts (no bank ones)
                     u'Synthèse':                      None,    # ignore this title
                    }

    def is_error(self):
        for script in self.document.xpath('//script'):
            if script.text is not None and \
               (u"Le service est momentanément indisponible" in script.text or
                u"Votre abonnement ne vous permet pas d'accéder à ces services" in script.text):
                return True

        return False

    def pop_up(self):
        if self.document.xpath('//span[contains(text(), "du navigateur Internet.")]'):
            return True
        return False

    def is_short_list(self):
        return len(self.document.xpath('//script[contains(text(), "EQUIPEMENT_COMPLET")]')) > 0

    COL_NUMBER = 0
    COL_TYPE = 1
    COL_LABEL = 2
    COL_BALANCE = 3
    COL_COMING = 4

    def iter_accounts(self, next_pages):
        account_type = Account.TYPE_UNKNOWN

        params = self.get_params()
        actions = self.get_button_actions()

        for div in self.document.getroot().cssselect('div.btit'):
            if div.text in (None, u'Synthèse'):
                continue
            account_type = self.ACCOUNT_TYPES.get(div.text.strip(), Account.TYPE_UNKNOWN)

            if account_type is None:
                # ignore services accounts
                self.logger.debug('Ignore account type %s', div.text.strip())
                continue

            # Go to the full list of this kind of account, if any.
            btn = div.getparent().xpath('.//button/span[text()="Suite"]')
            if len(btn) > 0:
                btn = btn[0].getparent()
                _params = params.copy()
                _params.update(actions[btn.attrib['id']])
                next_pages.append(_params)
                continue

            currency = None
            for th in div.getnext().xpath('.//thead//th'):
                m = re.match('.*\((\w+)\)$', th.text)
                if m and currency is None:
                    currency = Account.get_currency(m.group(1))

            for tr in div.getnext().xpath('.//tbody/tr'):
                if 'id' not in tr.attrib:
                    continue

                args = dict(parse_qsl(tr.attrib['id']))
                tds = tr.findall('td')

                if len(tds) < 4 or 'identifiant' not in args:
                    self.logger.warning('Unable to parse an account')
                    continue

                account = Account()
                account.id = args['identifiant'].replace(' ', '')
                account.label = u' '.join([u''.join([txt.strip() for txt in tds[1].itertext()]),
                                           u''.join([txt.strip() for txt in tds[2].itertext()])]).strip()
                account.type = account_type

                balance = FrenchTransaction.clean_amount(u''.join([txt.strip() for txt in tds[3].itertext()]))
                account.balance = Decimal(balance or '0.0')
                account.currency = currency
                if account.type == account.TYPE_LOAN:
                    account.balance = - abs(account.balance)

                account._prev_debit = None
                account._next_debit = None
                account._params = None
                account._coming_params = None
                account._invest_params = None
                if balance != u'' and len(tds[3].xpath('.//a')) > 0:
                    account._params = params.copy()
                    account._params['dialogActionPerformed'] = 'SOLDE'
                    account._params['attribute($SEL_$%s)' % tr.attrib['id'].split('_')[0]] = tr.attrib['id'].split('_', 1)[1]

                if len(tds) >= 5 and len(tds[self.COL_COMING].xpath('.//a')) > 0:
                    _params = account._params.copy()
                    _params['dialogActionPerformed'] = 'ENCOURS_COMPTE'

                    # If there is an action needed before going to the cards page, save it.
                    m = re.search('dialogActionPerformed=([\w_]+)', self.url)
                    if m and m.group(1) != 'EQUIPEMENT_COMPLET':
                        _params['prevAction'] = m.group(1)
                    next_pages.append(_params)

                if not account._params:
                    account._invest_params = params.copy()
                    account._invest_params['dialogActionPerformed'] = 'CONTRAT'
                    account._invest_params['attribute($SEL_$%s)' % tr.attrib['id'].split('_')[0]] = tr.attrib['id'].split('_', 1)[1]

                yield account

        # Needed to preserve navigation.
        btn = self.document.xpath('.//button/span[text()="Retour"]')
        if len(btn) > 0:
            btn = btn[0].getparent()
            _params = params.copy()
            _params.update(actions[btn.attrib['id']])
            self.browser.openurl('/cyber/internet/ContinueTask.do', urllib.urlencode(_params))

class AccountsFullPage(AccountsPage):
    pass

class CardsPage(BasePage):
    COL_ID = 0
    COL_TYPE = 1
    COL_LABEL = 2
    COL_DATE = 3
    COL_AMOUNT = 4

    def iter_accounts(self, next_pages):
        params = self.get_params()

        account = None
        currency = None
        for th in self.document.xpath('//table[@id="TabCtes"]//thead//th'):
            m = re.match('.*\((\w+)\)$', th.text)
            if m and currency is None:
                currency = Account.get_currency(m.group(1))

        for tr in self.document.xpath('//table[@id="TabCtes"]/tbody/tr'):
            cols = tr.xpath('./td')

            id = self.parser.tocleanstring(cols[self.COL_ID])
            if len(id) > 0:
                if account is not None:
                    yield account
                account = Account()
                account.id = id.replace(' ', '')
                account.type = Account.TYPE_CARD
                account.balance = account.coming = Decimal('0')
                account._next_debit = datetime.date.today()
                account._prev_debit = datetime.date(2000,1,1)
                account.label = u' '.join([self.parser.tocleanstring(cols[self.COL_TYPE]),
                                           self.parser.tocleanstring(cols[self.COL_LABEL])])
                account.currency = currency
                account._params = None
                account._invest_params = None
                account._coming_params = params.copy()
                account._coming_params['dialogActionPerformed'] = 'SELECTION_ENCOURS_CARTE'
                account._coming_params['attribute($SEL_$%s)' % tr.attrib['id'].split('_')[0]] = tr.attrib['id'].split('_', 1)[1]
            elif account is None:
                raise BrokenPageError('Unable to find accounts on cards page')
            else:
                account._params = params.copy()
                account._params['dialogActionPerformed'] = 'SELECTION_ENCOURS_CARTE'
                account._params['attribute($SEL_$%s)' % tr.attrib['id'].split('_')[0]] = tr.attrib['id'].split('_', 1)[1]

            date_col = self.parser.tocleanstring(cols[self.COL_DATE])
            m = re.search('(\d+)/(\d+)/(\d+)', date_col)
            if not m:
                self.logger.warning('Unable to parse date %r' % date_col)
                continue

            date = datetime.date(*reversed(map(int, m.groups())))
            if date.year < 100:
                date = date.replace(year=date.year+2000)

            amount = Decimal(FrenchTransaction.clean_amount(self.parser.tocleanstring(cols[self.COL_AMOUNT])))

            if not date_col.endswith('(1)'):
                # debited
                account.coming += - abs(amount)
                account._next_debit = date
            elif date > account._prev_debit:
                account._prev_balance = - abs(amount)
                account._prev_debit = date

        if account is not None:
            yield account

        # Needed to preserve navigation.
        btn = self.document.xpath('.//button/span[text()="Retour"]')
        if len(btn) > 0:
            btn = btn[0].getparent()
            actions = self.get_button_actions()
            _params = params.copy()
            _params.update(actions[btn.attrib['id']])
            self.browser.openurl('/cyber/internet/ContinueTask.do', urllib.urlencode(_params))


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile('^RET DAB (?P<text>.*?) RETRAIT (DU|LE) (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d+).*'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^RET DAB (?P<text>.*?) CARTE ?:.*'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^(?P<text>.*) RETRAIT DU (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2}) .*'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^(RETRAIT CARTE )?RET(RAIT)? DAB (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('((\w+) )?(?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2}) CB[:\*][^ ]+ (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile('^VIR(EMENT)? (?P<text>.*)'),   FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^(PRLV|PRELEVEMENT) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_ORDER),
                (re.compile('^(?P<text>CHEQUE .*)'),   FrenchTransaction.TYPE_CHECK),
                (re.compile('^(AGIOS /|FRAIS) (?P<text>.*)', re.IGNORECASE),
                                                            FrenchTransaction.TYPE_BANK),
                (re.compile('^(CONVENTION \d+ )?COTIS(ATION)? (?P<text>.*)', re.IGNORECASE),
                                                            FrenchTransaction.TYPE_BANK),
                (re.compile('^REMISE (?P<text>.*)'),        FrenchTransaction.TYPE_DEPOSIT),
                (re.compile('^(?P<text>ECHEANCE PRET .*)'), FrenchTransaction.TYPE_LOAN_PAYMENT),
                (re.compile('^(?P<text>.*)( \d+)? QUITTANCE .*'),
                                                            FrenchTransaction.TYPE_ORDER),
                (re.compile('^.* LE (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{2})$'),
                                                            FrenchTransaction.TYPE_UNKNOWN),
               ]


class TransactionsPage(BasePage):
    def get_next_params(self):
        nxt = self.document.xpath('//li[contains(@id, "_nxt")]')
        if len(nxt) == 0 or nxt[0].attrib.get('class', '') == 'nxt-dis':
            return None

        params = {}
        for field in self.document.xpath('//input'):
            params[field.attrib['name']] = field.attrib.get('value', '')

        params['validationStrategy'] = 'NV'
        params['pagingDirection'] = 'NEXT'
        params['pagerName'] = nxt[0].attrib['id'].split('_', 1)[0]

        return params

    def get_history(self, account, coming):
        if len(self.document.xpath('//table[@id="tbl1"]')) > 0:
            return self.get_account_history()
        if len(self.document.xpath('//table[@id="TabFact"]')) > 0:
            return self.get_card_history(account, coming)

        raise NotImplementedError('Unable to find what kind of history it is.')

    COL_COMPTA_DATE = 0
    COL_LABEL = 1
    COL_REF = 2 # optional
    COL_OP_DATE = -4
    COL_VALUE_DATE = -3
    COL_DEBIT = -2
    COL_CREDIT = -1

    def get_account_history(self):
        for tr in self.document.xpath('//table[@id="tbl1"]/tbody/tr'):
            tds = tr.findall('td')

            if len(tds) < 5:
                continue

            t = Transaction()

            # XXX We currently take the *value* date, but it will probably
            # necessary to use the *operation* one.
            # Default sort on website is by compta date, so in browser.py we
            # change the sort on value date.
            date = self.parser.tocleanstring(tds[self.COL_OP_DATE])
            vdate = self.parser.tocleanstring(tds[self.COL_VALUE_DATE])
            raw = self.parser.tocleanstring(tds[self.COL_LABEL])
            debit = self.parser.tocleanstring(tds[self.COL_DEBIT])
            credit = self.parser.tocleanstring(tds[self.COL_CREDIT])

            t.parse(date, re.sub(r'[ ]+', ' ', raw), vdate)
            t.set_amount(credit, debit)

            # Strip the balance displayed in transaction labels
            t.label = re.sub('solde en valeur : .*', '', t.label)

            # XXX Fucking hack to include the check number not displayed in the full label.
            if re.match("^CHEQUE ", t.label):
                t.label = 'CHEQUE No: %s' % self.parser.tocleanstring(tds[self.COL_REF])

            yield t

    COL_CARD_DATE = 0
    COL_CARD_LABEL = 1
    COL_CARD_AMOUNT = 2

    def get_card_history(self, account, coming):
        if coming:
            debit_date = account._next_debit
        elif not hasattr(account, '_prev_balance'):
            return
        else:
            debit_date = account._prev_debit
            if 'ContinueTask.do' in self.url:
                t = Transaction()
                t.parse(debit_date, 'RELEVE CARTE')
                t.amount = -account._prev_balance
                yield t

        currency = Account.get_currency(self.document\
                                        .xpath('//table[@id="TabFact"]/thead//th')[self.COL_CARD_AMOUNT]\
                                        .text\
                                        .replace('(', ' ')\
                                        .replace(')', ' '))
        for i, tr in enumerate(self.document.xpath('//table[@id="TabFact"]/tbody/tr')):
            tds = tr.findall('td')

            if len(tds) < 3:
                continue

            t = Transaction()

            date = self.parser.tocleanstring(tds[self.COL_CARD_DATE])
            label = self.parser.tocleanstring(tds[self.COL_CARD_LABEL])
            amount = '-' + self.parser.tocleanstring(tds[self.COL_CARD_AMOUNT])

            t.parse(debit_date, re.sub(r'[ ]+', ' ', label))
            t.set_amount(amount)
            t.rdate = t.parse_date(date)
            t.original_currency = currency
            yield t

    def no_operations(self):
        if len(self.document.xpath('//table[@id="tbl1" or @id="TabFact"]//td[@colspan]')) > 0:
            return True
        if len(self.document.xpath(u'//div[contains(text(), "Accès à LineBourse")]')) > 0:
            return True

        return False

    def get_investment_page_params(self):
        script = self.document.xpath('//body')[0].attrib['onload']
        url = None
        m = re.search(r"','(.+?)',\[", script, re.MULTILINE)
        if m:
            url = m.group(1)
        params = {}
        for key, value in re.findall(r"key:'(?P<key>SJRToken)'\,value:'(?P<value>.*?)'}", script, re.MULTILINE):
            params[key] = value
        return url, params if url and params else None


class LineboursePage(_BasePage):
    pass


class InvestmentLineboursePage(_BasePage):
    COL_LABEL = 0
    COL_QUANTITY = 1
    COL_UNITVALUE = 2
    COL_VALUATION = 3
    COL_UNITPRICE = 4
    COL_PERF_PERCENT = 5
    COL_PERF = 6
    def get_investments(self):
        for line in self.document.xpath('//table[contains(@summary, "Contenu")]/tbody/tr[@class="color4"]'):
            cols1 = line.findall('td')
            cols2 = line.xpath('./following-sibling::tr')[0].findall('td')

            inv = Investment()
            inv.label = self.parser.tocleanstring(cols1[self.COL_LABEL].xpath('.//span')[0])
            inv.code = self.parser.tocleanstring(cols1[self.COL_LABEL].xpath('./a')[0]).split(' ')[-1]
            inv.quantity = self.parse_decimal(cols2[self.COL_QUANTITY])
            inv.unitprice = self.parse_decimal(cols2[self.COL_UNITPRICE])
            inv.unitvalue = self.parse_decimal(cols2[self.COL_UNITVALUE])
            inv.valuation = self.parse_decimal(cols2[self.COL_VALUATION])
            inv.diff = self.parse_decimal(cols2[self.COL_PERF])

            yield inv

    def parse_decimal(self, string):
        value = self.parser.tocleanstring(string)
        if value == '':
            return NotAvailable
        return Decimal(Transaction.clean_amount(value))


class NatixisPage(_BasePage):
    def submit_form(self):
        self.browser.select_form(name="formRoutage")
        self.browser.submit(nologin=True)


class InvestmentNatixisPage(_BasePage):
    COL_LABEL = 0
    COL_QUANTITY = 2
    COL_UNITVALUE = 3
    COL_VALUATION = 4
    def get_investments(self):
        for line in self.document.xpath('//div[@class="row-fluid table-contrat-supports"]/table/tbody[(@class)]/tr'):
            cols = line.findall('td')

            inv = Investment()
            inv.label = self.parser.tocleanstring(cols[self.COL_LABEL]).replace('Cas sans risque ', '')
            inv.quantity = self.parse_decimal(cols[self.COL_QUANTITY])
            inv.unitvalue = self.parse_decimal(cols[self.COL_UNITVALUE])
            inv.valuation = self.parse_decimal(cols[self.COL_VALUATION])

            yield inv

    def parse_decimal(self, string):
        value = self.parser.tocleanstring(string).replace('Si famille fonds generaux, on affiche un tiret', '').replace('Cas sans risque', '').replace(' ', '')
        if value == '-':
            return NotAvailable
        return Decimal(Transaction.clean_amount(value))

class MessagePage(_BasePage):
    def skip(self):
        try:
            self.browser.select_form(name="leForm")
        except FormNotFoundError:
            pass
        else:
            self.browser.submit(nologin=True)

class DocumentsPage(BasePage):
    def get_account_extract(self, acc_id):
        for td in self.document.xpath('//tbody[@class="ts tms"]/tr'):
            if CleanText().filter(td.xpath('./td[1]')[0]) in acc_id and CleanText().filter(td.xpath('./td[4]')[0]) == "Extrait de compte":
                self.browser.select_form(predicate=lambda form: form.attrs.get('id', '') == 'myForm')
                self.browser.set_all_readonly(False)
                doc_id = self.browser['taskOID']
                self.browser['token'] = self.build_token(self.browser['token'])
                self.browser['attribute($SEL_ACTIVE$tbl2)'] = td.xpath('./@id')[0].split('_', 1)[1]
                self.browser['dialogActionPerformed'] = "TELECHARGER"
                self.browser['attribute($SEL_$lst1_hidden)'] = 'lst1$listeTypeDoc$listeTypeDocSelectionne$'
                self.browser['attribute($SEL_$lst2_hidden)'] = 'lst2$listeCompteRecherche$listeCompteSelect$'
                self.browser['dateDebut'] = '23/09/2014'
                self.browser['dateFin'] = '23/09/2015'
                self.browser['attribute($SEL_$tbl2_hidden)'] = 'tbl2$listeDocumentSelectionne$'
                self.browser['attribute($SEL_ACTIVE$tbl2_hidden)'] = 'tbl2$documentSelectionne$'
                self.browser.submit()
                return doc_id
        return False

class PostDocument(BasePage):
    def get_doc_id(self):
        for script in self.document.xpath('//script'):
            if script.text is None:
                continue

            m = re.search("DocumentUtils\.download\('(.*)'\)", script.text)
            if m:
                return m.group(1)

        return None

class ExtractPdf(_BasePage):
    iban_regexp= r'\(IBAN \) Tj(?:.*[\n\r]){5}\((\w{4})\)(?:.*[\n\r]){10}\((\d{4})\)(?:.*[\n\r]){10}\((\d{4})\)(?:.*[\n\r]){10}\((\d{4})\)(?:.*[\n\r]){10}\((\d{4})\)(?:.*[\n\r]){10}\((\d{4})\)(?:.*[\n\r]){10}\((\d{3})\)'
    def __init__(self, *args, **kwargs):
        _BasePage.__init__(self, *args, **kwargs)
        try:
            self._pdf = decompress_pdf(self.document)
        except OSError as e:
            raise UserError(u'Make sure mupdf-tools is installed (%s)' % e)

    def get_iban(self):
        res = re.findall(self.iban_regexp, self._pdf)
        if res and len(res) == 1:
            return u''.join(res[0])
        return None
