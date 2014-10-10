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


from weboob.deprecated.mech import ClientForm
ControlNotFoundError = ClientForm.ControlNotFoundError

from decimal import Decimal
import re

from weboob.deprecated.mech import ClientForm
from weboob.tools.ordereddict import OrderedDict
from weboob.deprecated.browser import Page, BrokenPageError, BrowserUnavailable, BrowserIncorrectPassword
from weboob.capabilities import NotAvailable
from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


class _LogoutPage(Page):
    def on_loaded(self):
        try:
            raise BrowserIncorrectPassword(self.parser.tocleanstring(self.parser.select(self.document.getroot(), '.messErreur', 1)))
        except BrokenPageError:
            pass


class LoginPage(_LogoutPage):
    def login(self, login):
        self.browser.select_form(name='Main')
        self.browser.set_all_readonly(False)
        self.browser['ctl01$CC_ind_pauthpopup$ctl01$CC_ind_ident$ctl01$CC_ind_inputuserid_sup$txnuabbd'] = login.encode('utf-8')
        self.browser['__EVENTTARGET'] = 'ctl01$CC_ind_pauthpopup$ctl01$CC_ind_ident$ctl01$CC_ind_inputuserid_sup$btnValider'
        self.browser.submit(nologin=True)

    def login2(self, nuser, passwd):
        self.browser.select_form(name='Main')
        self.browser.set_all_readonly(False)
        self.browser['__EVENTARGUMENT'] = 'idsrv=WE'

        m = None
        try:
            a = self.document.xpath('//a[@title="Valider"]')[0]
        except IndexError:
            pass
        else:
            m = re.match("javascript:RedirectToDeiPro\('([^']+)', \d+\);", a.attrib['href'])

        if m:
            self.browser['nuusager'] = nuser.encode('utf-8')
            self.browser['codconf'] = passwd.encode('utf-8')
            self.browser.form.action = m.group(1)

        self.browser.submit(nologin=True)

        return m is not None

    def login3(self, passwd):
        self.browser.select_form(name='Main')
        self.browser['codconf'] = passwd.encode('utf-8')
        a = self.document.xpath('//a[@title="Valider"]')[0]
        m = re.match("javascript:RedirectToDeiPart\('([^']+)'\);", a.attrib['href'])
        if not m:
            raise BrokenPageError('Unable to find validate URL')
        self.browser.form.action = m.group(1)
        self.browser.submit(nologin=True)


class ErrorPage(_LogoutPage):
    pass


class UnavailablePage(Page):
    def on_loaded(self):
        try:
            raise BrowserUnavailable(self.parser.select(self.document.getroot(), 'div#message_error_hs', 1).text.strip())
        except BrokenPageError:
            raise BrowserUnavailable()


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile('^CB (?P<text>.*?) FACT (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2})', re.IGNORECASE),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile('^RET(RAIT)? DAB (?P<dd>\d+)-(?P<mm>\d+)-.*', re.IGNORECASE),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^RET(RAIT)? DAB (?P<text>.*?) (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2}) (?P<HH>\d{2})H(?P<MM>\d{2})', re.IGNORECASE),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^VIR(EMENT)?(\.PERIODIQUE)? (?P<text>.*)', re.IGNORECASE),
                                                            FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^PRLV (?P<text>.*)', re.IGNORECASE),
                                                            FrenchTransaction.TYPE_ORDER),
                (re.compile('^CHEQUE.*', re.IGNORECASE),    FrenchTransaction.TYPE_CHECK),
                (re.compile('^(CONVENTION \d+ )?COTIS(ATION)? (?P<text>.*)', re.IGNORECASE),
                                                            FrenchTransaction.TYPE_BANK),
                (re.compile(r'^\* (?P<text>.*)', re.IGNORECASE),
                                                            FrenchTransaction.TYPE_BANK),
                (re.compile('^REMISE (?P<text>.*)', re.IGNORECASE),
                                                            FrenchTransaction.TYPE_DEPOSIT),
                (re.compile('^(?P<text>.*)( \d+)? QUITTANCE .*', re.IGNORECASE),
                                                            FrenchTransaction.TYPE_ORDER),
                (re.compile('^CB [\d\*]+ (?P<text>.*)', re.IGNORECASE),
                                                            FrenchTransaction.TYPE_CARD),
               ]


