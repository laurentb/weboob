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
from weboob.capabilities.bank import Account, Investment
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


class GarbagePage(Page):
    pass


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
                     u'Mes autres comptes':         Account.TYPE_SAVINGS,
                     u'Compte Epargne et DAT':      Account.TYPE_SAVINGS,
                     u'Plan et Contrat d\'Epargne': Account.TYPE_SAVINGS,
                     u'Titres':                     Account.TYPE_MARKET,
                     u'Compte titres':              Account.TYPE_MARKET,
                    }

    def on_loaded(self):
        # This page is sometimes an useless step to the market website.
        bourse_link = self.document.xpath(u'//div[@id="MM_COMPTE_TITRE_pnlbourseoic"]//a[contains(text(), "Accédez à la consultation")]')
        if len(bourse_link) == 1:
            self.browser.location(bourse_link[0].attrib['href'])

    def _get_account_info(self, a):
        m = re.search("PostBack(Options)?\([\"'][^\"']+[\"'],\s*['\"]([HISTORIQUE_\w|SYNTHESE_ASSURANCE_CNP|BOURSE|COMPTE_TITRE][\d\w&]+)?['\"]", a.attrib.get('href', ''))
        if m is None:
            return None
        else:
            # it is in form CB&12345[&2]. the last part is only for new website
            # and is necessary for navigation.
            link = m.group(2)
            parts = link.split('&')
            info = {}
            if len(parts) > 1:
                info['type'] = parts[0]
                info['id'] = parts[1]
            else:
                id = re.search("([\d]+)", a.attrib.get('title'))
                info['type'] = link
                info['id'] = id.group(1)
            if info['type'] == 'SYNTHESE_ASSURANCE_CNP':
                info['acc_type'] = Account.TYPE_LIFE_INSURANCE
            if info['type'] in ('BOURSE', 'COMPTE_TITRE'):
                info['acc_type'] = Account.TYPE_MARKET
            info['link'] = link
            return info


    def _add_account(self, accounts, link, label, account_type, balance):
        info = self._get_account_info(link)
        if info is None:
            self.logger.warning('Unable to parse account %r: %r' % (label, link))
            return

        account = Account()
        account.id = info['id']
        account.iban = u'FR76' + info['id']
        account._info = info
        account.label = label
        account.type = info['acc_type'] if 'acc_type' in info else account_type
        account.balance = Decimal(FrenchTransaction.clean_amount(balance)) if balance else self.get_balance(account)
        account.currency = account.get_currency(balance)
        account._card_links = []

        if account._info['type'] == 'HISTORIQUE_CB' and account.id in accounts:
            a = accounts[account.id]
            if not a.coming:
                a.coming = Decimal('0.0')
            a.coming += account.balance
            a._card_links.append(account._info)
            return

        accounts[account.id] = account

    def get_balance(self, account):
        if not account.type == Account.TYPE_LIFE_INSURANCE:
            return NotAvailable
        self.go_history(account._info)
        balance = self.browser.page.document.xpath('.//tr[td[contains(text(), ' + account.id + ')]]/td[contains(@class, "somme")]')
        if len(balance) > 0:
            balance = self.parser.tocleanstring(balance[0])
            balance = Decimal(FrenchTransaction.clean_amount(balance)) if balance != u'' else NotAvailable
        else:
            balance = NotAvailable
        self.go_list()
        return balance

    def get_list(self):
        accounts = OrderedDict()

        # Old website
        for table in self.document.xpath('//table[@cellpadding="1"]'):
            account_type = Account.TYPE_UNKNOWN
            for tr in table.xpath('./tr'):
                tds = tr.findall('td')
                if tr.attrib.get('class', '') == 'DataGridHeader':
                    account_type = self.ACCOUNT_TYPES.get(tds[1].text.strip()) or\
                                   self.ACCOUNT_TYPES.get(self.parser.tocleanstring(tds[2])) or\
                                   self.ACCOUNT_TYPES.get(self.parser.tocleanstring(tds[3]), Account.TYPE_UNKNOWN)
                else:
                    # On the same row, there are many accounts (for example a
                    # check accound and a card one).
                    if len(tds) > 4:
                        for i, a in enumerate(tds[2].xpath('./a')):
                            label = self.parser.tocleanstring(a)
                            balance = self.parser.tocleanstring(tds[-2].xpath('./a')[i])
                            self._add_account(accounts, a, label, account_type, balance)
                    # Only 4 tds on banque de la reunion website.
                    elif len(tds) == 4:
                        for i, a in enumerate(tds[1].xpath('./a')):
                            label = self.parser.tocleanstring(a)
                            balance = self.parser.tocleanstring(tds[-1].xpath('./a')[i])
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
            self.browser.controls.remove(self.browser.find_control(name='MM$HISTORIQUE_COMPTE$btnCumul'))
        except:
            pass
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
        self.browser['__EVENTARGUMENT'] = info['link']
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

            t = Transaction()

            date = u''.join([txt.strip() for txt in tds[i+0].itertext()])
            raw = u' '.join([txt.strip() for txt in tds[i+1].itertext()])
            debit = u''.join([txt.strip() for txt in tds[-2].itertext()])
            credit = u''.join([txt.strip() for txt in tds[-1].itertext()])

            t.parse(date, re.sub(r'[ ]+', ' ', raw))
            if t.date is NotAvailable or 'Tot Dif' in t.raw:
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
        try:
            self.browser.controls.remove(self.browser.find_control(name='MM$HISTORIQUE_COMPTE$btnCumul'))
        except ControlNotFoundError:
            pass
        self.browser.submit()

        return True

    def go_life_insurance(self, account):
        link = self.document.xpath('//table[@summary="Mes contrats d\'assurance vie"]/tbody/tr[td[contains(text(), ' + account.id + ') ]]//a')[0]
        m = re.search("PostBack(Options)?\([\"'][^\"']+[\"'],\s*['\"](REDIR_ASS_VIE[\d\w&]+)?['\"]", link.attrib.get('href', ''))
        if m is not None:
            self.browser.select_form(name='main')
            self.browser.set_all_readonly(False)
            self.browser['__EVENTTARGET'] = 'MM$SYNTHESE_ASSURANCE_CNP'
            self.browser['__EVENTARGUMENT'] = m.group(2)
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


