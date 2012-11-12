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


from decimal import Decimal
import re

from weboob.tools.mech import ClientForm
from weboob.tools.browser import BasePage, BrokenPageError, BrowserUnavailable
from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


__all__ = ['LoginPage', 'ErrorPage', 'IndexPage', 'UnavailablePage']


class LoginPage(BasePage):
    def login(self, login):
        self.browser.select_form(name='Main')
        self.browser.set_all_readonly(False)
        self.browser['ctl01$CC_ind_pauthpopup$ctl01$CC_ind_ident$ctl01$CC_ind_inputuserid_sup$txnuabbd'] = login
        self.browser['__EVENTTARGET'] = 'ctl01$CC_ind_pauthpopup$ctl01$CC_ind_ident$ctl01$CC_ind_inputuserid_sup$btnValider'
        self.browser.submit(nologin=True)

    def login2(self):
        self.browser.select_form(name='Main')
        self.browser.set_all_readonly(False)
        self.browser['__EVENTARGUMENT'] = 'idsrv=WE'
        self.browser.submit(nologin=True)

    def login3(self, passwd):
        self.browser.select_form(name='Main')
        self.browser['codconf'] = passwd
        a = self.document.xpath('//a[@title="Valider"]')[0]
        m = re.match("javascript:RedirectToDeiPart\('([^']+)'\);", a.attrib['href'])
        if not m:
            raise BrokenPageError('Unable to find validate URL')
        self.browser.form.action = m.group(1)
        self.browser.submit(nologin=True)

class ErrorPage(BasePage):
    def get_error(self):
        try:
            return self.parser.select(self.document.getroot(), 'div.messErreur', 1).text.strip()
        except BrokenPageError:
            return None

class UnavailablePage(BasePage):
    def on_loaded(self):
        try:
            raise BrowserUnavailable(self.parser.select(self.document.getroot(), 'div#message_error_hs', 1).text.strip())
        except BrokenPageError:
            raise BrowserUnavailable()

class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile('^CB (?P<text>.*?) FACT (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2})'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile('^RETRAIT DAB (?P<dd>\d+)-(?P<mm>\d+)-.*'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^VIR(EMENT)?(\.PERIODIQUE)? (?P<text>.*)'),   FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^PRLV (?P<text>.*)'),          FrenchTransaction.TYPE_ORDER),
                (re.compile('^CHEQUE.*'),                   FrenchTransaction.TYPE_CHECK),
                (re.compile('^(CONVENTION \d+ )?COTIS(ATION)? (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_BANK),
                (re.compile(r'^\* (?P<text>.*)'),           FrenchTransaction.TYPE_BANK),
                (re.compile('^REMISE (?P<text>.*)'),        FrenchTransaction.TYPE_DEPOSIT),
                (re.compile('^(?P<text>.*)( \d+)? QUITTANCE .*'),
                                                            FrenchTransaction.TYPE_ORDER),
               ]

class IndexPage(BasePage):
    ACCOUNT_TYPES = {u'Epargne liquide':            Account.TYPE_SAVINGS,
                     u'Compte Courant':             Account.TYPE_CHECKING,
                    }

    def get_list(self):
        for table in self.document.xpath('//table[@cellpadding="1"]'):
            account_type = Account.TYPE_UNKNOWN
            for tr in table.xpath('./tr'):
                tds = tr.findall('td')
                if tr.attrib.get('class', '') == 'DataGridHeader':
                    account_type = self.ACCOUNT_TYPES.get(tds[1].text.strip(), Account.TYPE_UNKNOWN)
                else:
                    a = tds[1].find('a')
                    m = re.match("^javascript:__doPostBack\('.*','HISTORIQUE_COMPTE&(\d+)'\)", a.attrib['href'])

                    if not m:
                        self.logger.warning('Unable to parse account %s' % (a.text.strip() if a.text is not None else ''))
                        continue

                    account = Account()
                    account.id = m.group(1)
                    account.label = unicode(a.text.strip())
                    account.type = account_type
                    amount = u''.join([txt.strip() for txt in tds[-1].itertext()])
                    account.balance = Decimal(FrenchTransaction.clean_amount(amount.rstrip(' EUR')))
                    yield account

    def go_history(self, id):
        self.browser.select_form(name='main')
        self.browser.set_all_readonly(False)
        self.browser['__EVENTTARGET'] = 'MM$SYNTHESE'
        self.browser['__EVENTARGUMENT'] = 'HISTORIQUE_COMPTE&%s' % id
        self.browser['MM$m_CH$IsMsgInit'] = '0'
        self.browser.controls.append(ClientForm.TextControl('text', 'm_ScriptManager', {'value': ''}))
        self.browser['m_ScriptManager'] = 'MM$m_UpdatePanel|MM$SYNTHESE'
        self.browser.controls.remove(self.browser.find_control(name='Cartridge$imgbtnMessagerie', type='image'))
        self.browser.controls.remove(self.browser.find_control(name='MM$m_CH$ButtonImageFondMessagerie', type='image'))
        self.browser.controls.remove(self.browser.find_control(name='MM$m_CH$ButtonImageMessagerie', type='image'))
        self.browser.submit()

    def get_history(self):
        i = 0
        for tr in self.document.xpath('//table[@cellpadding="1"]/tr'):
            if tr.attrib.get('class', '') == 'DataGridHeader':
                continue

            tds = tr.findall('td')

            t = Transaction(i)

            date = u''.join([txt.strip() for txt in tds[1].itertext()])
            raw = u' '.join([txt.strip() for txt in tds[2].itertext()])
            debit = u''.join([txt.strip() for txt in tds[-2].itertext()])
            credit = u''.join([txt.strip() for txt in tds[-1].itertext()])

            t.parse(date, re.sub(r'[ ]+', ' ', raw))
            t.set_amount(credit, debit)
            yield t

            i += 1
