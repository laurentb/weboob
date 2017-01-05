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

from weboob.browser.elements import method, DictElement, ItemElement
from weboob.browser.filters.standard import CleanText, CleanDecimal, Regexp, Eval, DateTime, Date
from weboob.browser.filters.html import Attr, Link, AttributeNotFound
from weboob.browser.filters.json import Dict
from weboob.exceptions import BrowserUnavailable, BrowserIncorrectPassword

from weboob.browser.pages import HTMLPage, LoggedPage, FormNotFound, JsonPage, RawPage

from weboob.capabilities.bank import Account, Investment
from weboob.capabilities import NotAvailable
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.json import json
from weboob.tools.misc import to_unicode
from weboob.tools.pdf import get_pdf_rows


class BrokenPageError(Exception):
    pass


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


class BasePage(object):
    ENCODING = 'iso-8859-15'

    def get_token(self):
        token = Attr('//form//input[@name="token"]', 'value', default=NotAvailable)(self.doc)
        if not token:
            try:
                token = Regexp(Attr('//body', 'onload'), "saveToken\('(.*?)'")(self.doc)
            except AttributeNotFound:
                self.logger.warning('Unable to update token.')
        return token

    def on_load(self):
        token = self.get_token()
        if token:
            self.browser.token = token
            self.logger.debug('Update token to %s', self.browser.token)

    def is_error(self):
        for script in self.doc.xpath('//script'):
            if script.text is not None and \
               (u"Le service est momentanément indisponible" in script.text or
                u"Votre abonnement ne vous permet pas d'accéder à ces services" in script.text):
                return True

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
        for script in self.doc.xpath('//script'):
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
        for field in self.doc.xpath('//input'):
            params[field.attrib['name']] = field.attrib.get('value', '')
        return params

    def get_button_actions(self):
        actions = {}
        for script in self.doc.xpath('//script'):
            if script.text is None:
                continue

            for id, action, strategy in re.findall(r'''attEvt\(window,"(?P<id>[^"]+)","click","sab\('(?P<action>[^']+)','(?P<strategy>[^']+)'\);"''', script.text, re.MULTILINE):
                actions[id] = {'dialogActionPerformed': action,
                               'validationStrategy': strategy,
                              }
        return actions


class MyHTMLPage(BasePage, HTMLPage):
    def build_doc(self, data, *args, **kwargs):
        # XXX FUCKING HACK BECAUSE BANQUE POPULAIRE ARE FAGGOTS AND INCLUDE NULL
        # BYTES IN DOCUMENTS.
        data = data.replace(b'\x00', b'')
        return super(MyHTMLPage, self).build_doc(data, *args, **kwargs)


class RedirectPage(LoggedPage, MyHTMLPage):
    ENCODING = None

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
        # httplib/cookielib don't seem to like unicode cookies...
        name = to_unicode(name).encode('utf-8')
        value = to_unicode(value).encode('utf-8')
        self.browser.logger.debug('adding cookie %r=%r', name, value)
        self.browser.session.cookies.set(name, value)

    def on_load(self):
        redirect_url = None
        args = {}
        RC4 = None
        for script in self.doc.xpath('//script'):
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
            url = self.browser.absurl(redirect_url)
            headers = {'Referer': self.url}
            self.browser.logger.debug('redir...')
            self.browser.location(url, headers=headers)

        try:
            form = self.get_form(name="CyberIngtegrationPostForm")
        except FormNotFound:
            pass
        else:
            form.submit()


class ErrorPage(LoggedPage, MyHTMLPage):
    def get_token(self):
        try:
            buf = self.doc.xpath('//body/@onload')[0]
        except IndexError:
            return
        else:
            m = re.search("saveToken\('([^']+)'\)", buf)
            if m:
                return m.group(1)


class UnavailablePage(LoggedPage, MyHTMLPage):
    def on_load(self):
        a = Link('//a[@class="btn"][1]')(self.doc)
        if not a:
            raise BrowserUnavailable()
        self.browser.location(a)


class LoginPage(MyHTMLPage):
    def on_load(self):
        h1 = CleanText('//h1[1]')(self.doc)

        if h1.startswith('Le service est moment'):
            text = CleanText('//h4[1]')(self.doc) or h1
            raise BrowserUnavailable(text)

    def login(self, login, passwd):
        form = self.get_form(name='Login')
        form['IDToken1'] = login.encode(self.ENCODING)
        form['IDToken2'] = passwd.encode(self.ENCODING)
        form.submit()