class IndexPage(Page):
    ACCOUNT_TYPES = {u'Epargne liquide':            Account.TYPE_SAVINGS,
                     u'Compte Courant':             Account.TYPE_CHECKING,
                     u'Mes comptes':                Account.TYPE_CHECKING,
                     u'Mon épargne':                Account.TYPE_SAVINGS,
                    }

    def _get_account_info(self, a):
        m = re.search("PostBack(Options)?\([\"'][^\"']+[\"'],\s*['\"]HISTORIQUE_([\d\w&]+)['\"]", a.attrib.get('href', ''))
        if m is None:
            return None
        else:
            # it is in form CB&12345[&2]. the last part is only for new website
            # and is necessary for navigation.
            link = m.group(2)
            parts = link.split('&')
            return {'type': parts[0], 'id': parts[1], 'link': link}

    def _add_account(self, accounts, link, label, account_type, balance):
        info = self._get_account_info(link)
        if info is None:
            self.logger.warning('Unable to parse account %r: %r' % (label, link))
            return

        account = Account()
        account.id = info['id']
        account._info = info
        account.label = label
        account.type = account_type
        account.balance = Decimal(FrenchTransaction.clean_amount(balance))
        account.currency = account.get_currency(balance)
        account._card_links = []

        if account._info['type'] == 'CB' and account.id in accounts:
            a = accounts[account.id]
            if not a.coming:
                a.coming = Decimal('0.0')
            a.coming += account.balance
            a._card_links.append(account._info)
            return

        accounts[account.id] = account

    def get_list(self):
        accounts = OrderedDict()

        # Old website
        for table in self.document.xpath('//table[@cellpadding="1"]'):
            account_type = Account.TYPE_UNKNOWN
            for tr in table.xpath('./tr'):
                tds = tr.findall('td')
                if tr.attrib.get('class', '') == 'DataGridHeader':
                    account_type = self.ACCOUNT_TYPES.get(tds[1].text.strip(), Account.TYPE_UNKNOWN)
                else:
                    label = ''
                    i = 1
                    a = None
                    while label == '' and i < len(tds):
                        a = tds[i].find('a')
                        if a is None:
                            continue

                        label = self.parser.tocleanstring(a)
                        i += 1

                    balance = ''
                    i = -1
                    while balance == '' and i > -len(tds):
                        try:
                            balance = self.parser.tocleanstring(tds[i].xpath('./a')[0])
                        except KeyError:
                            balance = u''.join([txt.strip() for txt in tds[i].itertext()])
                        i -= 1
                    self._add_account(accounts, a, label, account_type, balance)

        if len(accounts) == 0:
            # New website
            for table in self.document.xpath('//div[@class="panel"]'):
                title = table.getprevious()
                if title is None:
                    continue
                account_type = self.ACCOUNT_TYPES.get(self.parser.tocleanstring(title), Account.TYPE_UNKNOWN)
                for tr in table.xpath('.//tr'):
                    tds = tr.findall('td')
                    for i in xrange(len(tds)):
                        a = tds[i].find('a')
                        if a is not None:
                            break

                    if a is None:
                        continue

                    label = self.parser.tocleanstring(tds[0])
                    balance = self.parser.tocleanstring(tds[-1])

                    self._add_account(accounts, a, label, account_type, balance)

        return accounts.itervalues()

    def go_list(self):
        self.browser.select_form(name='main')
        self.browser.set_all_readonly(False)
        self.browser['__EVENTARGUMENT'] = 'CPTSYNT0'
        self.browser.controls.append(ClientForm.TextControl('text', 'm_ScriptManager', {'value': ''}))

        # Ugly check to determine if we are on the new or old website.
        try:
            self.browser['MM$m_CH$IsMsgInit']
        except ControlNotFoundError:
            self.logger.debug('New website')
            self.browser['__EVENTTARGET'] = 'MM$m_PostBack'
            self.browser['m_ScriptManager'] = 'MM$m_UpdatePanel|MM$m_PostBack'
        else:
            self.logger.debug('Old website')
            self.browser['__EVENTTARGET'] = 'Menu_AJAX'
            self.browser['m_ScriptManager'] = 'm_ScriptManager|Menu_AJAX'

        try:
            self.browser.controls.remove(self.browser.find_control(name='Cartridge$imgbtnMessagerie', type='image'))
            self.browser.controls.remove(self.browser.find_control(name='MM$m_CH$ButtonImageFondMessagerie', type='image'))
            self.browser.controls.remove(self.browser.find_control(name='MM$m_CH$ButtonImageMessagerie', type='image'))
        except ControlNotFoundError:
            pass
        self.browser.submit()

    def go_history(self, info):
        self.browser.select_form(name='main')
        self.browser.set_all_readonly(False)
        self.browser['__EVENTTARGET'] = 'MM$SYNTHESE'
        self.browser['__EVENTARGUMENT'] = 'HISTORIQUE_%s' % info['link']
        try:
            self.browser['MM$m_CH$IsMsgInit'] = '0'
        except ControlNotFoundError:
            # Not available on new website.
            pass
        self.browser.controls.append(ClientForm.TextControl('text', 'm_ScriptManager', {'value': ''}))
        self.browser['m_ScriptManager'] = 'MM$m_UpdatePanel|MM$SYNTHESE'
        try:
            self.browser.controls.remove(self.browser.find_control(name='Cartridge$imgbtnMessagerie', type='image'))
            self.browser.controls.remove(self.browser.find_control(name='MM$m_CH$ButtonImageFondMessagerie', type='image'))
            self.browser.controls.remove(self.browser.find_control(name='MM$m_CH$ButtonImageMessagerie', type='image'))
        except ControlNotFoundError:
            pass
        self.browser.submit()

    def get_history(self):
        i = 0
        ignore = False
        for tr in self.document.xpath('//table[@cellpadding="1"]/tr') + self.document.xpath('//tr[@class="rowClick" or @class="rowHover"]'):
            tds = tr.findall('td')

            if len(tds) < 4:
                continue

            # if there are more than 4 columns, ignore the first one.
            i = min(len(tds) - 4, 1)

            if tr.attrib.get('class', '') == 'DataGridHeader':
                if tds[2].text == u'Titulaire':
                    ignore = True
                else:
                    ignore = False
                continue

            if ignore:
                continue

            # Remove useless details
            detail = tr.cssselect('div.detail')
            if len(detail) > 0:
                detail[0].drop_tree()

            t = Transaction(i)

            date = u''.join([txt.strip() for txt in tds[i+0].itertext()])
            raw = u' '.join([txt.strip() for txt in tds[i+1].itertext()])
            debit = u''.join([txt.strip() for txt in tds[-2].itertext()])
            credit = u''.join([txt.strip() for txt in tds[-1].itertext()])

            t.parse(date, re.sub(r'[ ]+', ' ', raw))
            if t.date is NotAvailable:
                continue
            t.set_amount(credit, debit)
            yield t

            i += 1

    def go_next(self):
        # <a id="MM_HISTORIQUE_CB_lnkSuivante" class="next" href="javascript:WebForm_DoPostBackWithOptions(new WebForm_PostBackOptions(&quot;MM$HISTORIQUE_CB$lnkSuivante&quot;, &quot;&quot;, true, &quot;&quot;, &quot;&quot;, false, true))">Suivant<span class="arrow">></span></a>

        link = self.document.xpath('//a[contains(@id, "lnkSuivante")]')
        if len(link) == 0 or 'disabled' in link[0].attrib:
            return False

        account_type = 'COMPTE'
        m = re.search('HISTORIQUE_(\w+)', link[0].attrib['href'])
        if m:
            account_type = m.group(1)

        self.browser.select_form(name='main')
        self.browser.set_all_readonly(False)
        self.browser['__EVENTTARGET'] = 'MM$HISTORIQUE_%s$lnkSuivante' % account_type
        self.browser['__EVENTARGUMENT'] = ''
        try:
            self.browser['MM$m_CH$IsMsgInit'] = 'N'
        except ControlNotFoundError:
            # New website
            pass
        self.browser.controls.append(ClientForm.TextControl('text', 'm_ScriptManager', {'value': ''}))
        self.browser['m_ScriptManager'] = 'MM$m_UpdatePanel|MM$HISTORIQUE_COMPTE$lnkSuivante'
        try:
            self.browser.controls.remove(self.browser.find_control(name='Cartridge$imgbtnMessagerie', type='image'))
            self.browser.controls.remove(self.browser.find_control(name='MM$m_CH$ButtonImageFondMessagerie', type='image'))
            self.browser.controls.remove(self.browser.find_control(name='MM$m_CH$ButtonImageMessagerie', type='image'))
        except ControlNotFoundError:
            pass
        self.browser.submit()

        return True