class MarketPage(Page):
    def is_error(self):
        try:
            return self.document.xpath('//caption')[0].text == "Erreur"
        except IndexError:
            return False


    def parse_decimal(self, td):
        value = self.parser.tocleanstring(td)
        if value and value != '-':
            return Decimal(FrenchTransaction.clean_amount(value))
        else:
            return NotAvailable

    def submit(self):
        self.browser.select_form(nr=1)
        self.browser.submit()

    def iter_investment(self):
        for tbody in self.document.xpath(u'//table[@summary="Contenu du portefeuille valorisé"]/tbody'):

            inv = Investment()
            inv.label = self.parser.tocleanstring(tbody.xpath('./tr[1]/td[1]/a/span')[0])
            inv.code = self.parser.tocleanstring(tbody.xpath('./tr[1]/td[1]/a')[0]).split(' - ')[1]
            inv.quantity = self.parse_decimal(tbody.xpath('./tr[2]/td[2]')[0])
            inv.unitvalue = self.parse_decimal(tbody.xpath('./tr[2]/td[3]')[0])
            inv.unitprice = self.parse_decimal(tbody.xpath('./tr[2]/td[5]')[0])
            inv.valuation = self.parse_decimal(tbody.xpath('./tr[2]/td[4]')[0])
            inv.diff = self.parse_decimal(tbody.xpath('./tr[2]/td[7]')[0])

            yield inv

    def get_valuation_diff(self, account):
        valuation_diff = re.sub(r'\(.*\)', '', self.document.xpath(u'//td[contains(text(), "values latentes")]/following-sibling::*[1]')[0].text)
        account.valuation_diff = Decimal(FrenchTransaction.clean_amount(valuation_diff))

    def is_on_right_portfolio(self, account):
        return len(self.document.xpath('//form[@class="choixCompte"]//option[@selected and contains(text(), "%s")]' % account._info['id']))

    def get_compte(self, account):
        return self.document.xpath('//option[contains(text(), "%s")]/@value' % account._info['id'])[0]

class LifeInsurance(MarketPage):
    def get_cons_repart(self):
        return self.document.xpath('//tr[@id="sousMenuConsultation3"]/td/div/a')[0].attrib['href']

    def iter_investment(self):
        for tr in self.document.xpath(u'//table[@class="boursedetail"]/tr[@class and not(@class="total")]'):

            inv = Investment()
            libelle = self.parser.tocleanstring(tr.xpath('./td[1]')[0]).split(' ')
            inv.label, inv.code = self.split_label_code(libelle)
            diff = self.parse_decimal(tr.xpath('./td[6]')[0])
            inv.quantity = self.parse_decimal(tr.xpath('./td[2]')[0])
            inv.unitvalue = self.parse_decimal(tr.xpath('./td[3]')[0])
            inv.unitprice = self.calc(inv.unitvalue, diff)
            inv.valuation = self.parse_decimal(tr.xpath('./td[5]')[0])
            inv.diff = self.get_diff(inv.valuation, self.calc(inv.valuation, diff))

            yield inv

    def calc(self, value, diff):
        if value is NotAvailable or diff is NotAvailable:
            return NotAvailable
        return Decimal(value) / (1 + Decimal(diff)/100)

    def get_diff(self, valuation, calc):
        if valuation is NotAvailable or calc is NotAvailable:
            return NotAvailable
        return valuation - calc

    def split_label_code(self, libelle):
        m = re.search('FR\d+', libelle[-1])
        if m:
            return ' '.join(libelle[:-1]), libelle[-1]
        else:
            return ' '.join(libelle), NotAvailable