class Login2Page(LoginPage):
    @property
    def request_url(self):
        transactionID = self.params['transactionID']
        assert transactionID
        return 'https://www.icgauth.banquepopulaire.fr/dacswebssoissuer/api/v1u0/transaction/%s' % transactionID

    def on_load(self):
        r = self.browser.open(self.request_url)
        doc = json.loads(r.content)
        self.form_id = doc['step']['validationUnits'][0]['PASSWORD_LOOKUP'][0]['id']

    def login(self, login, password):
        payload = {'validate': {'PASSWORD_LOOKUP': [{'id': self.form_id,
                                                     'login': login.encode(self.ENCODING).upper(),
                                                     'password': password.encode(self.ENCODING),
                                                     'type': 'PASSWORD_LOOKUP'
                                                    }]
                               }
                  }

        url = self.request_url + '/step'
        headers = {'Content-Type': 'application/json'}
        r = self.browser.open(url, data=json.dumps(payload), headers=headers)

        doc = json.loads(r.content)
        self.logger.debug('doc = %s', doc)
        if 'phase' in doc and doc['phase']['state'] == 'TERMS_OF_USE':
            # Got:
            # {u'phase': {u'state': u'TERMS_OF_USE'}, u'validationUnits': [{u'LIST_OF_TERMS': [{u'type': u'TERMS', u'id': u'b7f28f91-7aa0-48aa-8028-deec13ae341b', u'reference': u'CGU_CYBERPLUS'}]}]}
            if 'reference' in doc['validationUnits'][0]:
                del doc['validationUnits'][0]['reference']
            payload = {'validate': doc['validationUnits'][0]}

            url = self.request_url + '/step'
            headers = {'Content-Type': 'application/json'}
            r = self.browser.open(url, data=json.dumps(payload), headers=headers)
            doc = json.loads(r.content)
            self.logger.debug('doc = %s', doc)

        if ('phase' in doc and doc['phase']['previousResult'] == 'FAILED_AUTHENTICATION') or \
           doc['response']['status'] != 'AUTHENTICATION_SUCCESS':
            raise BrowserIncorrectPassword()

        data = {'SAMLResponse': doc['response']['saml2_post']['samlResponse']}
        self.browser.location(doc['response']['saml2_post']['action'], data=data)


class IndexPage(LoggedPage, MyHTMLPage):
    def get_token(self):
        url = self.doc.xpath('//frame[@name="portalHeader"]')[0].attrib['src']
        v = urlsplit(url)
        args = dict(parse_qsl(v.query))
        return args['token']


class HomePage(LoggedPage, MyHTMLPage):
    def get_token(self):
        vary = None
        if self.params.get('vary', None) is not None:
            vary = self.params['vary']
        else:
            for script in self.doc.xpath('//script'):
                if script.text is None:
                    continue

                m = re.search("'vary', '([\d-]+)'\)", script.text)
                if m:
                    vary = m.group(1)
                    break

        url = self.browser.absurl('/portailinternet/Transactionnel/Pages/CyberIntegrationPage.aspx?%s' % urllib.urlencode({'vary': vary}))
        headers = {'Referer': self.url}
        r = self.browser.open(url, data='taskId=aUniversMesComptes', headers=headers)

        if not int(r.headers.get('Content-Length', 0)):
            url = self.browser.absurl('/portailinternet/Transactionnel/Pages/CyberIntegrationPage.aspx')
            headers = {'Referer': self.url}
            r = self.browser.open(url, data='taskId=aUniversMesComptes', headers=headers)

        doc = r.page.doc
        date = None
        for script in doc.xpath('//script'):
            if script.text is None:
                continue

            m = re.search('lastConnectionDate":"([^"]*)"', script.text)
            if m:
                date = m.group(1)

        url = self.browser.absurl('/cyber/ibp/ate/portal/integratedInternet.jsp')
        data = 'session%%3Aate.lastConnectionDate=%s&taskId=aUniversMesComptes' % date
        headers = {'Referer': r.url}
        r = self.browser.open(url, data=data, headers=headers)

        v = urlsplit(r.url)
        args = dict(parse_qsl(v.query))
        return args['token']


class AccountsPage(LoggedPage, MyHTMLPage):
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

    PATTERN = [(re.compile('.*Titres Pea.*'), Account.TYPE_PEA),
               (re.compile('.*Plan Epargne Retraite.*'), Account.TYPE_PERP),
               (re.compile('.*Titres.*'), Account.TYPE_MARKET),
               (re.compile('.*Selection Vie.*'),Account.TYPE_LIFE_INSURANCE),
               (re.compile('^Fructi Pulse.*'), Account.TYPE_MARKET),
               ]

    def pop_up(self):
        if self.doc.xpath('//span[contains(text(), "du navigateur Internet.")]'):
            return True
        return False

    def is_short_list(self):
        return len(self.doc.xpath('//script[contains(text(), "EQUIPEMENT_COMPLET")]')) > 0

    COL_NUMBER = 0
    COL_TYPE = 1
    COL_LABEL = 2
    COL_BALANCE = 3
    COL_COMING = 4

    def iter_accounts(self, next_pages):
        account_type = Account.TYPE_UNKNOWN

        params = self.get_params()
        actions = self.get_button_actions()

        for div in self.doc.getroot().cssselect('div.btit'):
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

                for pattern, _type in self.PATTERN:
                    match = pattern.match(account.label)
                    if match:
                        account.type = _type
                        break
                    else:
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
        btn = self.doc.xpath('.//button/span[text()="Retour"]')
        if len(btn) > 0:
            btn = btn[0].getparent()
            _params = params.copy()
            _params.update(actions[btn.attrib['id']])
            self.browser.open('/cyber/internet/ContinueTask.do', data=_params)


class AccountsFullPage(AccountsPage):
    pass


class CardsPage(LoggedPage, MyHTMLPage):
    COL_ID = 0
    COL_TYPE = 1
    COL_LABEL = 2
    COL_DATE = 3
    COL_AMOUNT = 4

    def iter_accounts(self, next_pages):
        params = self.get_params()

        account = None
        currency = None
        for th in self.doc.xpath('//table[@id="TabCtes"]//thead//th'):
            m = re.match('.*\((\w+)\)$', th.text)
            if m and currency is None:
                currency = Account.get_currency(m.group(1))

        for tr in self.doc.xpath('//table[@id="TabCtes"]/tbody/tr'):
            cols = tr.xpath('./td')

            id = CleanText(None).filter(cols[self.COL_ID])
            if len(id) > 0:
                if account is not None:
                    yield account
                account = Account()
                account.id = id.replace(' ', '')
                account.type = Account.TYPE_CARD
                account.balance = account.coming = Decimal('0')
                account._next_debit = datetime.date.today()
                account._prev_debit = datetime.date(2000,1,1)
                account.label = u' '.join([CleanText(None).filter(cols[self.COL_TYPE]),
                                           CleanText(None).filter(cols[self.COL_LABEL])])
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

            date_col = CleanText(None).filter(cols[self.COL_DATE])
            m = re.search('(\d+)/(\d+)/(\d+)', date_col)
            if not m:
                self.logger.warning('Unable to parse date %r' % date_col)
                continue

            date = datetime.date(*reversed(map(int, m.groups())))
            if date.year < 100:
                date = date.replace(year=date.year+2000)

            amount = Decimal(FrenchTransaction.clean_amount(CleanText(None).filter(cols[self.COL_AMOUNT])))

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
        btn = self.doc.xpath('.//button/span[text()="Retour"]')
        if len(btn) > 0:
            btn = btn[0].getparent()
            actions = self.get_button_actions()
            _params = params.copy()
            _params.update(actions[btn.attrib['id']])
            self.browser.open('/cyber/internet/ContinueTask.do', data=_params)


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


class TransactionsPage(LoggedPage, MyHTMLPage):
    def get_next_params(self):
        nxt = self.doc.xpath('//li[contains(@id, "_nxt")]')
        if len(nxt) == 0 or nxt[0].attrib.get('class', '') == 'nxt-dis':
            return None

        params = {}
        for field in self.doc.xpath('//input'):
            params[field.attrib['name']] = field.attrib.get('value', '')

        params['validationStrategy'] = 'NV'
        params['pagingDirection'] = 'NEXT'
        params['pagerName'] = nxt[0].attrib['id'].split('_', 1)[0]

        return params

    def get_history(self, account, coming):
        if len(self.doc.xpath('//table[@id="tbl1"]')) > 0:
            return self.get_account_history()
        if len(self.doc.xpath('//table[@id="TabFact"]')) > 0:
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
        for tr in self.doc.xpath('//table[@id="tbl1"]/tbody/tr'):
            tds = tr.findall('td')

            if len(tds) < 5:
                continue

            t = Transaction()

            # XXX We currently take the *value* date, but it will probably
            # necessary to use the *operation* one.
            # Default sort on website is by compta date, so in browser.py we
            # change the sort on value date.
            cleaner = CleanText(None).filter
            date = cleaner(tds[self.COL_OP_DATE])
            vdate = cleaner(tds[self.COL_VALUE_DATE])
            raw = cleaner(tds[self.COL_LABEL])
            debit = cleaner(tds[self.COL_DEBIT])
            credit = cleaner(tds[self.COL_CREDIT])

            t.parse(date, re.sub(r'[ ]+', ' ', raw), vdate)
            t.set_amount(credit, debit)

            # Strip the balance displayed in transaction labels
            t.label = re.sub('solde en valeur : .*', '', t.label)
            t.raw = re.sub('solde en valeur : .*', '', t.raw)

            # XXX Fucking hack to include the check number not displayed in the full label.
            if re.match("^CHEQUE |^CHQ VOTRE CHEQUE", t.label):
                t.raw = '%s No: %s' % (t.raw, cleaner(tds[self.COL_REF]))

            # In rare cases, label is empty ..
            if not t.label:
                t.label = cleaner(tds[self.COL_REF])

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

        currency = Account.get_currency(self.doc\
                                        .xpath('//table[@id="TabFact"]/thead//th')[self.COL_CARD_AMOUNT]\
                                        .text\
                                        .replace('(', ' ')\
                                        .replace(')', ' '))
        for i, tr in enumerate(self.doc.xpath('//table[@id="TabFact"]/tbody/tr')):
            tds = tr.findall('td')

            if len(tds) < 3:
                continue

            t = Transaction()

            cleaner = CleanText(None).filter
            date = cleaner(tds[self.COL_CARD_DATE])
            label = cleaner(tds[self.COL_CARD_LABEL])
            amount = '-' + cleaner(tds[self.COL_CARD_AMOUNT])

            t.parse(debit_date, re.sub(r'[ ]+', ' ', label))
            t.set_amount(amount)
            t.rdate = t.parse_date(date)
            t.original_currency = currency
            yield t

    def no_operations(self):
        if len(self.doc.xpath('//table[@id="tbl1" or @id="TabFact"]//td[@colspan]')) > 0:
            return True
        if len(self.doc.xpath(u'//div[contains(text(), "Accès à LineBourse")]')) > 0:
            return True

        return False

    def get_investment_page_params(self):
        script = self.doc.xpath('//body')[0].attrib['onload']
        url = None
        m = re.search(r"','(.+?)',\[", script, re.MULTILINE)
        if m:
            url = m.group(1)
        params = {}
        for key, value in re.findall(r"key:'(?P<key>SJRToken)'\,value:'(?P<value>.*?)'}", script, re.MULTILINE):
            params[key] = value
        return url, params if url and params else None


class LineboursePage(LoggedPage, HTMLPage):
    pass


class InvestmentLineboursePage(LoggedPage, HTMLPage):
    COL_LABEL = 0
    COL_QUANTITY = 1
    COL_UNITVALUE = 2
    COL_VALUATION = 3
    COL_UNITPRICE = 4
    COL_PERF_PERCENT = 5
    COL_PERF = 6

    def get_investments(self):
        for line in self.doc.xpath('//table[contains(@summary, "Contenu")]/tbody/tr[@class="color4"]'):
            cols1 = line.findall('td')
            cols2 = line.xpath('./following-sibling::tr')[0].findall('td')

            cleaner = CleanText(None).filter

            inv = Investment()
            inv.label = cleaner(cols1[self.COL_LABEL].xpath('.//span')[0])
            inv.code = cleaner(cols1[self.COL_LABEL].xpath('./a')[0]).split(' ')[-1]
            inv.quantity = self.parse_decimal(cols2[self.COL_QUANTITY])
            inv.unitprice = self.parse_decimal(cols2[self.COL_UNITPRICE])
            inv.unitvalue = self.parse_decimal(cols2[self.COL_UNITVALUE])
            inv.valuation = self.parse_decimal(cols2[self.COL_VALUATION])
            inv.diff = self.parse_decimal(cols2[self.COL_PERF])

            yield inv

    def parse_decimal(self, string):
        value = CleanText(None).filter(string)
        if value == '':
            return NotAvailable
        return Decimal(Transaction.clean_amount(value))


class NatixisPage(LoggedPage, HTMLPage):
    def submit_form(self):
        form = self.get_form(name="formRoutage")
        form.submit()


class NatixisErrorPage(LoggedPage, HTMLPage):
    pass


class MessagePage(LoggedPage, HTMLPage):
    def skip(self):
        try:
            form = self.get_form(name="leForm")
        except FormNotFound:
            pass
        else:
            form.submit()


class IbanPage(LoggedPage, MyHTMLPage):
    def need_to_go(self):
        return len(self.doc.xpath('//div[@class="grid"]/div/span[contains(text(), "IBAN")]')) == 0

    def go_iban(self, account):
        for tr in self.doc.xpath('//table[@id]/tbody/tr'):
            if account.type not in (Account.TYPE_LOAN, Account.TYPE_MARKET) and CleanText().filter(tr.xpath('./td[1]')) in account.id:
                form = self.get_form(id='myForm')
                form['token'] = self.build_token(form['token'])
                form['dialogActionPerformed'] = "DETAIL_IBAN_RIB"
                tr_id = Attr(None, 'id').filter(tr.xpath('.')).split('_')
                form[u'attribute($SEL_$%s)' % tr_id[0]] = tr_id[1]
                form.submit()
                return True
        return False

    def get_iban(self, acc_id):
        iban_class = None
        for div in self.doc.xpath('//div[@class="grid"]/div'):
            if not iban_class and "IBAN" in CleanText().filter(div.xpath('./span')):
                iban_class = Attr(None, 'class').filter(div.xpath('.'))
            elif iban_class is not None and iban_class == Attr(None, 'class').filter(div.xpath('.')):
                iban = CleanText().filter(div.xpath('.')).replace(' ', '')
                if re.sub('\D', '', acc_id) in iban:
                    return iban
        return NotAvailable


class EtnaPage(LoggedPage, MyHTMLPage):
    pass


def float_to_decimal(f):
    # Decimal(float_value) gives horrible results, convert to str first
    return Decimal(str(f))


class NatixisInvestPage(LoggedPage, JsonPage):
    @method
    class get_investments(DictElement):
        item_xpath = 'detailContratVie/valorisation/supports'

        class item(ItemElement):
            klass = Investment

            obj_label = CleanText(Dict('nom'))
            obj_code = CleanText(Dict('codeIsin'))
            obj_vdate = DateTime(Dict('dateValeurUniteCompte'))

            obj_valuation = Eval(float_to_decimal, Dict('montant'))
            obj_quantity = Eval(float_to_decimal, Dict('nombreUnitesCompte'))
            obj_unitvalue = Eval(float_to_decimal, Dict('valeurUniteCompte'))
            obj_portfolio_share = Eval(lambda x: float_to_decimal(x) / 100, Dict('repartition'))


class NatixisHistoryPage(LoggedPage, JsonPage):
    @method
    class get_history(DictElement):
        item_xpath = None

        class item(ItemElement):
            klass = Transaction

            obj_amount = Eval(float_to_decimal, Dict('montantNet'))
            obj_raw = CleanText(Dict('libelle'))
            obj_date = DateTime(Dict('dateValeur'))


class NatixisDetailsPage(LoggedPage, RawPage):
    def build_doc(self, data):
        return list(get_pdf_rows(data))

    def get_history(self):
        sign = 0
        tr = None

        for page in self.doc:
            first_in_page = True

            for row in page:
                if len(row) != 7:
                    first_in_page = False
                    continue

                label = ''.join(row[0])

                if label == 'Investissement':
                    sign = 1
                    first_in_page = False
                    continue
                elif label == u'Désinvestissement':
                    sign = -1
                    first_in_page = False
                    continue

                global_amount = ''.join(row[2])
                if global_amount:
                    if first_in_page and tr and tr.raw == label:
                        # this must be the continuation of the previous page
                        first_in_page = False
                        continue
                    first_in_page = False

                    if tr is not None:
                        # flush
                        yield tr

                    # amount is "brut", unlike invest amounts ("net")...
                    sign = 0
                    tr = None

                    if not label:
                        # this pdf is really cryptic...
                        # we assume blue rows are a new transaction
                        # but if no label, it doesn't appear in the website json
                        continue

                    tr = Transaction()
                    tr.raw = label
                    tr.investments = []
                    continue

                first_in_page = False

                date = ''.join(row[1])
                assert date

                if tr is None:
                    # ignore transactions with the empty label, see above
                    continue

                assert sign

                inv = Investment()
                inv.label = label
                inv.vdate = Date(dayfirst=True).filter(date)

                inv.quantity = CleanDecimal(replace_dots=True, default=NotAvailable).filter(''.join(row[5]))
                if inv.quantity is not NotAvailable:
                    inv.quantity *= sign

                inv.unitvalue = CleanDecimal(replace_dots=True, default=NotAvailable).filter(''.join(row[4]))
                if inv.unitvalue is not NotAvailable:
                    inv.unitvalue *= sign

                tr.investments.append(inv)

        # flush
        if tr is not None:
            yield tr
